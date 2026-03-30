# data_source/ths_client.py
"""同花顺财务风险数据爬虫

使用Playwright异步爬取同花顺网站的财务风险评估数据
"""

import asyncio
import logging
import re
import time
from datetime import date, datetime
from typing import List, Optional

from playwright.async_api import async_playwright, Browser, BrowserContext, Page, TimeoutError as PlaywrightTimeoutError

from data_source.exceptions import NetworkError, NoDataError, DataError
from data_source.rate_limiter import RateLimiter
from models.stock_financial_risk import StockFinancialRisk


logger = logging.getLogger(__name__)


class THSRiskPageSource:
    """同花顺股票财务风险页面数据源"""

    # 同花顺股票风险页面URL模板 - 使用经过验证的URL
    RISK_URL_TEMPLATE = "https://basic.10jqka.com.cn/{stock_code}/"

    # 风险等级CSS选择器（基于同花顺页面结构）
    RISK_TABLE_SELECTOR = "table.risk-table, table.risk-eval"
    RISK_ROW_SELECTOR = "table.risk-table tr, table.risk-eval tr"

    # 风险数据选择器
    TOTAL_RISK_SELECTOR = "span.total-risk, .risk-total"
    NO_RISK_SELECTOR = "span.no-risk, .risk-level-0"
    LOW_RISK_SELECTOR = "span.low-risk, .risk-level-1"
    MEDIUM_RISK_SELECTOR = "span.medium-risk, .risk-level-2"
    HIGH_RISK_SELECTOR = "span.high-risk, .risk-level-3"

    # 日期选择器
    DATE_SELECTOR = ".risk-date, .update-date, [class*='risk-date']"


