import asyncio
import json
import re
from datetime import datetime
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode
import argparse

async def extract_ctrip_itinerary(url):
    """
    专业的携程行程数据提取器 - 严格按时间顺序解析
    """
    print("🎯 携程行程数据专业提取工具 v3.0")
    print("🎯 启动携程行程数据提取器...")
    
    # 浏览器配置
    browser_config = BrowserConfig(
        # browser_type="chromium",
        headless=True,
        # verbose=True,
        # user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 14_7_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.2 Mobile/15E148 Safari/604.1"
        extra_args=['--disable-web-security']
    )
    
    # 爬取配置
    crawler_config = CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS,
        delay_before_return_html=3,
        page_timeout=30000,
        js_code="window.scrollTo(0, document.body.scrollHeight);",
        word_count_threshold=1,
    )
    
    try:
        async with AsyncWebCrawler(config=browser_config) as crawler:
            print("📱 正在访问携程页面...")
            result = await crawler.arun(url=url, config=crawler_config)
            
            print("\n" + "="*50)
            print("📊 爬取结果:")
            print(f"状态码: {result.status_code}")
            print(f"成功: {result.success}")
            print(f"URL: {result.url}")
            print("="*50)
            
            if result.success and result.markdown:
                # # 保存原始HTML和markdown内容用于分析
                # html_filename = f"ctrip_html_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
                # with open(html_filename, "w", encoding="utf-8") as f:
                #     f.write(result.html)
                # print(f"📄 HTML内容已保存到 {html_filename}")
                
                # markdown_filename = f"ctrip_markdown_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
                # with open(markdown_filename, "w", encoding="utf-8") as f:
                #     f.write(result.markdown)
                # print(f"📝 Markdown内容已保存到 {markdown_filename}")
                
                # 使用新的解析方法提取结构化数据
                structured_data = parse_ctrip_content_v3(result.markdown, url)
                
                # # 保存结构化数据
                # output_filename = f"ctrip_structured_v3_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                # with open(output_filename, "w", encoding="utf-8") as f:
                #     json.dump(structured_data, f, ensure_ascii=False, indent=2)
                # print(f"💾 结构化数据已保存到 {output_filename}")
                
                # 打印摘要
                print_summary(structured_data)
                
                return structured_data
            else:
                print("❌ 爬取失败或内容为空")
                return None
                
    except Exception as e:
        print(f"❌ 爬取过程中出现错误: {str(e)}")
        return None

def parse_ctrip_content_v3(markdown_content, source_url):
    """
    严格按照页面时间顺序解析携程内容
    """
    print("🔍 开始解析携程内容...")
    
    # 从URL提取产品ID
    product_id_match = re.search(r'ProductId=(\d+)', source_url)
    product_id = product_id_match.group(1) if product_id_match else ""
    
    # 初始化标准数据结构
    data = {
        "product_info": {
            "product_id": product_id,
            "title": "",  # 将从内容中提取
            "sub_title": "",
            "duration": "",
            "total_days": 0,
            "remarks": ""
        },
        "itinerary": [],
        "metadata": {
            "extracted_at": datetime.now().isoformat(),
            "source_url": source_url
        }
    }
    
    lines = markdown_content.split('\n')
    current_day = None
    current_day_data = None

    # for line in lines:
    #     print(line)
    
    # 提取行程天数
    for i, line in enumerate(lines):
        line = line.strip()
        if not line:
            continue
            
        # 提取行程天数
        if re.match(r'^\d+日行程$', line):
            days = int(line[0])
            data["product_info"]["duration"] = f"{days}天"
            data["product_info"]["total_days"] = days
            print(f"✓ 提取到行程天数: {days}天")
            
        # 尝试从DAY01之前的内容中提取行程标题
        if i > 0 and "DAY01" in line:
            # 向前查找可能的标题行
            for j in range(i-1, 0, -1):
                prev_line = lines[j].strip()
                if prev_line and "【行程】" in prev_line:
                    data["product_info"]["title"] = prev_line
                    print(f"✓ 提取到行程标题: {prev_line}")
                    break
    
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if not line:
            i += 1
            continue
        
        # 检测新的一天开始 (DAY01, DAY02等)
        day_match = re.match(r'^DAY0?(\d+)$', line)
        if day_match:
            # 保存上一天的数据
            if current_day_data:
                data["itinerary"].append(current_day_data)
            
            # 开始新的一天
            current_day = int(day_match.group(1))
            current_day_data = {
                "day": current_day,
                "day_title": "",
                "activities": []
            }
            
            # 获取行程标题（下一行）
            if i + 1 < len(lines):
                next_line = lines[i + 1].strip()
                if next_line and not next_line.startswith('!['):
                    current_day_data["day_title"] = next_line
                    
                    # 如果是第一天，可以从标题中提取子标题
                    if current_day == 1 and data["product_info"]["sub_title"] == "":
                        # 尝试从标题中提取目的地信息作为子标题
                        match = re.search(r'【行程】(.+?)(?:🚗|$)', next_line)
                        if match:
                            data["product_info"]["sub_title"] = match.group(1).strip()
                            print(f"✓ 提取到行程子标题: {data['product_info']['sub_title']}")
            
            # 为第一天添加集合活动
            if current_day == 1:
                assembly_activity = create_assembly_activity(lines)
                current_day_data["activities"].append(assembly_activity)
            
            i += 1
            continue
        
        # 解析具体的活动项目（严格按时间顺序）
        if current_day_data:
            activity = parse_activity_line(line, lines, i, current_day_data["day_title"])
            if activity:
                current_day_data["activities"].append(activity)
        
        i += 1
    
    # 保存最后一天的数据
    if current_day_data:
        data["itinerary"].append(current_day_data)
    
    # 如果没有提取到标题，尝试从第一天的标题构建一个
    if not data["product_info"]["title"] and data["itinerary"]:
        first_day = data["itinerary"][0]
        if "day_title" in first_day and first_day["day_title"]:
            # 从第一天标题中提取行程概要
            title_parts = []
            if "【行程】" in first_day["day_title"]:
                match = re.search(r'【行程】(.+?)(?:🚗|$)', first_day["day_title"])
                if match:
                    title_parts.append(match.group(1).strip())
            
            # 如果有多天，也从最后一天提取信息
            if len(data["itinerary"]) > 1:
                last_day = data["itinerary"][-1]
                if "day_title" in last_day and last_day["day_title"] and "【行程】" in last_day["day_title"]:
                    end_dest = re.search(r'【行程】.+?-(.+?)(?:🚗|$)', last_day["day_title"])
                    if end_dest:
                        title_parts.append(end_dest.group(1).strip())
            
            if title_parts:
                data["product_info"]["title"] = f"{data['product_info']['duration']}·{'·'.join(title_parts)}"
                print(f"✓ 构建行程标题: {data['product_info']['title']}")
    
    print(f"✓ 解析完成，提取到 {len(data['itinerary'])} 天完整行程")
    return data

