import asyncio
import json
import re
from datetime import datetime
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode

def extract_product_data_from_markdown(markdown_content):
    """
    从markdown内容中提取结构化的商品数据
    """
    print("🎯 开始从markdown中提取结构化数据...")
    
    # 初始化数据结构
    product_data = {
        "product_id": "",
        "title": "",
        "subtitle": "",
        "route_title": "",
        "route_overview": {
            "accommodation": "",
            "activities": "",
            "meals": ""
        },
        "price": "",
        "product_images": [],  # 商品展示图（去掉尺寸参数的大图）
        "detail_images": [],   # 详情介绍图（保持原尺寸）
        "overview": {
            "guide": "",
            "transport": "",
            "activities": "",
            "accommodation": "",
            "meals": ""
        },
        "features": [],
        "cost_info": {
            "transport": "",
            "accommodation": "",
            "meals": "",
            "tickets": "",
            "service": ""
        }
    }
    
    lines = markdown_content.split('\n')

    # 0. 提取线路字母，并提取线路标题和概述
    route_letter_pattern = r'([A-Z])线'
    for i, line in enumerate(lines):
        line = line.strip()
        if not line:
            continue

        match = re.search(route_letter_pattern, line)
        if match:
            route_letter = match.group(1)
            for j in range(i + 1, len(lines)):
                next_line = lines[j].strip()
                if not next_line:
                    continue

                if next_line.startswith(f'{route_letter}线|'):
                    product_data["route_title"] = next_line
                    for k in range(j + 1, len(lines)):
                        next_line = lines[k].strip()
                        if not next_line:
                            continue
                        if "住" in next_line:
                            product_data["route_overview"]["accommodation"] = lines[k + 1]
                        elif "游" in next_line:
                            product_data["route_overview"]["activities"] = lines[k + 1]
                        elif "餐" in next_line:
                            product_data["route_overview"]["meals"] = lines[k + 1]
                            break

    title_pattern = r'.+\+.+私家团'
    subtitle_pattern = r'.+·.+'
    
    # 1. 提取商品ID和标题
    for i, line in enumerate(lines):
        # 提取商品ID (从URL中)
        if 'productid=' in line:
            match = re.search(r'productid=(\d+)', line)
            if match:
                product_data["product_id"] = match.group(1)
        
        # 提取标题 (通常是第一个较长的文本行)
        if not product_data["title"] and '+' in line:
            match = re.search(title_pattern, line.strip())
            if match:
                product_data["title"] = line.strip()
                # 寻找真正的副标题（景点列表）
                for j in range(i + 1, min(i + 10, len(lines))):
                    next_line = lines[j].strip()
                    # 副标题通常包含景点名称，用·分隔
                    if next_line and '·' in next_line:
                        match = re.search(subtitle_pattern, next_line)
                        if match:
                        # # 检查是否包含景点关键词
                        # if any(keyword in next_line for keyword in ['羊卓雍错', '珠峰', '陈塘沟', '卡若拉', '白居寺']):
                            product_data["subtitle"] = next_line
                            break
    
    # 2. 提取价格信息
    price_pattern = r'¥(\d+)'
    for line in lines:
        if '¥' in line and '星期' in line:
            matches = re.findall(price_pattern, line)
            if matches:
                product_data["price"] = f"¥{matches[0]}"
                break
    
    # 3. 提取并分类图片
    image_pattern = r'!\[\]\((https://dimg04\.c-ctrip\.com/images/[^)]+)\)'
    
    def remove_size_params(url):
        """去掉图片URL中的尺寸参数，获取大图"""
        # 去掉 _C_数字_数字_R1_Q80 这样的尺寸参数
        url = re.sub(r'_[A-Za-z]_\d+_\d+(_R\d+_Q\d+)?', '', url)
        return url
    
    def is_detail_image(url):
        """判断是否为商品展示图"""
        # 商品图特征：通常包含特定的尺寸参数，且在页面前部出现
        # 详情图特征：通常是.jpg格式，或者没有复杂的尺寸参数
        size_pattern = r'_[A-Za-z]_\d+_\d+'
        size_match = re.search(size_pattern, url)
        if size_match:
            return False
        if url.endswith('.jpg'):
            return True  # .jpg通常是详情图
        return False
    
    processed_images = set()  # 用于去重
    
    for line in lines:
        matches = re.findall(image_pattern, line)
        for original_url in matches:
            if original_url in processed_images:
                continue
            processed_images.add(original_url)
            
            if is_detail_image(original_url):
                # 详情图：保持原尺寸
                if original_url not in product_data["detail_images"]:
                    product_data["detail_images"].append(original_url)
            else:
                # 商品图：去掉尺寸参数保存大图
                large_url = remove_size_params(original_url)
                if large_url not in product_data["product_images"]:
                    product_data["product_images"].append(large_url)
    
    # 4. 提取线路总览信息 - 完整优化版本
    overview_section = False
    guide_info_parts = []  # 用于收集guide的完整信息
    transport_info_parts = []  # 用于收集交通的完整信息
    activities_info_parts = []  # 用于收集游玩的完整信息
    accommodation_info_parts = []  # 用于收集住宿的完整信息
    meals_info_parts = []  # 用于收集餐食的完整信息
    
    for i, line in enumerate(lines):
        if '线总览' in line:
            overview_section = True
            continue
        
        if overview_section and '产品特色' in line:
            overview_section = False
            break
            
        if overview_section:
            if '团队服务' in line:
                # 收集团队服务的完整信息
                guide_info_parts = []
                
                # 查找后续几行的详细描述
                for j in range(i+1, min(i+15, len(lines))):
                    desc_line = lines[j].strip()
                    
                    # 跳过空行和图片链接
                    if not desc_line or desc_line.startswith('!['):
                        continue
                    
                    # 收集基本服务描述
                    if '含司机服务' in desc_line:
                        guide_info_parts.append(desc_line)
                    
                    # 收集详细说明
                    elif '仅安排中文司机' in desc_line:
                        guide_info_parts.append(desc_line)
                    
                    # 收集司机信息
                    elif any(name in desc_line for name in ['刘华山', '彭亚平']) and '分' in desc_line:
                        guide_info_parts.append(desc_line)
                    
                    # 收集司机数量信息
                    elif '全部' in desc_line and '位' in desc_line:
                        guide_info_parts.append(desc_line)
                    
                    # 收集补充说明
                    elif '以上为近期带过本团的司机' in desc_line:
                        guide_info_parts.append(desc_line)
                        break  # 找到最后一条信息，结束收集
                
                # 将收集到的信息组合成完整的guide描述
                if guide_info_parts:
                    product_data["overview"]["guide"] = '; '.join(guide_info_parts)
                    
            elif '交通' in line:
                # 收集交通的完整信息
                transport_info_parts = []
                
                for j in range(i+1, min(i+8, len(lines))):
                    desc_line = lines[j].strip()
                    
                    # 跳过空行和图片链接
                    if not desc_line or desc_line.startswith('!['):
                        continue
                    
                    # 收集交通相关信息
                    if ('含行中专属用车' in desc_line or '不拼车' in desc_line or 
                        '经济' in desc_line and '座' in desc_line):
                        transport_info_parts.append(desc_line.replace('• ', ''))
                    
                    # 如果遇到下一个section，停止收集
                    if any(keyword in desc_line for keyword in ['游玩', '住宿', '餐食']):
                        break
                
                if transport_info_parts:
                    product_data["overview"]["transport"] = '; '.join(transport_info_parts)
                    
            elif '游玩' in line:
                # 收集游玩的完整信息
                activities_info_parts = []
                
                for j in range(i+1, min(i+8, len(lines))):
                    desc_line = lines[j].strip()
                    
                    # 跳过空行和图片链接
                    if not desc_line or desc_line.startswith('!['):
                        continue
                    
                    # 收集游玩相关信息
                    if ('个景点' in desc_line or '场馆' in desc_line or 
                        '儿童票' in desc_line or '无购物' in desc_line):
                        activities_info_parts.append(desc_line.replace('• ', ''))
                    
                    # 如果遇到下一个section，停止收集
                    if any(keyword in desc_line for keyword in ['住宿', '餐食', '团队服务']):
                        break
                
                if activities_info_parts:
                    product_data["overview"]["activities"] = '; '.join(activities_info_parts)
                    
            elif '住宿' in line:
                # 收集住宿的完整信息
                accommodation_info_parts = []
                
                for j in range(i+1, min(i+8, len(lines))):
                    desc_line = lines[j].strip()
                    
                    # 跳过空行和图片链接
                    if not desc_line or desc_line.startswith('!['):
                        continue
                    
                    # 收集住宿相关信息
                    if ('钻酒店' in desc_line or '平措康桑' in desc_line or 
                        '详情' in desc_line):
                        accommodation_info_parts.append(desc_line.replace('• ', ''))
                    
                    # 如果遇到下一个section，停止收集
                    if any(keyword in desc_line for keyword in ['餐食', '团队服务', '交通']):
                        break
                
                if accommodation_info_parts:
                    product_data["overview"]["accommodation"] = '; '.join(accommodation_info_parts)
                    
            elif '餐食' in line:
                # 收集餐食的完整信息
                meals_info_parts = []
                
                for j in range(i+1, min(i+8, len(lines))):
                    desc_line = lines[j].strip()
                    
                    # 跳过空行和图片链接
                    if not desc_line or desc_line.startswith('!['):
                        continue
                    
                    # 收集餐食相关信息
                    if ('成人' in desc_line and ('早餐' in desc_line or '晚餐' in desc_line or '自理' in desc_line)) or \
                       ('儿童' in desc_line and ('晚餐' in desc_line or '自理' in desc_line)):
                        meals_info_parts.append(desc_line.replace('• ', ''))
                    
                    # 如果遇到下一个section，停止收集
                    if any(keyword in desc_line for keyword in ['产品特色', '团队服务', '交通']):
                        break
                
                if meals_info_parts:
                    product_data["overview"]["meals"] = '; '.join(meals_info_parts)
    
    # 5. 提取产品特色
    features_section = False
    for i, line in enumerate(lines):
        if '产品特色' in line:
            features_section = True
            continue
        
        if features_section and ('5日行程' in line or 'D1|' in line):
            features_section = False
            break
            
        if features_section and line.strip() and not line.startswith('!['):
            # 特色通常以关键词开头，如"大牌驾到"、"精选酒店"等
            if any(keyword in line for keyword in ['大牌驾到', '精选酒店', '服务保障', '独特', '精选', '保障', '首选', '度假']):
                product_data["features"].append(line.strip())
    
    # 6. 提取费用信息 - 优化版本
    cost_section = False
    
    for i, line in enumerate(lines):
        if '费用信息' in line:
            cost_section = True
            continue
        
        if cost_section and '购买须知' in line:
            cost_section = False
            break
            
        if cost_section and '费用包含' in line:
            # 开始解析费用包含项目
            for j in range(i+1, min(i+20, len(lines))):
                cost_line = lines[j].strip()
                if not cost_line or cost_line.startswith('购买须知'):
                    break
                
                if cost_line == '交通':
                    # 获取下一行的详细信息
                    if j + 1 < len(lines):
                        detail = lines[j + 1].strip()
                        product_data["cost_info"]["transport"] = detail
                elif cost_line == '住宿':
                    if j + 1 < len(lines):
                        detail = lines[j + 1].strip()
                        product_data["cost_info"]["accommodation"] = detail
                elif cost_line == '餐食':
                    if j + 1 < len(lines):
                        detail = lines[j + 1].strip()
                        product_data["cost_info"]["meals"] = detail
                elif cost_line == '门票及地面项目':
                    if j + 1 < len(lines):
                        detail = lines[j + 1].strip()
                        product_data["cost_info"]["tickets"] = detail
                elif cost_line == '随团服务人员':
                    if j + 1 < len(lines):
                        detail = lines[j + 1].strip()
                        product_data["cost_info"]["service"] = detail
            break
    
    return product_data

