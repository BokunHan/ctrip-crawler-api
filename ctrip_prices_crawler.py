import asyncio
import re
from datetime import datetime, date
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode


def extract_prices_from_markdown(markdown_content, url=""):
    """
    从加载后的markdown内容中，提取所有班期的价格信息
    """
    print("🎯 开始从markdown中提取价格日历...")

    product_id_match = re.search(r'productid=(\d+)', url, re.IGNORECASE)
    product_id = product_id_match.group(1) if product_id_match else ""

    prices = []
    current_year = ""
    current_month = ""
    today = date.today()
    lines = markdown_content.split('\n')

    calendar_loaded = any(re.search(r'\d{4}年\d{1,2}月', line) for line in lines)
    if not calendar_loaded:
        print("⚠️ 警告: 未在页面内容中找到价格日历结构。JS点击可能未成功。")
        return {"product_id": product_id, "prices": [],
                "metadata": {"extracted_at": datetime.now().isoformat(), "source_url": url,
                             "error": "Calendar data not found."}}

    for line in lines:
        line = line.strip()
        month_header_match = re.search(r'(\d{4})年(\d{1,2})月', line)
        if month_header_match:
            current_year, current_month = month_header_match.groups()
            current_month = current_month.zfill(2)
            continue

        price_line_match = re.search(r'(\d{1,2})¥(\d+)', line)
        if price_line_match and current_year and current_month:
            day, price_str = price_line_match.groups()
            day = day.zfill(2)

            try:
                current_date = date(int(current_year), int(current_month), int(day))
                if current_date < today:
                    continue

                prices.append({
                    "date": current_date.isoformat(),
                    "price": int(price_str)
                })
            except ValueError:
                continue

    print(f"✅ 价格提取完成！共找到 {len(prices)} 个有效班期。")
    return {"product_id": product_id, "prices": prices,
            "metadata": {"extracted_at": datetime.now().isoformat(), "source_url": url}}


async def crawl_and_extract_prices(url):
    """
    最终版: 使用JS内置延时来确保在稳定状态下执行点击
    """
    print(f"🚀 开始爬取价格日历 (0.7.4 最终兼容模式): {url}")

    browser_config = BrowserConfig(
        # browser_type="chromium",
        headless=True,
        # verbose=True,
        extra_args=['--disable-web-security']
        # user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E183 Safari/604.1"
    )

    # 唯一有效的延时参数是 delay_before_return_html
    # 我们将在JS内部处理前置延时
    crawl_config = CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS,
        delay_before_return_html=6.0,
        scan_full_page=True,
        log_console=True,
        verbose=True,
        js_code="""
            async function stableClick() {
                console.log('--- JS SCRIPT STARTED ---');
                
                // 关键步骤: 增加前置等待时间到5秒，确保所有事件监听器都已附加
                console.log('Waiting 3 seconds for page to fully stabilize...');
                await new Promise(resolve => setTimeout(resolve, 3000));
                console.log('Page should be stable now. Looking for button...');

                const targetButton = document.querySelector('.ScheduleDetailMoreText');
                if (targetButton) {
                    console.log('>>> Button FOUND. Simulating a real user click...');
                    
                    // 关键改动：创建一个真实的鼠标事件并派发它
                    const clickEvent = new MouseEvent('click', {
                        view: window,
                        bubbles: true,
                        cancelable: true
                    });
                    targetButton.dispatchEvent(clickEvent);
                    
                    console.log('>>> Click event dispatched!');
                } else {
                    console.log('!!! ERROR: Button .ScheduleDetailMoreText not found.');
                }
                console.log('--- JS SCRIPT FINISHED ---');
            }
            stableClick();
            """
    )

    async with AsyncWebCrawler(config=browser_config) as crawler:
        try:
            print("📱 正在加载页面并执行JS...")
            result = await crawler.arun(url=url, config=crawl_config)

            if result.success and result.markdown:
                print("✅ 页面爬取成功！")
                structured_data = extract_prices_from_markdown(result.markdown, url)
                return {"success": True, "data": structured_data}
            else:
                print(f"❌ 页面爬取失败: {result.error_message}")
                return {"success": False, "error": f"爬取失败: {result.error_message}"}

        except Exception as e:
            print(f"💥 爬取过程中发生异常: {str(e)}")
            return {"success": False, "error": f"发生异常: {str(e)}"}