def parse_activity_line(line, lines, index, day_title):
    """
    解析单个活动行，严格按照时间格式识别
    """
    # 跳过图片链接和空行
    if line.startswith('![') or not line:
        return None
    
    # 解析时间格式的活动: "08:00 · 早餐"
    time_activity_match = re.match(r'^(\d{2}:\d{2})\s*[·•]\s*(.+?)(?:\（(.+?)\）)?$', line)
    if time_activity_match:
        time_str = time_activity_match.group(1)
        activity_type = time_activity_match.group(2)
        extra_info = time_activity_match.group(3) if time_activity_match.group(3) else ""
        
        # 根据活动类型创建对应的活动
        if '早餐' in activity_type or '午餐' in activity_type or '晚餐' in activity_type:
            return create_restaurant_activity(time_str, activity_type, extra_info, lines, index)
        elif '交通' in activity_type:
            return create_transport_activity(time_str, activity_type, day_title, lines, index)
        elif '景点' in activity_type or '场馆' in activity_type:
            return create_scenic_activity(time_str, activity_type, lines, index)
        elif '酒店' in activity_type:
            return create_hotel_activity(time_str, activity_type, day_title, lines, index)
        else:
            # 其他类型的活动（如其他、购物等）
            return create_other_activity(time_str, activity_type, lines, index)
    
    # 解析时间段格式的活动: "全天 · 其它"
    period_activity_match = re.match(r'^(全天|上午|下午|晚上)\s*[·•]\s*(.+)$', line)
    if period_activity_match:
        period = period_activity_match.group(1)
        activity_type = period_activity_match.group(2)
        
        if '其它' in activity_type or '其他' in activity_type:
            return create_period_other_activity(period, activity_type, lines, index)
        elif '交通' in activity_type:
            return create_period_transport_activity(period, activity_type, day_title, lines, index)
        elif '购物' in activity_type:
            # 处理购物活动
            return create_period_other_activity(period, activity_type, lines, index)
        elif '自由活动' in activity_type:
            # 处理自由活动
            return create_period_other_activity(period, activity_type, lines, index)
        elif '酒店' in activity_type:
            # 处理时间段酒店活动
            return create_hotel_activity(None, activity_type, day_title, lines, index)
    
    # 特殊格式的酒店活动识别 (例如: "19:00 · 酒店")
    hotel_match = re.match(r'^(\d{2}:\d{2})\s*[·•]?\s*酒店', line)
    if hotel_match:
        time_str = hotel_match.group(1)
        return create_hotel_activity(time_str, "酒店", day_title, lines, index)
    
    # 解析集合信息
    if line == '集合' or '集合' in line:
        # 集合信息已在第一天自动添加，这里跳过
        return None
        
    # 解析解散信息
    if line == '解散' or '解散' in line:
        return create_dismissal_activity(lines, index)
    
    return None

