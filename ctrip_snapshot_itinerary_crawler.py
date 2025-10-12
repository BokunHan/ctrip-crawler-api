import asyncio
import re
import json
from datetime import datetime
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode

def extract_snapshot_itinerary(markdown_content, url):
    """
    从产品快照页面的markdown内容中，提取结构化的多日行程数据
    """
    print("🎯 开始从markdown中提取快照行程...")

    data = {
        "product_info": {
            "ctrip_id": "",
            "title": "",  # 将从内容中提取
            "sub_title": "",
            "duration": "",
            "total_days": 0,
            "remarks": ""
        },
        "itinerary": [],
        "metadata": {
            "extracted_at": datetime.now().isoformat(),
            "source_url": url
        }
    }

    lines = markdown_content.split('\n')
    current_day_data = None

    # 尝试提取ctrip_id
    for line in lines:
        if "编号" in line:
            data["product_info"]["ctrip_id"] = line.split("：")[1].strip()
            break

    # 尝试提取title和sub_title
    for i, line in enumerate(lines):
        title_match = re.match(r'^#\s+(.+)$', line)
        if title_match:
            data["product_info"]["title"] = title_match.group(1).strip()
            data["product_info"]["sub_title"] = lines[i+1].strip()
            break

    for i, line in enumerate(lines):
        line = line.strip()
        if not line:
            continue

        # --- 识别天的开始 ---
        if line.lower() == "day" and i + 1 < len(lines) and lines[i + 1].strip().isdigit():
            if current_day_data:
                data["itinerary"].append(current_day_data)

            day_num = int(lines[i + 1].strip())
            current_day_data = {
                "day": day_num,
                "day_title": "",
                "activities": []
            }
            data["product_info"]["total_days"] += 1

            if i + 2 < len(lines):
                current_day_data["day_title"] = lines[i + 2].strip()

            # 为第一天添加集合活动
            if day_num == 1:
                assembly_activity = create_assembly_activity(lines)
                current_day_data["activities"].append(assembly_activity)

            continue

        # 解析具体的活动项目（严格按时间顺序）
        if current_day_data:
            activity = parse_activity_line(line, lines, i, current_day_data["day_title"])
            if activity:
                current_day_data["activities"].append(activity)

    # 添加最后一天的数据
    if current_day_data:
        data["itinerary"].append(current_day_data)

    data["product_info"]["duration"] = f"{data["product_info"]['total_days']}天"

    print(f"✅ 快照行程提取完成！共找到 {data["product_info"]['total_days']} 天的行程。")
    return data


