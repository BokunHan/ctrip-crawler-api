import asyncio
import re
import json
from datetime import datetime
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode


def extract_reviews_from_markdown(markdown_content, url=""):
    """
    (正式版) 从markdown内容中提取结构化的评论数据

    此函数根据实际的 markdown 内容编写了详细的解析规则。
    """
    print("🎯 (正式版) 开始从markdown中提取评论数据...")

    # 尝试从URL中解析 product_id (即 queryid)
    product_id_match = re.search(r'queryid=(\d+)', url, re.IGNORECASE)
    product_id = product_id_match.group(1) if product_id_match else ""

    # 1. 初始化数据结构
    data = {
        "product_id": product_id,
        "rating": 0.0,
        "good_rate": "0",
        "rating_spec": {
            "itinerary": "0",
            "accommodation": "0",
            "service": "0"
        },
        "reviews": [],
        "metadata": {
            "extracted_at": datetime.now().isoformat(),
            "source_url": url
        }
    }

    # 2. 提取页面总评分
    # 5.0/5
    rating_match = re.search(r'(\d\.\d)/5', markdown_content)
    if rating_match:
        data["rating"] = float(rating_match.group(1))

    # 好评率100.0%
    good_rate_match = re.search(r'好评率(\d+\.\d+)%', markdown_content)
    if good_rate_match:
        data["good_rate"] = good_rate_match.group(1)

    # 提取三项详细评分
    # 行程安排
    # 酒店体验
    # 司导服务
    # 5.0
    # 5.0
    # 5.0
    spec_rating_match = re.search(
        r'行程安排\s*\n\s*酒店体验\s*\n\s*司导服务\s*\n\s*(\d\.\d)\s*\n\s*(\d\.\d)\s*\n\s*(\d\.\d)',
        markdown_content
    )
    if spec_rating_match:
        data["rating_spec"]["itinerary"] = spec_rating_match.group(1)
        data["rating_spec"]["accommodation"] = spec_rating_match.group(2)
        data["rating_spec"]["service"] = spec_rating_match.group(3)
    else:
        print("⚠️ 未找到详细评分模块")

    # 3. 逐行解析，提取每条评论
    lines = markdown_content.split('\n')

    # for line in lines:
    #     print(line)

    def remove_size_params(url):
        """去掉图片URL中的尺寸参数，获取大图"""
        # 去掉 _C_数字_数字_R1_Q80 这样的尺寸参数
        url = re.sub(r'_[A-Za-z]_\d+_\d+(_R\d+)?(_Q\d+)?', '', url)
        return url

    current_review = None
    i = 0
    while i < len(lines):
        line = lines[i].strip()

        # 检查是否为评论的起始点（用户头像）
        if line.startswith('![](') and 'webp?proc=resize/m_w,w_40,h_40,2B60' in line:
            # 如果上一条评论还未保存，先保存
            if current_review:
                data["reviews"].append(current_review)

            # 初始化一条新评论
            current_review = {
                "user_avatar": line.replace('![](', '').replace(')', ''),
                "user_name": "N/A",
                "rating": 0.0,
                "created_at": "",
                "location": "",
                "group_type": "",
                "travel_date": "",
                "route": "",
                "content": "",
                "images": [],
                "guide_name": "",
                "guide_photo": "",
                "helpful_count": 0
            }

            # 提取用户名 (头像后一行)
            if i + 1 < len(lines):
                current_review["user_name"] = lines[i + 1].strip()

            # 提取评分 (头像后三行)
            if i + 3 < len(lines):
                rating_match = re.search(r'(\d\.\d)分', lines[i + 3])
                if rating_match:
                    current_review["rating"] = float(rating_match.group(1))

            # 提取元数据 (头像后四行)
            # 格式: 2024-02-14发表于西藏家庭亲子2024-02-07出发日喀则口碑4钻+珠峰供氧房
            if i + 4 < len(lines):
                meta_line = lines[i + 4].strip()
                meta_match = re.search(r'(\d{4}-\d{2}-\d{2})发表于(\S+)(\S{4})(\d{4}-\d{2}-\d{2})出发(.+)', meta_line)
                if meta_match:
                    current_review["created_at"] = meta_match.group(1)
                    current_review["location"] = meta_match.group(2)
                    current_review["group_type"] = meta_match.group(3)
                    current_review["travel_date"] = meta_match.group(4)
                    current_review["route"] = meta_match.group(5)

            # 提取评论内容 (头像后五行)
            if i + 5 < len(lines):
                current_review["content"] = lines[i + 5].strip()

            # 跳过评论头信息，继续处理
            i += 6
            continue

        # 如果当前正在处理一条评论
        if current_review:
            # 提取评论图片
            if line.startswith('![](') and 'C_360_360_Q70' in line:
                image_url = line.replace('![](', '').replace(')', '')
                current_review["images"].append(remove_size_params(image_url))

            # 提取司导信息
            elif line == 'TA的司导：':
                if i + 1 < len(lines):
                    guide_line = lines[i + 1].strip()

                    # 提取司导头像和名字
                    guide_match = re.search(r'!\[\]\((.*?\.jpg)\)([^!]+)', guide_line)
                    if guide_match:
                        current_review["guide_photo"] = guide_match.group(1)
                        current_review["guide_name"] = guide_match.group(2)

                i += 1  # 跳过司导行

            # 检查评论结束标志（"有用"图标）
            elif line.startswith('![](') and '0303y120009qrdtd8387B' in line:
                if i + 1 < len(lines):
                    helpful_line = lines[i + 1].strip()

                    if helpful_line.isdigit():
                        # 如果是数字，直接转换
                        current_review["helpful_count"] = int(helpful_line)
                    elif helpful_line == "有用":
                        # 如果是 "有用" 文字，计为 0
                        current_review["helpful_count"] = 0
                    else:
                        # 兜底，万一格式是 "有用 10" 这种
                        count_match = re.search(r'(\d+)', helpful_line)
                        if count_match:
                            current_review["helpful_count"] = int(count_match.group(1))
                        else:
                            current_review["helpful_count"] = 0  # 默认 0

                data["reviews"].append(current_review)
                current_review = None  # 重置
                i += 1  # 跳过 "有用" 文本行
                continue  # 结束本次循环

        i += 1

    # 循环结束后，保存最后一条评论（如果存在）
    if current_review:
        data["reviews"].append(current_review)

    print(f"✅ (正式版) 提取完成！共找到 {len(data['reviews'])} 条评论。")

    # 移除临时的原始 markdown (如果存在)
    data.pop("raw_markdown_for_analysis", None)

    return data