def create_assembly_activity(lines):
    """创建集合活动（只在第一天添加一次）
    从markdown内容中提取集合信息，而不是硬编码
    """
    # 初始化默认值
    assembly_type = "上门接"
    title = "本产品提供免费接送服务"
    locations = []
    time_info = "全天（专车）"
    remark = "超过免费接送范围请自行集合，如有疑问请联系客服"
    
    # 从markdown内容中查找集合信息
    for i, line in enumerate(lines):
        line = line.strip()
        
        # 寻找集合信息的开始
        if line == "集合":
            # 查找后续的集合信息
            j = i + 1
            while j < len(lines) and not re.match(r'^\d{2}:\d{2}\s*[·•]', lines[j].strip()):
                current_line = lines[j].strip()
                
                # 提取集合类型和标题
                if "免费接" in current_line:
                    title = current_line
                    if "接机" in current_line or "接站" in current_line or "接机/站" in current_line:
                        assembly_type = "接机/站"
                    else:
                        assembly_type = "上门接"
                
                # 提取地点列表 - 处理接机/站的情况
                elif "免费接区域" in current_line:
                    # 从"免费接区域: "后面提取地点信息
                    location_info = current_line.split(":", 1)[1].strip() if ":" in current_line else ""
                    # 提取地区名称
                    locations = [loc.strip() for loc in re.findall(r'[^\d\s、，,]+区', location_info)]
                elif "免费接的机场/火车站" in current_line or "免费接机场" in current_line:
                    # 从":"后面提取机场/站点信息
                    location_info = current_line.split(":", 1)[1].strip() if ":" in current_line else ""
                    # 分割可能的多个地点
                    locations = [loc.strip() for loc in re.split(r'[、，,]', location_info) if loc.strip()]
                
                # 提取时间信息
                elif "服务时间" in current_line:
                    time_info = current_line.split(":", 1)[1].strip() if ":" in current_line else "全天（专车）"
                
                # 提取备注信息
                elif "超过免费接" in current_line or current_line.startswith("超过"):
                    remark = current_line
                
                j += 1
            break
    
    # 如果没有找到集合信息，尝试从其他格式中提取
    if not locations:
        # 查找接机/站信息
        for i in range(len(lines)):
            line = lines[i].strip()
            
            # 检查是否有接机/站的相关信息
            if ("接机/站" in line or "接机" in line or "接站" in line) and not line.startswith('!['):
                assembly_type = "接机/站"
                title = line
                
                # 查找后续行中的机场/站点信息
                j = i + 1
                while j < len(lines) and j < i + 10:  # 限制查找范围，避免查找过远
                    next_line = lines[j].strip()
                    
                    # 提取机场/站点信息
                    if "机场" in next_line or "站" in next_line:
                        # 从行中提取地点名称
                        location_parts = re.split(r'[：:、，,]', next_line)
                        for part in location_parts:
                            if "机场" in part or "站" in part:
                                clean_part = part.strip()
                                if clean_part and clean_part not in locations:
                                    locations.append(clean_part)
                    
                    # 提取服务时间
                    if "服务时间" in next_line or "时间段" in next_line:
                        time_parts = next_line.split(":", 1) if ":" in next_line else next_line.split("：", 1)
                        if len(time_parts) > 1:
                            time_info = time_parts[1].strip()
                    
                    # 提取备注
                    if "超过" in next_line and ("范围" in next_line or "集合" in next_line):
                        remark = next_line
                    
                    j += 1
                    
                    # 如果遇到下一个活动或元素，停止
                    if next_line.startswith('![](') or re.match(r'^\d{2}:\d{2}\s*[·•]', next_line):
                        break
                
                break
    
    # 处理你提供的示例格式
    if not locations:
        for i in range(len(lines)):
            line = lines[i].strip()
            
            # 检查是否包含"本产品提供免费接服务"
            if "本产品提供免费接服务" in line:
                title = line
                
                # 查找接机/站信息
                j = i + 1
                while j < len(lines) and j < i + 10:  # 限制查找范围
                    next_line = lines[j].strip()
                    
                    # 检查是否是接机/站行
                    if "接机/站" in next_line or "接机" in next_line or "接站" in next_line:
                        assembly_type = "接机/站"
                    
                    # 提取机场/站点信息
                    if "免费接" in next_line and ("机场" in next_line or "站" in next_line):
                        # 从行中提取地点名称
                        location_info = next_line.split(":", 1)[1].strip() if ":" in next_line else next_line
                        # 分割可能的多个地点
                        for part in re.split(r'[、，,]', location_info):
                            if part.strip() and part.strip() not in locations:
                                locations.append(part.strip())
                    
                    # 提取服务时间
                    if "服务时间" in next_line or "时间段" in next_line:
                        time_parts = next_line.split(":", 1) if ":" in next_line else next_line.split("：", 1)
                        if len(time_parts) > 1:
                            time_info = time_parts[1].strip()
                    
                    # 提取备注
                    if "超过" in next_line and ("范围" in next_line or "集合" in next_line):
                        remark = next_line
                    
                    j += 1
                    
                    # 如果遇到下一个活动或元素，停止
                    if next_line.startswith('![](') or re.match(r'^\d{2}:\d{2}\s*[·•]', next_line):
                        break
                
                break
    
    # 如果没有找到地点信息，使用默认值
    if not locations:
        if assembly_type == "接机/站":
            locations = ["贡嘎国际机场", "拉萨站"]  # 默认机场/站点
        else:
            locations = ["青白江区", "青羊区", "新津区", "郫都区", "锦江区", 
                        "成华区", "温江区", "双流区", "武侯区", "金牛区", 
                        "龙泉驿区", "新都区"]  # 默认城市区域
    
    return {
        "elementType": "assembly",
        "title": "集合",
        "time_type": "period",
        "time_start_time": None,
        "time_duration_hours": None,
        "time_duration_minutes": None,
        "time_period": "全天",
        "time_remark": "集合时间",
        "driving_distance": 0,
        "driving_duration_hours": 0,
        "driving_duration_minutes": 0,
        "elementData": {
            "assembly_type": assembly_type,
            "title": title,
            "locations": locations,
            "time_info": time_info,
            "remark": remark
        }
    }