class THSClient:
    """同花顺财务风险数据爬虫

    使用Playwright异步爬取同花顺网站的财务风险评估数据

    注意：同花顺网站有严格的反爬虫机制，如果频繁访问可能会被封禁
    """

    # 默认User-Agent列表，模拟真实浏览器
    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    ]

    def __init__(
        self,
        headless: bool = True,
        timeout: int = 30000,
        slow_mo: int = 100,
        browser_type: str = "chromium",
        rate_limit_interval: float = 3.0,
        use_proxy: bool = False
    ):
        """初始化同花顺爬虫

        Args:
            headless: 是否使用无头模式
            timeout: 超时时间（毫秒）
            slow_mo: 操作间隔（毫秒），用于调试
            browser_type: 浏览器类型，可选 'chromium', 'firefox', 'webkit'
            rate_limit_interval: 请求间隔（秒），防止被封禁
            use_proxy: 是否使用代理
        """
        self.headless = headless
        self.timeout = timeout
        self.slow_mo = slow_mo
        self.browser_type = browser_type
        self.use_proxy = use_proxy
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        self._playwright = None
        self._rate_limiter = RateLimiter(
            base_interval=rate_limit_interval,
            full_sync_interval=rate_limit_interval,
            incremental_sync_interval=rate_limit_interval
        )
        self._last_request_time = 0.0
        self._request_count = 0

    async def _create_context(self) -> BrowserContext:
        """创建浏览器上下文，带有反反爬虫措施"""
        if self._context is None:
            # 选择随机User-Agent
            import random
            user_agent = random.choice(self.USER_AGENTS)

            self._context = await self._browser.new_context(
                user_agent=user_agent,
                viewport={"width": 1920, "height": 1080},
                locale="zh-CN",
                timezone_id="Asia/Shanghai",
                ignore_https_errors=True,
            )

            # 阻止webdriver检测
            await self._context.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5]
                });
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['zh-CN', 'zh', 'en-US', 'en']
                });
                window.chrome = { runtime: {} };
            """)

        return self._context

    async def _get_browser(self) -> Browser:
        """获取或创建浏览器实例"""
        if self._browser is None:
            self._playwright = await async_playwright().start()
            browser_launcher = getattr(self._playwright, self.browser_type)

            launch_args = [
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-infobars',
                '--disable-extensions',
            ]

            self._browser = await browser_launcher.launch(
                headless=self.headless,
                slow_mo=self.slow_mo,
                args=launch_args
            )
        return self._browser

    async def _create_page(self) -> Page:
        """创建新页面"""
        browser = await self._get_browser()
        context = await self._create_context()
        page = await context.new_page()
        page.set_default_timeout(self.timeout)
        return page

    async def close(self) -> None:
        """关闭浏览器"""
        if self._context:
            await self._context.close()
            self._context = None
        if self._browser:
            await self._browser.close()
            self._browser = None
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None

    async def get_financial_risk(self, stock_code: str) -> List[StockFinancialRisk]:
        """获取单只股票的财务风险数据

        Args:
            stock_code: 股票代码（如 600000、000001）

        Returns:
            List[StockFinancialRisk]: 财务风险数据列表

        Raises:
            NetworkError: 网络请求失败
            NoDataError: 未获取到数据
            DataError: 数据解析失败
        """
        if not stock_code:
            raise ValueError("stock_code cannot be empty")

        # 标准化股票代码格式
        symbol = stock_code.strip()
        if not symbol.isalnum():
            raise ValueError(f"Invalid stock code: {stock_code}")

        # 限流：确保请求间隔
        current_time = time.time()
        elapsed = current_time - self._last_request_time
        if elapsed < self._rate_limiter.base_interval:
            await asyncio.sleep(self._rate_limiter.base_interval - elapsed)
        self._last_request_time = time.time()
        self._request_count += 1

        url = THSRiskPageSource.RISK_URL_TEMPLATE.format(stock_code=symbol)

        page = None
        try:
            page = await self._create_page()

            logger.debug(f"Fetching risk data from {url}")

            # 先访问主页建立会话
            await page.goto("https://www.10jqka.com.cn/", wait_until="domcontentloaded")
            await asyncio.sleep(1)

            # 然后访问目标页面
            response = await page.goto(url, wait_until="networkidle", timeout=60000)

            if response is None or response.status >= 400:
                raise NetworkError(
                    f"Failed to fetch risk data for {stock_code}: HTTP {response.status if response else 'None'}"
                )

            # 等待页面加载完成
            await page.wait_for_load_state("domcontentloaded")
            # 额外等待JS渲染
            await asyncio.sleep(2)

            # 获取页面内容用于调试
            content = await page.content()
            if len(content) < 1000:
                logger.warning(f"Page content too short ({len(content)} chars) for {stock_code}, may be blocked")

            # 尝试提取风险数据
            risk_data = await self._extract_risk_data(page, stock_code)

            if risk_data is None:
                logger.warning(f"No risk data found for {stock_code}")
                return []

            logger.info(f"Successfully extracted risk data for {stock_code}: {risk_data}")
            return [risk_data]

        except PlaywrightTimeoutError as e:
            raise NetworkError(f"Timeout fetching risk data for {stock_code}: {str(e)}")
        except NetworkError:
            raise
        except Exception as e:
            raise DataError(f"Failed to parse risk data for {stock_code}: {str(e)}")
        finally:
            if page:
                await page.close()

    async def _extract_risk_data(self, page: Page, stock_code: str) -> Optional[StockFinancialRisk]:
        """从页面提取风险数据

        Args:
            page: Playwright页面对象
            stock_code: 股票代码

        Returns:
            Optional[StockFinancialRisk]: 风险数据，未找到则返回None
        """
        try:
            # 提取日期
            trade_date = await self._extract_date(page)
            if trade_date is None:
                # 默认为当天
                trade_date = date.today()

            # 提取各风险等级数量
            total_risk = await self._extract_risk_count(page, THSRiskPageSource.TOTAL_RISK_SELECTOR, default=0)
            no_risk = await self._extract_risk_count(page, THSRiskPageSource.NO_RISK_SELECTOR, default=0)
            low_risk = await self._extract_risk_count(page, THSRiskPageSource.LOW_RISK_SELECTOR, default=0)
            medium_risk = await self._extract_risk_count(page, THSRiskPageSource.MEDIUM_RISK_SELECTOR, default=0)
            high_risk = await self._extract_risk_count(page, THSRiskPageSource.HIGH_RISK_SELECTOR, default=0)

            # 如果total_risk为0，尝试从各风险等级求和
            if total_risk == 0:
                total_risk = no_risk + low_risk + medium_risk + high_risk

            # 如果所有值都是0，尝试从表格中提取
            if total_risk == 0 and no_risk == 0 and low_risk == 0 and medium_risk == 0 and high_risk == 0:
                total_risk, no_risk, low_risk, medium_risk, high_risk = await self._extract_from_table(page)

            return StockFinancialRisk(
                stock_code=stock_code,
                trade_date=trade_date,
                total_risk=total_risk,
                no_risk=no_risk,
                low_risk=low_risk,
                medium_risk=medium_risk,
                high_risk=high_risk,
                data_source="ths"
            )

        except Exception as e:
            logger.error(f"Error extracting risk data: {e}")
            return None

    async def _extract_date(self, page: Page) -> Optional[date]:
        """从页面提取日期"""
        try:
            date_str = await page.text_content(THSRiskPageSource.DATE_SELECTOR)
            if date_str:
                # 尝试解析日期
                date_str = date_str.strip()
                for fmt in ["%Y-%m-%d", "%Y年%m月%d日", "%Y/%m/%d"]:
                    try:
                        return datetime.strptime(date_str, fmt).date()
                    except ValueError:
                        continue
        except Exception:
            pass
        return None

    async def _extract_risk_count(self, page: Page, selector: str, default: int = 0) -> int:
        """提取风险数量"""
        try:
            elements = await page.query_selector_all(selector)
            if elements:
                text = await elements[0].text_content()
                if text:
                    # 提取数字
                    numbers = re.findall(r'\d+', text)
                    if numbers:
                        return int(numbers[0])
        except Exception:
            pass
        return default

    async def _extract_from_table(self, page: Page) -> tuple:
        """从表格中提取风险数据

        Returns:
            tuple: (total_risk, no_risk, low_risk, medium_risk, high_risk)
        """
        try:
            rows = await page.query_selector_all(THSRiskPageSource.RISK_ROW_SELECTOR)
            total = 0
            no_risk = 0
            low_risk = 0
            medium_risk = 0
            high_risk = 0

            for row in rows:
                text = await row.text_content()
                if not text:
                    continue

                # 查找风险等级行
                text_lower = text.lower()
                if 'no risk' in text_lower or '无风险' in text:
                    numbers = self._extract_numbers(text)
                    if numbers:
                        no_risk = numbers[0]
                        total += no_risk
                elif 'low risk' in text_lower or '低风险' in text:
                    numbers = self._extract_numbers(text)
                    if numbers:
                        low_risk = numbers[0]
                        total += low_risk
                elif 'medium risk' in text_lower or '中等风险' in text:
                    numbers = self._extract_numbers(text)
                    if numbers:
                        medium_risk = numbers[0]
                        total += medium_risk
                elif 'high risk' in text_lower or '高风险' in text:
                    numbers = self._extract_numbers(text)
                    if numbers:
                        high_risk = numbers[0]
                        total += high_risk
                elif 'total' in text_lower or '总风险' in text:
                    numbers = self._extract_numbers(text)
                    if numbers:
                        total = numbers[0]

            return total, no_risk, low_risk, medium_risk, high_risk

        except Exception as e:
            logger.error(f"Error extracting from table: {e}")
            return 0, 0, 0, 0, 0

    def _extract_numbers(self, text: str) -> List[int]:
        """从文本中提取数字"""
        return [int(n) for n in re.findall(r'\d+', text)]

    async def health_check(self) -> bool:
        """健康检查

        Returns:
            bool: 服务是否可用
        """
        try:
            result = await self.get_financial_risk("600000")
            return True
        except Exception:
            return False