def parse_activity_line(line, lines, index, day_title):
    """
    解析单个活动行，严格按照时间格式识别
    """
    # 跳过图片链接和空行
    if line.startswith('![') or not line:
        return None

    # 解析时间格式的活动: "08:00"
    time_activity_match = re.match(r'^(\d{2}:\d{2})\s*$', line)
    if time_activity_match:
        time_str = time_activity_match.group(1)
        activity_type_match = re.match(r'^#####\s*(.+)$', lines[index + 1])
        if activity_type_match:
            activity_type = activity_type_match.group(1).strip()

        # extra_info = time_activity_match.group(3) if time_activity_match.group(3) else ""

        # 根据活动类型创建对应的活动
        if '早餐' in activity_type or '午餐' in activity_type or '晚餐' in activity_type:
            return create_restaurant_activity(time_str, activity_type, "", lines, index)
        elif '交通' in activity_type:
            return create_transport_activity(time_str, activity_type, day_title, lines, index)
        elif '景点' in activity_type or '场馆' in activity_type:
            return create_scenic_activity(time_str, activity_type, lines, index)
        elif '酒店' in activity_type:
            return create_hotel_activity(time_str, activity_type, day_title, lines, index)
        else:
            # 其他类型的活动（如其他、购物等）
            return create_other_activity(time_str, activity_type, lines, index)

    # 解析时间段格式的活动: "全天"
    period_activity_match = re.match(r'^(全天|上午|下午|晚上)\s*$', line)
    if period_activity_match:
        period = period_activity_match.group(1)
        activity_type_match = re.match(r'^#####\s*(.+)$', lines[index + 1])
        if activity_type_match:
            activity_type = activity_type_match.group(1).strip()

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
    # hotel_match = re.match(r'^(\d{2}:\d{2})\s*[·•]?\s*酒店', line)
    # if hotel_match:
    #     time_str = hotel_match.group(1)
    #     return create_hotel_activity(time_str, "酒店", day_title, lines, index)

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
        if "集合" in line:
            # 查找后续的集合信息
            j = i + 1
            while j < len(lines) and not re.match(r'^#####\s*(.+)$', lines[j].strip()):
                current_line = lines[j].strip()

                if j == i + 1:
                    title = current_line.strip().replace(":", "").replace("：", "")
                    next_line = lines[j + 1].strip()
                    if "接机" in next_line or "接站" in next_line or "接机/站" in next_line:
                        assembly_type = "接机/站"
                    else:
                        assembly_type = "上门接"

                # 提取地点列表 - 处理接机/站的情况
                if "免费接区域" in current_line:
                    # 从"免费接区域: "后面提取地点信息
                    location_info = current_line.split(":", 1)[1].strip() if ":" in current_line else ""
                    # 提取地区名称
                    locations = [loc.strip() for loc in re.findall(r'[^\d\s、，,]+区', location_info)]

                info_match = re.match(r'^免费接的机场/火车站[:：](.+)服务时间段[:：](.+)$', current_line)
                if info_match:
                    # 从":"后面提取机场/站点信息
                    location_info = info_match.group(1).strip()
                    # 分割可能的多个地点
                    locations = [loc.strip() for loc in re.split(r'[、，,]', location_info) if loc.strip()]
                    time_info = info_match.group(2).strip()

                # 提取时间信息
                # if "服务时间" in current_line:
                #     time_info = current_line.split(":", 1)[1].strip() if ":" in current_line else "全天（专车）"

                # 提取备注信息
                if "超过免费接" in current_line or current_line.startswith("超过"):
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
    # included = "含餐" in extra_info or "含" in extra_info
    # if "自理" in extra_info:
    #     included = False
    adult_included = False
    child_included = False

    # 获取下一行的详细信息
    remark = ""
    remark_lines = []
    duration_hours = 1  # 默认时长1小时

    # 查找后续行中的用餐时间信息
    i = index + 1
    while i < len(lines):
        i += 1
        line = lines[i].strip()
        if not line:
            continue

        # 如果遇到下一个时间活动，停止
        if re.match(r'^\d{2}:\d{2}\s*', line) or re.match(r'^(全天|上午|下午|晚上)\s*', line) or re.match(r'^#####\s*(.+)', line):
            break

        # 提取用餐时间
        duration_match = re.search(r'用餐时间[:：]\s*约(\d+)\s*(.+)', line)
        if duration_match:
            time_value, unit = duration_match.groups()
            time = int(time_value)
            match unit.strip():
                case u if "小时" in u:
                    duration_hours = time
                case u if "分钟" in u:
                    duration_hours = time / 60

        if re.search(r'成人[:：]含餐', line):
            adult_included = True

        if re.search(r'儿童[:：]含餐', line):
            child_included = True

        # 提取备注信息
        if not line.startswith('![') and not re.match(r'^\d{2}:\d{2}\s*', line) and not re.match(r'^(全天|上午|下午|晚上)\s*', line) and not re.match(r'(.*)(含餐|自理|用餐时间)(.*)', line):
            remark_lines.append(line)

    if remark_lines:
        remark = '\n'.join(remark_lines)

    return {
        "elementType": "restaurant",
        "title": "餐厅",
        "time_type": "specific",
        "time_start_time": time_str,
        "time_duration_hours": duration_hours,
        "time_duration_minutes": 0,
        "time_period": None,
        "time_remark": None,
        "driving_distance": 0,
        "driving_duration_hours": 0,
        "driving_duration_minutes": 0,
        "elementData": {
            "name": meal_type,
            "meal_type": meal_type,
            "adult_included": adult_included,
            "adult_fee_type": "费用包含" if adult_included else "自理",
            "child_included": child_included,
            "child_fee_type": "费用包含" if child_included else "自理",
            "remark": remark
        }
    }