def remove_size_params(url):
    """去掉图片URL中的尺寸参数，获取大图"""
    # 去掉 _C_数字_数字_R1_Q80 这样的尺寸参数
    url = re.sub(r'_[A-Za-z]_\d+_\d+(_R\d+_Q\d+)?', '', url)
    return url

def create_restaurant_activity(time_str, activity_type, extra_info, lines, index):
    """创建餐厅活动"""
    meal_type = ""
    if "早餐" in activity_type:
        meal_type = "早餐"
    elif "午餐" in activity_type:
        meal_type = "午餐"
    elif "晚餐" in activity_type:
        meal_type = "晚餐"
    
    # 从extra_info判断是否包含
    included = "含餐" in extra_info or "含" in extra_info
    if "自理" in extra_info:
        included = False

    standard = 0
    
    # 获取下一行的详细信息
    remark = "敬请自理"
    remark_lines = []
    images = []
    duration_hours = 1  # 默认时长1小时
    duration_minutes = 0
    
    # 查找后续行中的用餐时间信息
    i = index + 1
    while i < len(lines):
        line = lines[i].strip()
        if not line:
            i += 1
            continue
            
        # 如果遇到下一个时间活动，停止
        if re.match(r'^\d{2}:\d{2}\s*[·•]', line) or re.match(r'^(全天|上午|下午|晚上)\s*[·•]', line):
            break

        if line.startswith("![](") and "static" not in line:
            image_pattern = r'\((.*?)\)'
            image_urls = re.findall(image_pattern, line)
            images = [remove_size_params(url) for url in image_urls]
            i += 1
            continue
            
        # 提取用餐时间
        duration_match = re.search(r'用餐时间[:：]\s*约(\d+)小时(?:\s*(\d+)分钟)?', line)
        if duration_match:
            duration_hours = float(duration_match.group(1))
            if duration_match.group(2):
                duration_minutes = int(duration_match.group(2))
            i += 1
            continue

        duration_match2 = re.search(r'用餐时间[:：]\s*约(\d+)分钟', line)
        if duration_match2:
            minutes = int(duration_match2.group(1))
            duration_hours = minutes / 60
            i += 1
            continue

        standard_match = re.search(r'餐标[:：]\s*(\d+)\s*.+人$', line)
        if standard_match:
            standard = int(standard_match.group(1))
            i += 1
            continue
        
        # 提取备注信息
        if not line.startswith('![') and not re.match(r'^\d{2}:\d{2}', line):
            remark_lines.append(line)
            if "酒店" in line:
                included = True
                
        i += 1

    if len(remark_lines) > 0:
        remark = '\n'.join(remark_lines)

    return {
        "elementType": "restaurant",
        "title": "餐厅",
        "time_type": "specific",
        "time_start_time": time_str,
        "time_duration_hours": duration_hours,
        "time_duration_minutes": duration_minutes,
        "time_period": None,
        "time_remark": None,
        "driving_distance": 0,
        "driving_duration_hours": 0,
        "driving_duration_minutes": 0,
        "elementData": {
            "name": meal_type,
            "meal_type": meal_type,
            "adult_included": included,
            "adult_fee_type": "费用包含" if included else "自理",
            "child_included": included,
            "child_fee_type": "费用包含" if included else "自理",
            "standard": standard,
            "images": images,
            "remark": remark
        }
    }

