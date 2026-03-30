#!/usr/bin/env python3
"""分析同花顺财务风险页面结构"""

import asyncio
import re
from playwright.async_api import async_playwright


async def main():
    """分析页面结构"""

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080},
        )
        page = await context.new_page()

        # 访问风险页面
        risk_url = "https://basic.10jqka.com.cn/600000/risk.html"
        print(f"访问: {risk_url}")
        response = await page.goto(risk_url, wait_until="networkidle", timeout=30000)
        print(f"状态: {response.status if response else 'None'}")

        # 等待JS渲染
        await asyncio.sleep(3)

        # 获取页面内容
        html = await page.content()
        print(f"页面长度: {len(html)} 字符")

        # 保存完整HTML
        with open('/tmp/ths_risk.html', 'w', encoding='utf-8') as f:
            f.write(html)
        print("HTML已保存到 /tmp/ths_risk.html")

        # 截图
        await page.screenshot(path='/tmp/ths_risk.png')

        # 查找风险相关内容
        print("\n=== 风险相关内容 ===")
        risk_keywords = ['风险', 'risk', 'Risk', '高风险', '中风险', '低风险', '无风险']
        for kw in risk_keywords:
            count = html.count(kw)
            if count > 0:
                print(f"  '{kw}': 出现 {count} 次")

        # 查找数字内容（风险评估通常是数字）
        print("\n=== 页面中的数字 ===")
        # 查找所有数字
        numbers = re.findall(r'\d+', html)
        unique_numbers = list(set(numbers))[:50]
        print(f"找到 {len(unique_numbers)} 个不同数字: {unique_numbers[:30]}")

        # 查找表格内容
        print("\n=== 表格内容 ===")
        tables = await page.query_selector_all('table')
        print(f"找到 {len(tables)} 个表格")

        for i, table in enumerate(tables[:3]):
            table_html = await table.inner_html()
            print(f"\n表格 {i}:")
            print(table_html[:500])

        # 查找特定class或id
        print("\n=== 查找class/id包含风险的元素 ===")
        risk_elements = await page.query_selector_all('[class*="risk"], [id*="risk"]')
        print(f"找到 {len(risk_elements)} 个元素")
        for el in risk_elements[:10]:
            cls = await el.get_attribute('class')
            id_attr = await el.get_attribute('id')
            text = await el.text_content()
            print(f"  class={cls}, id={id_attr}, text={text[:50] if text else 'None'}")

        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