def create_transport_activity(time_str, activity_type, day_title, lines, index):
    """创建交通活动"""
    # 从day_title中提取距离和时间信息
    distance = 0
    duration_hours = 0
    duration_minutes = 0

    distance_match = re.search(r'约(\d+)(km|千米|公里)', day_title)
    if distance_match:
        distance = int(distance_match.group(1))

    duration_match = re.findall(r'(\d+)\s*(小时|分钟)', day_title)
    for value, unit in duration_match:
        if unit == "小时":
            duration_hours = int(value)
        elif unit == "分钟":
            duration_minutes = int(value)

    # 获取交通详细描述（可能跨多行）
    content = activity_type
    content_lines = []

    i = index + 1
    while i < len(lines):
        i += 1
        line = lines[i].strip()
        if not line:
            continue

        # 如果遇到下一个时间活动，停止
        if re.match(r'^\d{2}:\d{2}\s*', line) or re.match(r'^(全天|上午|下午|晚上)\s*', line) or re.match(r'^#####\s*(.+)', line):
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
            dist_match = re.search(r'约(\d+)(km|千米|公里)', line)
            if dist_match:
                distance = int(dist_match.group(1))

            time_match = re.findall(r'(\d+)\s*(小时|分钟)', line)
            for value, unit in time_match:
                if unit == "小时":
                    duration_hours = int(value)
                elif unit == "分钟":
                    duration_minutes = int(value)

        # 添加内容行
        content_lines.append(line)


    # 合并内容行
    if content_lines:
        content = '\n'.join(content_lines)

    return {
        "elementType": "transport",
        "title": "交通",
        "time_type": "specific",
        "time_start_time": time_str,
        "time_duration_hours": duration_hours,
        "time_duration_minutes": duration_minutes,
        "time_period": None,
        "time_remark": None,
        "driving_distance": distance,
        "driving_duration_hours": duration_hours,
        "driving_duration_minutes": duration_minutes,
        "elementData": {
            "content": content
        }
    }