async def crawl_and_extract_reviews(url):
    """
    爬取携程评论列表页面，自动滚动到底部，然后提取数据
    """
    print(f"🚀 开始爬取携程评论页面: {url}")

    # 模拟手机浏览器
    browser_config = BrowserConfig(
        browser_type="chromium",
        headless=True,
        viewport_width=375,
        viewport_height=812,
        user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
    )

    # 爬取配置 - 核心是 js_code
    crawl_config = CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS,
        page_timeout=240000,  # 延长超时到90秒，以应对大量评论的滚动
        delay_before_return_html=3.0,  # 滚动结束后，再等待3秒确保所有内容渲染
        log_console=True,  # 打印JS控制台日志，方便调试
        js_code="""
            async function scrollToBottomUntilEnd() {
                console.log('--- JS SCRIPT: 开始滚动加载评论... ---');
                let maxScrolls = 100;  // 最大滚动次数，防止无限循环
                let scrollCount = 0;
                let scrollDelay = 800; // 每次滚动后等待800毫秒

                while (scrollCount < maxScrolls) {
                    // 检查是否已出现 "已经到底啦"
                    if (document.body.innerText.includes("已经到底啦")) {
                        console.log('--- JS SCRIPT: 找到 "已经到底啦"。停止滚动。 ---');
                        break;
                    }
                    
                    // 滚动到底部
                    window.scrollBy(0, 1200);
                    await new Promise(resolve => setTimeout(resolve, scrollDelay));
                    
                    scrollCount++;
                    console.log(`--- JS SCRIPT: 滚动次数 ${scrollCount}/${maxScrolls} ---`);
                }

                if (scrollCount === maxScrolls) {
                    console.log('--- JS SCRIPT: 达到最大滚动次数。 ---');
                }
                
                console.log('--- JS SCRIPT: 滚动加载完成。 ---');
            }
            
            // 执行滚动函数
            await scrollToBottomUntilEnd();
            """
    )

    async with AsyncWebCrawler(config=browser_config) as crawler:
        try:
            print("📱 正在加载页面并执行JS滚动脚本...")
            result = await crawler.arun(url=url, config=crawl_config)

            if result.success and result.markdown:
                print("✅ 页面爬取成功 (已滚动到底部)！")
                # (!!!) 调用正式的解析函数
                structured_data = extract_reviews_from_markdown(result.markdown, url)
                return {"success": True, "data": structured_data}
            else:
                print(f"❌ 页面爬取失败: {result.error_message}")
                return {"success": False, "error": f"爬取失败: {result.error_message}"}

        except Exception as e:
            print(f"💥 爬取过程中发生异常: {str(e)}")
            return {"success": False, "error": f"发生异常: {str(e)}"}


async def main():
    """
    主函数 - 测试爬虫功能
    """
    # 使用你提供的示例URL
    test_url = "https://m.ctrip.com/webapp/vacations/order/public/comment_list?channel=vacations-grp&queryid=45584321&scene=PRODUCT_QUERY"

    print("🎯 携程评论爬虫测试开始")
    print(f"   URL: {test_url}")
    print("=" * 50)

    result = await crawl_and_extract_reviews(test_url)

    if result and result.get("success"):
        print("\n🎉 爬取测试完成！")

        # 将解析后的 JSON 结果保存到文件
        output_filename = "ctrip_review_data.json"
        with open(output_filename, 'w', encoding='utf-8') as f:
            json.dump(result['data'], f, ensure_ascii=False, indent=2)

        print(f"💾 解析后的 JSON 数据已保存到: {output_filename}")
        print("\n👉 你现在可以通过 `main.py` 的 `/api/reviews/{product_id}` 接口调用此功能了。")
    else:
        print(f"\n❌ 爬取测试失败: {result.get('error', '未知错误')}")


if __name__ == "__main__":
    asyncio.run(main())