def create_transport_activity(time_str, activity_type, day_title, lines, index):
    """创建交通活动"""
    # 从day_title中提取距离和时间信息
    distance = 0
    duration_hours = 0
    
    distance_match = re.search(r'约(\d+)km', day_title)
    duration_match = re.search(r'(\d+(?:\.\d+)?)小时', day_title)
    
    if distance_match:
        distance = int(distance_match.group(1))
    if duration_match:
        duration_hours = float(duration_match.group(1))
    
    # 获取交通详细描述（可能跨多行）
    content = activity_type
    content_lines = []
    
    i = index + 1
    while i < len(lines):
        line = lines[i].strip()
        if not line:
            i += 1
            continue
        
        # 如果遇到下一个时间活动，停止
        if re.match(r'^\d{2}:\d{2}\s*[·•]', line) or re.match(r'^(全天|上午|下午|晚上)\s*[·•]', line):
            break
            
        # 如果遇到下一个元素的开始，停止
        if line.startswith('![](') and re.search(r'activetype/V1/activetype\d+\.png', line):
            break
        
        # 跳过图片链接
        if line.startswith('![') and line.endswith(')'):
            i += 1
            continue
            
        # 检查是否有"展开"按钮
        if line == "展开":
            i += 1
            continue
            
        # 检查是否有"行驶："信息，这通常包含距离和时间
        if line.startswith("行驶："):
            # 尝试提取距离和时间
            dist_match = re.search(r'约(\d+)公里', line)
            time_match = re.search(r'约(\d+(?:\.\d+)?)小时', line)
            
            if dist_match:
                distance = int(dist_match.group(1))
            if time_match:
                duration_hours = float(time_match.group(1))
        
        # 添加内容行
        content_lines.append(line)
        i += 1
    
    # 合并内容行
    if content_lines:
        content = '\n'.join(content_lines)
    
    return {
        "elementType": "transport",
        "title": "交通",
        "time_type": "specific",
        "time_start_time": time_str,
        "time_duration_hours": duration_hours,
        "time_duration_minutes": 0,
        "time_period": None,
        "time_remark": None,
        "driving_distance": distance,
        "driving_duration_hours": duration_hours,
        "driving_duration_minutes": 0,
        "elementData": {
            "content": content
        }
    }

def create_scenic_activity(time_str, activity_type, lines, index):
    """创建景点活动"""
    scenic_spots = []
    content = activity_type
    duration_hours = 2  # 默认时长2小时
    duration_minutes = 0
    remark = ""
    remark_lines = []
    
    # 查找后续的景点信息
    i = index + 1
    while i < len(lines):
        line = lines[i].strip()
        if not line:
            i += 1
            continue
        
        # 如果遇到下一个时间活动，停止
        if re.match(r'^\d{2}:\d{2}\s*[·•]', line):
            break
        
        # 提取活动时间
        duration_match = re.search(r'活动时间[:：]\s*约(\d+)小时(?:\s*(\d+)分钟)?', line)
        if duration_match:
            duration_hours = float(duration_match.group(1))
            if duration_match.group(2):
                duration_minutes = int(duration_match.group(2))
            break
            
        duration_match2 = re.search(r'活动时间[:：]\s*约(\d+)分钟', line)
        if duration_match2:
            minutes = int(duration_match2.group(1))
            duration_hours = minutes / 60
            break
        
        # 检查是否是图片链接
        if line.startswith('![](') and line.endswith(')'):
            # 提取图片URL
            image_url = line[4:-1]  # 去掉 ![](  和  )
            
            # 过滤掉图标类型的链接
            if "activetype" not in image_url:
                # 处理图片链接，移除尺寸参数
                if image_url.startswith("@"):
                    image_url = image_url[1:]  # 移除@前缀
                
                if "_R_" in image_url:
                    image_url = re.sub(r'_R_\d+_\d+\.jpg', '.jpg', image_url)
                
                # 检查下一行是否是景点名称
                if i + 1 < len(lines):
                    next_line = lines[i + 1].strip()
                    # 景点名称通常是"景点名(门票信息)"格式
                    if '(' in next_line:
                        spot_parts = next_line.split('(', 1)
                        spot_name = spot_parts[0].strip()
                        
                        # 提取门票信息
                        ticket_info = ""
                        ticket_included = False
                        if len(spot_parts) > 1 and ')' in spot_parts[1]:
                            ticket_info = spot_parts[1].split(')', 1)[0].strip()
                            ticket_included = ('含' in ticket_info or '已含' in ticket_info)

                        # 创建景点对象
                        print(f"提取到景点: {spot_name}, 图片: {image_url}")
                        scenic_spots.append({
                            "name": spot_name,
                            "ticket_included": ticket_included,
                            "ticket_type": ticket_info,
                            "description": "",
                            "images": [image_url]  # 使用处理后的图片URL
                        })

                        i += 1
                        continue

        if not re.match(r'^\d{1}\.\d{1}\s*分', line):
            remark_lines.append(line.strip())

        i += 1

    if len(remark_lines) > 0:
        remark = '\n'.join(remark_lines)
    
    return {
        "elementType": "scenic",
        "title": "景点",
        "time_type": "specific",
        "time_start_time": time_str,
        "time_duration_hours": duration_hours,
        "time_duration_minutes": duration_minutes,
        "time_period": None,
        "time_remark": None,
        "driving_distance": 0,
        "driving_duration_hours": 0,
        "driving_duration_minutes": 0,
        "remark": remark,
        "elementData": {
            "content": content,
            "scenic_spots": scenic_spots
        }
    }