def create_scenic_activity(time_str, activity_type, lines, index):
    """创建景点活动"""
    scenic_spots = []
    content = activity_type
    duration_hours = 2  # 默认时长2小时
    remark = ""
    remark_lines = []
    current_spot = None

    # 查找后续的景点信息
    i = index + 1
    while i < len(lines):
        i += 1
        line = lines[i].strip()
        if not line:
            continue

        print(line)

        # 如果遇到下一个时间活动，停止
        if re.match(r'^\d{2}:\d{2}\s*', line) or re.match(r'^(全天|上午|下午|晚上)\s*', line) or re.match(r'^#####\s*(.+)', line):
            break

        # 提取活动时间
        duration_match = re.search(r'活动时间[:：]\s*约(\d+)小时', line)
        if duration_match:
            duration_hours = float(duration_match.group(1))

        duration_match2 = re.search(r'活动时间[:：]\s*约(\d+)分钟', line)
        if duration_match2:
            minutes = int(duration_match2.group(1))
            duration_hours = minutes / 60

        # image_url = ""
        # # 检查是否是图片链接
        # if line.startswith('![') and line.endswith(')'):
        #     # 提取图片URL
        #     image_url = line

        # 景点名称通常是"前往：景点名(门票信息)"格式
        spot_info_match = re.match(r'^前往[:：]\s*(.+?)\s*\((.+?)\)', line)
        if spot_info_match:
            spot_name = spot_info_match.group(1).strip()
            ticket_info = spot_info_match.group(2).strip()
            ticket_included = ('含' in ticket_info or '已含' in ticket_info)

            # 创建景点对象
            print(f"提取到景点: {spot_name}")
            current_spot = {
                "name": spot_name,
                "ticket_included": ticket_included,
                "ticket_type": ticket_info,
                "description": "",
                "images": []  # 使用处理后的图片URL
            }
            scenic_spots.append(current_spot)
            continue  # 处理完景点行，继续下一行

        urls = re.findall(r'!\[.*?\]\((.+?)\)', line)
        if current_spot:
            for url in urls:
                # 将提取到的图片URL添加到当前景点的images列表中
                if url not in current_spot['images']:
                    current_spot['images'].append(url)
            continue  # 处理完图片行，继续下一行

        if not re.search(r'活动时间[:：]\s*约(\d+)', line) and not re.search(r'^前往[:：]', line) and not line.startswith('!['):
            remark_lines.append(line)

    if remark_lines:
        remark = '\n'.join(remark_lines)

    return {
        "elementType": "scenic",
        "title": "景点",
        "time_type": "specific",
        "time_start_time": time_str,
        "time_duration_hours": duration_hours,
        "time_duration_minutes": 0,
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

    hotel_match = re.search(r'🏨【酒店】(.+)', day_title)
    if hotel_match:
        hotel_name = hotel_match.group(1).strip()
        location = hotel_name

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
        i += 1
        line = lines[i].strip()
        if not line:
            continue

        # 如果遇到下一个时间活动，停止
        if re.match(r'^\d{2}:\d{2}\s*', line) or re.match(r'^(全天|上午|下午|晚上)\s*', line) or re.match(r'^#####\s*(.+)', line):
            break

        # 如果遇到下一个元素的开始，停止
        if line.startswith('![](') and re.search(r'activetype/V1/activetype\d+\.png', line):
            break

        # 如果遇到下一天的行程信息，停止
        if re.match(r'^Day\s*$', line):
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

        # 检查是否是自选酒店提示
        elif "自选酒店" in line:
            hotel_name = "自选酒店"

        # 检查是否是酒店名称（带有">"符号的行通常是酒店名称）
        elif ">" in line and not line.startswith("!["):
            hotel_parts = line.split(">")
            if len(hotel_parts) > 0:
                current_hotel = hotel_parts[0].strip()
                if not hotel_name or hotel_name == "当地精选酒店" or hotel_name == "自选酒店":
                    hotel_name = current_hotel
                else:
                    alternative_hotels.append(current_hotel)
                in_hotel_block = True

        # 提取酒店名称（双星号包围的文本通常是酒店名称）
        elif "**" in line:
            hotel_name_match = re.search(r'\*\*(.+?)\*\*', line)
            if hotel_name_match:
                extracted_name = hotel_name_match.group(1).strip()
                if not hotel_name or hotel_name == "当地精选酒店" or hotel_name == "自选酒店":
                    hotel_name = extracted_name
                else:
                    alternative_hotels.append(extracted_name)

        # 提取酒店评分
        elif in_hotel_block and re.search(r'\d+\.\d+分', line):
            hotel_rating = re.search(r'(\d+\.\d+)分', line).group(1)

        # 提取酒店地址
        elif in_hotel_block and ("距" in line or "km" in line.lower() or "公里" in line):
            hotel_address = line
            if not location:
                location = line

        # 提取酒店地址（非酒店块内）
        elif ("距" in line and "公里" in line) or ("距" in line and "km" in line.lower()):
            hotel_address = line
            if not location:
                location = line

        # 检查是否是备选酒店
        elif line.startswith("或") and "酒店" in line:
            alt_hotel = line.replace("或", "").strip()
            alternative_hotels.append(alt_hotel)

        # 提取酒店备注
        elif "温馨提示" in line or "注意" in line:
            # 使用原来的方法提取备注，但过滤掉DAY之后的文字
            full_remark = line

            # 检查备注中是否包含DAY
            day_match = re.search(r'(Day\s*)', full_remark)
            if day_match:
                # 如果包含DAY，只保留DAY之前的部分
                full_remark = full_remark.split(day_match.group(1))[0].strip()

            remark = full_remark


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
        i += 1
        line = lines[i].strip()
        if not line:
            continue

        # 如果遇到下一个时间活动，停止
        if re.match(r'^\d{2}:\d{2}\s*', line) or re.match(r'^(全天|上午|下午|晚上)\s*', line) or re.match(r'^#####\s*(.+)', line):
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
        i += 1
        line = lines[i].strip()
        if not line:
            continue

        # 如果遇到下一个活动，停止
        if re.match(r'^\d{2}:\d{2}\s*', line) or re.match(r'^(全天|上午|下午|晚上)\s*', line) or re.match(r'^#####\s*(.+)', line):
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

    distance_match = re.search(r'约(\d+)(km|千米|公里)', day_title)
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
        i += 1
        line = lines[i].strip()
        if not line:
            continue

        # 如果遇到下一个活动，停止
        if re.match(r'^\d{2}:\d{2}\s*', line) or re.match(r'^(全天|上午|下午|晚上)\s*', line) or re.match(r'^#####\s*(.+)', line):
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
            dist_match = re.search(r'约(\d+)(km|千米|公里)', line)
            time_match = re.search(r'约(\d+(?:\.\d+)?)小时', line)

            if dist_match:
                distance = int(dist_match.group(1))
            if time_match:
                duration_hours = float(time_match.group(1))

        # 添加内容行
        content_lines.append(line)

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
    content_lines = []
    locations = []
    time_info = ""

    # 查找解散信息
    i = index + 1
    while i < len(lines):
        i += 1
        line = lines[i].strip()
        if not line:
            continue

        # 如果遇到下一个活动，停止
        if re.match(r'^\d{2}:\d{2}\s*', line) or re.match(r'^(全天|上午|下午|晚上)\s*', line) or re.match(r'^##\s*(.+)', line):
            break

        # 提取解散地点
        if "散团点" in line:
            location_line = lines[i + 1].strip() if i + 1 < len(lines) else ""
            if location_line:
                locations.append(location_line.split("复制")[0].strip())

        # 提取解散时间
        elif "解散时间" in line:
            time_line = lines[i + 1].strip() if i + 1 < len(lines) else ""
            if time_line:
                time_info = time_line

        else:
            content_lines.append(line)

    if content_lines:
        content = '\n'.join(content_lines)

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


async def crawl_and_extract_snapshot(url):
    """
    直接爬取快照页面并提取结构化行程
    """
    print(f"🚀 开始爬取产品快照页面: {url}")

    browser_config = BrowserConfig(
        headless=True,
        extra_args=['--disable-web-security', '--no-sandbox'],
    )

    crawl_config = CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS,
        page_timeout=50000,
        delay_before_return_html=20.0,
        log_console=True,
        verbose=True,
        scan_full_page=False,
        js_code=  # 快照页可能很长，模拟滚动以确保加载完整
            """
            // This is a two-phase script to solve the timing issue.
            
            // --- PHASE 1: DISCOVER THE TRUE HEIGHT ---
            console.log('--- Starting Phase 1: Waiting for container height to stabilize... ---');
            let lastHeight = 0;
            let stableChecks = 0;
            const discoveryTimer = setInterval(() => {
                const container = document.getElementById('hp_container');
                if (!container) {
                    console.log('Waiting for #hp_container to appear...');
                    return;
                }

                const styles = window.getComputedStyle(container);
                const currentHeight = parseInt(styles.height, 10);

                // Check if the height has changed
                if (currentHeight > lastHeight) {
                    // console.log(`Height is growing... New height: ${currentHeight}px`);
                    lastHeight = currentHeight;
                    stableChecks = 0; // Reset the stability counter
                } 
                // If height is the same and is a reasonable value, consider it stable
                else if (currentHeight === lastHeight && currentHeight > window.innerHeight) {
                    stableChecks++;
                    console.log(`Height is stable at ${currentHeight}px (check #${stableChecks})`);
                }
                
                // If the height has been stable for 5 checks, we are confident it's the final value.
                if (stableChecks >= 5) {
                    clearInterval(discoveryTimer);
                    // --- START PHASE 2 ---
                    startScrolling(currentHeight);
                }
            }, 500); // Check the height every 500ms

            // --- PHASE 2: SCROLL USING THE DISCOVERED HEIGHT ---
            function startScrolling(scrollHeight) {
                console.log(`--- Phase 1 complete. Final height is ${scrollHeight}px. Starting Phase 2: Scrolling... ---`);
                
                let totalHeight = 0;
                let distance = 1000;
                let scrollCount = 0;

                const scrollTimer = setInterval(() => {
                    window.scrollBy(0, distance);
                    totalHeight += distance;
                    scrollCount++;
                    
                    // console.log(`--- scroll #${scrollCount}, scrolled: ${totalHeight} / ${scrollHeight}`);

                    if (totalHeight >= scrollHeight) {
                        clearInterval(scrollTimer);
                        console.log('--- Phase 2: Scrolling finished. ---');
                    }
                }, 100);
            }
        """
    )

    async with AsyncWebCrawler(config=browser_config) as crawler:
        try:
            print("📱 正在加载页面并执行滚动...")
            result = await crawler.arun(url=url, config=crawl_config)

            if result.success and result.markdown:
                print("✅ 页面爬取成功！")
                structured_data = extract_snapshot_itinerary(result.markdown, url)
                return {"success": True, "data": structured_data}
            else:
                print(f"❌ 页面爬取失败: {result.error_message}")
                return {"success": False, "error": f"爬取失败: {result.error_message}"}

        except Exception as e:
            print(f"💥 爬取过程中发生异常: {str(e)}")
            return {"success": False, "error": f"发生异常: {str(e)}"}