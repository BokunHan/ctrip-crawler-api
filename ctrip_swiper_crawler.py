import asyncio
import re
from datetime import datetime
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode


def extract_swiper_from_markdown(markdown_content, url=""):
    """
    从markdown内容中提取所有图片的URL地址
    """
    print("🎯 开始从markdown中提取图片URL...")

    # 尝试从URL中解析product_id
    product_id_match = re.search(r'productId=(\d+)', url, re.IGNORECASE)
    product_id = product_id_match.group(1) if product_id_match else ""

    # 使用正则表达式查找所有携程图片CDN的URL
    image_pattern = r'https?://dimg04\.c-ctrip\.com/images/[^)]+'
    image_urls = re.findall(image_pattern, markdown_content)

    # 清理URL，尝试获取高清大图并去除重复项
    cleaned_urls = set()
    for img_url in image_urls:
        # 移除常见的缩略图/尺寸参数
        cleaned_url = re.sub(r'_R_\d+_\d+.*\.', '.', img_url)
        cleaned_url = re.sub(r'_C_\d+_\d+.*\.', '.', cleaned_url)
        cleaned_url = re.sub(r'_W_\d+_\d+.*\.', '.', cleaned_url)
        cleaned_urls.add(cleaned_url)

    print(f"✅ 提取完成！共找到 {len(cleaned_urls)} 张不重复的图片。")

    # 返回结构化数据
    return {
        "product_id": product_id,
        "image_urls": list(cleaned_urls),
        "metadata": {
            "extracted_at": datetime.now().isoformat(),
            "source_url": url
        }
    }


async def crawl_and_extract_swiper(url):
    """
    爬取携程图片列表页面并提取所有图片
    """
    print(f"🚀 开始爬取携程图片列表页面: {url}")

    browser_config = BrowserConfig(
        browser_type="chromium",
        headless=True,
        user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
    )

    # 图片列表页面很可能也需要滚动来加载全部图片
    crawl_config = CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS,
        page_timeout=60000,  # 延长超时时间到60秒
        delay_before_return_html=5,  # 滚动结束后再等待5秒
        js_code="""
        async function fullScroll() {
            let maxScrolls = 40; // 允许滚动更多次以加载所有图片
            let scrollCount = 0;
            let scrollDelay = 800; // 每次滚动后等待800毫秒

            while (scrollCount < maxScrolls) {
                let beforeHeight = document.body.scrollHeight;
                window.scrollTo(0, beforeHeight);
                await new Promise(resolve => setTimeout(resolve, scrollDelay));
                let afterHeight = document.body.scrollHeight;
                // 如果页面高度不再增加，说明已到底部
                if (afterHeight <= beforeHeight) {
                    break;
                }
                scrollCount++;
            }
        }
        await fullScroll();
        """
    )

    async with AsyncWebCrawler(config=browser_config) as crawler:
        try:
            print("📱 正在爬取页面内容并模拟滚动...")
            result = await crawler.arun(url=url, config=crawl_config)

            if result.success and result.markdown:
                print("✅ 页面爬取成功！")
                structured_data = extract_swiper_from_markdown(result.markdown, url)
                return {"success": True, "data": structured_data}
            else:
                print(f"❌ 页面爬取失败: {result.error_message}")
                return {"success": False, "error": f"爬取失败: {result.error_message}"}

        except Exception as e:
            print(f"💥 爬取过程中发生异常: {str(e)}")
            return {"success": False, "error": f"发生异常: {str(e)}"}