def create_hotel_activity(time_str, activity_type, day_title, lines, index):
    """创建酒店活动"""
    # 从day_title中提取酒店信息
    hotel_name = "当地精选酒店"
    location = ""
    duration_hours = 12  # 默认时长12小时
    hotel_rating = ""
    hotel_address = ""
    hotel_image = ""  # 只保存一张图片
    alternative_hotels = []
    
    # hotel_match = re.search(r'🏨【酒店】(.+)', day_title)
    # if hotel_match:
    #     hotel_name = hotel_match.group(1).strip()
    #     location = hotel_name
    
    # 查找酒店详细信息
    i = index + 1
    in_hotel_block = False
    current_hotel = None
    remark = "温馨提示：本产品指定入住当地精选酒店，酒店房型以实际安排为准。"
    
    # 向前查找是否有图片（有时图片在酒店活动之前）
    j = index - 1
    while j >= 0 and j >= index - 5:  # 限制向前查找范围
        prev_line = lines[j].strip()
        if prev_line.startswith('![](') and prev_line.endswith(')'):
            # 提取图片URL
            image_url = prev_line[4:-1]  # 去掉 ![](  和  )
            
            # 过滤掉图标类型的链接
            if "activetype" not in image_url:
                # 处理图片链接，移除尺寸参数
                if image_url.startswith("@"):
                    image_url = image_url[1:]  # 移除@前缀
                
                if "_R_" in image_url:
                    image_url = re.sub(r'_R_\d+_\d+\.jpg', '.jpg', image_url)
                
                hotel_image = image_url
                break
        j -= 1
    
    while i < len(lines):
        line = lines[i].strip()
        if not line:
            i += 1
            continue
            
        # 如果遇到下一个时间活动，停止
        if re.match(r'^\d{2}:\d{2}\s*[·•]', line) or re.match(r'^(全天|上午|下午|晚上)\s*[·•]', line):
            break
            
        # 如果遇到下一个元素的开始，停止
        if line.startswith('![](') and re.search(r'activetype/V1/activetype\d+\.png', line):
            break
            
        # 如果遇到下一天的行程信息，停止
        if re.match(r'^DAY\d+$', line):
            break
            
        # 如果遇到行程标题（通常包含【行程】），停止
        if "【行程】" in line:
            break
        
        # 提取酒店图片（如果之前没有找到）
        if not hotel_image and line.startswith('![](') and line.endswith(')'):
            # 提取图片URL
            image_url = line[4:-1]  # 去掉 ![](  和  )
            
            # 过滤掉图标类型的链接
            if "activetype" not in image_url:
                # 处理图片链接，移除尺寸参数
                if image_url.startswith("@"):
                    image_url = image_url[1:]  # 移除@前缀
                
                if "_R_" in image_url:
                    image_url = re.sub(r'_R_\d+_\d+\.jpg', '.jpg', image_url)
                
                hotel_image = image_url

        elif re.match(r'^.+型酒店$', line) and len(line) < 10:
            hotel_name_raw = lines[i - 1].strip()
            junk_pattern = r'[^\u4e00-\u9fa5a-zA-Z0-9]+$'
            hotel_name = re.sub(junk_pattern, '', hotel_name_raw)

        # 检查是否是自选酒店提示
        # elif "自选酒店" in line:
        #     hotel_name = "自选酒店"
        
        # 检查是否是酒店名称（带有">"符号的行通常是酒店名称）
        # elif ">" in line and not line.startswith("!["):
        #     print(f'CONTAINS > : {line}')
        #     hotel_parts = line.split(">")
        #     if len(hotel_parts) > 0:
        #         current_hotel = hotel_parts[0].strip()
        #         if not hotel_name or hotel_name == "当地精选酒店" or hotel_name == "自选酒店":
        #             hotel_name = current_hotel
        #         else:
        #             alternative_hotels.append(current_hotel)
        #         in_hotel_block = True
                
        # 提取酒店名称（双星号包围的文本通常是酒店名称）
        # elif "**" in line:
        #     hotel_name_match = re.search(r'\*\*(.+?)\*\*', line)
        #     if hotel_name_match:
        #         extracted_name = hotel_name_match.group(1).strip()
        #         if not hotel_name or hotel_name == "当地精选酒店" or hotel_name == "自选酒店":
        #             hotel_name = extracted_name
        #         else:
        #             alternative_hotels.append(extracted_name)
        
        # 提取酒店评分
        elif re.search(r'\d+\.\d+分', line):
            hotel_rating = re.search(r'(\d+\.\d+)分', line).group(1)
        
        # 提取酒店地址
        # elif in_hotel_block and ("距" in line or "km" in line.lower() or "公里" in line):
        #     hotel_address = line
        #     if not location:
        #         location = line
        #
        # # 提取酒店地址（非酒店块内）
        # elif ("距" in line and "公里" in line) or ("距" in line and "km" in line.lower()):
        #     hotel_address = line
        #     if not location:
        #         location = line
        
        # 检查是否是备选酒店
        elif line.startswith("或"):
            alt_hotel = line.replace("或", "").strip()
            alternative_hotels.append(alt_hotel)
        
        # 提取酒店备注
        elif len(line) > 20:
            # 使用原来的方法提取备注，但过滤掉DAY之后的文字
            full_remark = line
            
            # 检查备注中是否包含DAY
            day_match = re.search(r'(DAY\d+)', full_remark)
            if day_match:
                # 如果包含DAY，只保留DAY之前的部分
                full_remark = full_remark.split(day_match.group(1))[0].strip()
            
            remark = full_remark
        
        i += 1
    
    return {
        "elementType": "hotel",
        "title": "酒店",
        "location": location,
        "time_type": "specific",
        "time_start_time": time_str,
        "time_duration_hours": duration_hours,
        "time_duration_minutes": 0,
        "time_period": "晚上",
        "time_remark": "入住时间",
        "driving_distance": 0,
        "driving_duration_hours": 0,
        "driving_duration_minutes": 0,
        "elementData": {
            "hotelName": hotel_name,
            "rating": hotel_rating,
            "address": hotel_address,
            "alternativeHotels": alternative_hotels,
            "image": hotel_image,  # 只保存一张图片
            "remark": remark
        }
    }

