#!/usr/bin/env python3
"""同花顺财务风险爬虫 - 使用增强的反反爬虫措施"""

import asyncio
from playwright.async_api import async_playwright


async def main():
    """使用增强措施爬取同花顺风险页面"""

    async with async_playwright() as p:
        # 启动带更多参数的浏览器
        browser = await p.chromium.launch(
            headless=True,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-infobars',
                '--disable-extensions',
                '--disable-gpu',
                '--window-size=1920,1080',
            ]
        )

        # 创建更真实的浏览器上下文
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080},
            locale="zh-CN",
            timezone_id="Asia/Shanghai",
            permissions=["geolocation"],
            ignore_https_errors=True,
        )

        # 阻止webdriver检测
        await context.add_init_script("""
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

        page = await context.new_page()

        # 拦截请求，查看是否有API调用
        api_requests = []
        page.on("response", lambda response: api_requests.append({
            "url": response.url,
            "status": response.status
        }) if "risk" in response.url.lower() or "api" in response.url.lower() else None)

        print("1. 先访问同花顺主页...")
        await page.goto("https://www.10jqka.com.cn/", wait_until="domcontentloaded", timeout=30000)
        await asyncio.sleep(3)

        print("2. 直接访问股票风险数据URL...")
        # 尝试不同的URL格式
        test_urls = [
            "https://stockpage.10jqka.com.cn/600000/risk/",
            "https://basic.10jqka.com.cn/600000/risk.html",
            "https://vip.10jqka.com.cn/600000/risk/",
        ]

        for test_url in test_urls:
            print(f"\n测试: {test_url}")
            try:
                response = await page.goto(test_url, wait_until="networkidle", timeout=30000)
                print(f"  状态: {response.status if response else 'None'}")
                await asyncio.sleep(2)

                content = await page.content()
                print(f"  内容长度: {len(content)}")

                if len(content) > 1000:
                    print(f"  内容预览: {content[:500]}")

                    # 保存完整内容
                    filename = test_url.split('/')[-2] + '.html'
                    with open(f'/tmp/{filename}', 'w', encoding='utf-8') as f:
                        f.write(content)
                    print(f"  已保存到 /tmp/{filename}")

                    # 截图
                    await page.screenshot(path=f'/tmp/{filename.replace(".html", ".png")}')
                    print(f"  截图已保存")

            except Exception as e:
                print(f"  错误: {e}")

        # 打印拦截到的API请求
        print(f"\n3. 拦截到的相关请求 ({len(api_requests)}个):")
        for req in api_requests[:20]:
            print(f"  {req['status']}: {req['url'][:100]}")

        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