async def crawl_and_extract_ctrip_data(url):
    """
    完整的携程手机版数据爬取和提取流程
    """
    print("🚀 启动携程手机版完整数据爬取器...")
    
    # 手机浏览器配置
    browser_config = BrowserConfig(
        # browser_type="chromium",
        headless=True,
        # verbose=True,
        # viewport_width=375,
        # viewport_height=812,
        # user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1"
        extra_args=['--disable-web-security']
    )
    
    # 爬取配置 - 针对手机版优化
    crawler_config = CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS,
        delay_before_return_html=8,  # 减少固定等待时间：10秒 -> 3秒
        page_timeout=30000,  # 减少超时时间：60秒 -> 30秒
        js_code=
            # 手机版滑动脚本 - 优化版本
            """
            // 手机版页面滑动加载 - 性能优化版
            async function mobileScrollOptimized() {
                let totalHeight = 0;
                let distance = 400;  // 增加滑动距离：300 -> 400
                let scrollDelay = 500;  // 减少滑动延迟：800ms -> 500ms
                let maxScrolls = 15;  // 限制最大滑动次数，避免无限滚动
                let scrollCount = 0;

                console.log('开始优化滑动加载...');

                while (totalHeight < document.body.scrollHeight && scrollCount < maxScrolls) {
                    let beforeHeight = document.body.scrollHeight;
                    window.scrollBy(0, distance);
                    totalHeight += distance;
                    scrollCount++;

                    // 动态调整等待时间
                    await new Promise(resolve => setTimeout(resolve, scrollDelay));

                    // 检查是否有新内容加载
                    let afterHeight = document.body.scrollHeight;
                    if (afterHeight === beforeHeight) {
                        // 如果页面高度没有变化，说明没有新内容，可以提前结束
                        console.log('页面内容已全部加载，提前结束滚动');
                        break;
                    }

                    // 如果连续3次滚动都没有新内容，则结束
                    if (totalHeight >= afterHeight) {
                        console.log('已滚动到页面底部');
                        break;
                    }
                }

                console.log(`滚动完成，共滚动${scrollCount}次`);

                // 滚动到顶部，减少等待时间
                window.scrollTo(0, 0);
                await new Promise(resolve => setTimeout(resolve, 500));  // 减少等待：1000ms -> 500ms
            }

            await mobileScrollOptimized();
            """
    )
    
    async with AsyncWebCrawler(config=browser_config) as crawler:
        print(f"📱 开始爬取手机版页面: {url}")
        
        result = await crawler.arun(
            url=url,
            config=crawler_config,
        )
        
        if result.success:
            print("✅ 页面爬取成功!")
            
            # 生成时间戳
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # # 保存原始HTML文件
            # html_file = f"ctrip_mobile_html_{timestamp}.html"
            # with open(html_file, 'w', encoding='utf-8') as f:
            #     f.write(result.html)
            # print(f"💾 HTML文件已保存: {html_file}")
            
            # # 保存Markdown文件
            # markdown_file = f"ctrip_mobile_markdown_{timestamp}.md"
            # with open(markdown_file, 'w', encoding='utf-8') as f:
            #     f.write(result.markdown)
            # print(f"📝 Markdown文件已保存: {markdown_file}")
            
            # 提取结构化数据
            print("🎯 开始提取结构化数据...")
            product_data = extract_product_data_from_markdown(result.markdown)
            
            # # 保存结构化JSON数据
            # json_file = f"ctrip_product_data_{timestamp}.json"
            # with open(json_file, 'w', encoding='utf-8') as f:
            #     json.dump(product_data, f, ensure_ascii=False, indent=2)
            # print(f"📊 结构化数据已保存: {json_file}")
            
            # 打印提取结果摘要
            print("\n🎯 数据提取摘要:")
            print(f"商品ID: {product_data['product_id']}")
            print(f"标题: {product_data['title']}")
            print(f"价格: {product_data['price']}")
            print(f"商品图数量: {len(product_data['product_images'])}")
            print(f"详情图数量: {len(product_data['detail_images'])}")
            print(f"特色数量: {len(product_data['features'])}")
            
            return {
                "success": True,
                # "html_file": html_file,
                # "markdown_file": markdown_file,
                # "json_file": json_file,
                "product_data": product_data
            }
        else:
            print(f"❌ 页面爬取失败: {result.error_message}")
            return {"success": False, "error": result.error_message}

async def main():
    """
    主函数 - 执行完整的爬取流程
    """
    # 携程手机版商品详情页URL
    url = "https://m.ctrip.com/webapp/xtour/detail?rv=1&productid=61162192&departcityid=41&frompc=1&isRedirect=tour_h5"
    
    print("🎯 携程手机版商品详情爬虫 v3.0")
    print("=" * 50)
    
    result = await crawl_and_extract_ctrip_data(url)
    
    if result["success"]:
        print("\n✅ 爬取任务完成!")
        # print(f"📁 生成文件:")
        # print(f"  - HTML: {result['html_file']}")
        # print(f"  - Markdown: {result['markdown_file']}")
        # print(f"  - JSON: {result['json_file']}")
        print("\n🎉 所有核心数据已成功提取!")
    else:
        print(f"\n❌ 爬取失败: {result['error']}")

if __name__ == "__main__":
    asyncio.run(main()) 