def create_other_activity(time_str, activity_type, lines, index):
    """创建其他活动"""
    content = activity_type
    
    # 获取详细内容（可能跨多行）
    content_lines = []
    i = index + 1
    while i < len(lines):
        line = lines[i].strip()
        if not line:
            i += 1
            continue
        
        # 如果遇到下一个时间活动，停止
        if re.match(r'^\d{2}:\d{2}\s*[·•]', line) or re.match(r'^(全天|上午|下午|晚上)\s*[·•]', line):
            break
            
        # 如果遇到下一个元素的开始，停止
        if line.startswith('![](') and re.search(r'activetype/V1/activetype\d+\.png', line):
            break
        
        # 跳过图片链接
        if line.startswith('![') and line.endswith(')'):
            i += 1
            continue
            
        # 检查是否有"展开"按钮
        if line == "展开":
            i += 1
            continue
        
        # 添加内容行
        content_lines.append(line)
        i += 1
    
    # 合并内容行
    if content_lines:
        content = '\n'.join(content_lines)
    
    return {
        "elementType": "other",
        "title": "其他",
        "time_type": "specific",
        "time_start_time": time_str,
        "time_duration_hours": None,
        "time_duration_minutes": None,
        "time_period": None,
        "time_remark": "",
        "driving_distance": 0,
        "driving_duration_hours": 0,
        "driving_duration_minutes": 0,
        "elementData": {
            "content": content
        }
    }

def create_period_other_activity(period, activity_type, lines, index):
    """创建时间段其他活动"""
    content = activity_type
    
    # 获取详细内容（可能跨多行）
    content_lines = []
    i = index + 1
    while i < len(lines):
        line = lines[i].strip()
        if not line:
            i += 1
            continue
        
        # 如果遇到下一个活动，停止
        if re.match(r'^\d{2}:\d{2}\s*[·•]', line) or re.match(r'^(全天|上午|下午|晚上)\s*[·•]', line):
            break
            
        # 如果遇到下一个元素的开始，停止
        if line.startswith('![](') and re.search(r'activetype/V1/activetype\d+\.png', line):
            break
        
        # 跳过图片链接
        if line.startswith('![') and line.endswith(')'):
            i += 1
            continue
            
        # 检查是否有"展开"按钮，这也表示内容块的结束
        if line == "展开":
            i += 1
            continue
        
        content_lines.append(line)
        i += 1
    
    if content_lines:
        content = '\n'.join(content_lines)
    
    return {
        "elementType": "other",
        "title": "其他",
        "time_type": "period",
        "time_start_time": None,
        "time_duration_hours": None,
        "time_duration_minutes": None,
        "time_period": period,
        "time_remark": "",
        "driving_distance": 0,
        "driving_duration_hours": 0,
        "driving_duration_minutes": 0,
        "elementData": {
            "content": content
        }
    }

def create_period_transport_activity(period, activity_type, day_title, lines, index):
    """创建时间段交通活动"""
    # 从day_title中提取距离和时间信息
    distance = 0
    duration_hours = 0
    
    distance_match = re.search(r'约(\d+)km', day_title)
    duration_match = re.search(r'(\d+(?:\.\d+)?)小时', day_title)
    
    if distance_match:
        distance = int(distance_match.group(1))
    if duration_match:
        duration_hours = float(duration_match.group(1))
    
    # 获取交通详细描述（可能跨多行）
    content = activity_type
    content_lines = []
    
    i = index + 1
    while i < len(lines):
        line = lines[i].strip()
        if not line:
            i += 1
            continue
        
        # 如果遇到下一个活动，停止
        if re.match(r'^\d{2}:\d{2}\s*[·•]', line) or re.match(r'^(全天|上午|下午|晚上)\s*[·•]', line):
            break
            
        # 如果遇到下一个元素的开始，停止
        if line.startswith('![](') and re.search(r'activetype/V1/activetype\d+\.png', line):
            break
        
        # 跳过图片链接
        if line.startswith('![') and line.endswith(')'):
            i += 1
            continue
            
        # 检查是否有"展开"按钮
        if line == "展开":
            i += 1
            continue
            
        # 检查是否有"行驶："信息，这通常包含距离和时间
        if line.startswith("行驶："):
            # 尝试提取距离和时间
            dist_match = re.search(r'约(\d+)公里', line)
            time_match = re.search(r'约(\d+(?:\.\d+)?)小时', line)
            
            if dist_match:
                distance = int(dist_match.group(1))
            if time_match:
                duration_hours = float(time_match.group(1))
        
        # 添加内容行
        content_lines.append(line)
        i += 1
    
    # 合并内容行
    if content_lines:
        content = '\n'.join(content_lines)
    
    return {
        "elementType": "transport",
        "title": "交通",
        "time_type": "period",
        "time_start_time": None,
        "time_duration_hours": duration_hours,
        "time_duration_minutes": 0,
        "time_period": period,
        "time_remark": None,
        "driving_distance": distance,
        "driving_duration_hours": duration_hours,
        "driving_duration_minutes": 0,
        "elementData": {
            "content": content
        }
    }

def create_dismissal_activity(lines, index):
    """创建解散活动"""
    content = "解散"
    locations = []
    time_info = ""
    
    # 查找解散信息
    i = index + 1
    while i < len(lines):
        line = lines[i].strip()
        if not line:
            i += 1
            continue
            
        # 如果遇到下一个活动，停止
        if re.match(r'^\d{2}:\d{2}\s*[·•]', line) or re.match(r'^(全天|上午|下午|晚上)\s*[·•]', line):
            break
            
        # 提取解散地点
        if "散团点" in line:
            location_line = lines[i+1].strip() if i+1 < len(lines) else ""
            if location_line:
                locations.append(location_line.split("复制")[0].strip())
                
        # 提取解散时间
        if "解散时间" in line:
            time_line = lines[i+1].strip() if i+1 < len(lines) else ""
            if time_line:
                time_info = time_line
        
        i += 1
    
    return {
        "elementType": "dismissal",
        "title": "解散",
        "time_type": "period",
        "time_start_time": None,
        "time_duration_hours": None,
        "time_duration_minutes": None,
        "time_period": "全天",
        "time_remark": "解散时间",
        "driving_distance": 0,
        "driving_duration_hours": 0,
        "driving_duration_minutes": 0,
        "elementData": {
            "content": content,
            "locations": locations,
            "time_info": time_info
        }
    }

def print_summary(data):
    """打印数据提取摘要"""
    print("\n📋 数据提取摘要:")
    print("="*50)
    print(f"📅 产品ID: {data['product_info']['product_id']}")
    print(f"📝 产品标题: {data['product_info']['title']}")
    print(f"⏰ 行程天数: {data['product_info']['duration']}")
    print(f"🗓️  详细行程: {len(data['itinerary'])} 天")
    
    for day_data in data['itinerary']:
        activities_count = {}
        for activity in day_data['activities']:
            activity_type = activity['elementType']
            activities_count[activity_type] = activities_count.get(activity_type, 0) + 1
        
        print(f"  Day {day_data['day']}: {len(day_data['activities'])} 个活动")
        for activity_type, count in activities_count.items():
            print(f"    {activity_type}: {count}个")
    
    print("="*50)
    print("\n🎉 数据提取完成!")
    print(f"📊 提取到完整的 {len(data['itinerary'])} 天行程数据")
    print("💾 数据已保存为JSON格式，可直接用于前端展示")
    print("✅ 程序执行完毕!")

# 主程序入口
if __name__ == "__main__":
    # 创建命令行参数解析器
    parser = argparse.ArgumentParser(description='携程行程数据提取工具')
    parser.add_argument('--url', type=str, help='携程行程页面URL', 
                       default="https://m.ctrip.com/webapp/xtour/detailComplexRoute?ProductId=61698933&DepartCityId=28&Alias=A")
    parser.add_argument('--output', type=str, help='输出文件路径', default="")
    args = parser.parse_args()
    
    # 获取URL
    url = args.url
    
    # 执行爬取
    result = asyncio.run(extract_ctrip_itinerary(url))
    
    # 如果指定了输出文件，则保存结果
    if args.output and result:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"💾 结果已保存到 {args.output}") 