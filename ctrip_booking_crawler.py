import asyncio
import json
import re
from datetime import datetime
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode

def extract_booking_note_data_from_markdown(markdown_content, url=""):
    """
    从markdown内容中提取结构化的预订须知数据
    """
    print("🎯 开始从markdown中提取预订须知结构化数据...")
    
    # 初始化数据结构
    booking_data = {
        "product_id": "",
        "travel_agency_info": {
            "agent": "",  # 代理社
            "delegate": "",  # 委托社
            "claim": ""   # 委托声明
        },
        "booking_restrictions": {
            "age_limit": "",
            "group_limit": "",
            "other_limit": ""
        },
        "accommodation_policy": {
            "multi_person": ""
        },
        "group_info": {
            "group_description": "",
            "departure_notice": ""
        },
        "booking_requirements": [],  # 预订及出行须知列表
        "violation_terms": {
            "agency_violation": [],  # 旅行社违约条款
            "tourist_violation": []   # 旅游者违约条款
        },
        "travel_guide": [],  # 出行指南
        "safety_tips": [],   # 安全提示
        "protection_tips": [],  # 保障提示
        "payment_info": {
            "supported_methods": [],  # 支持的支付方式
            "payment_notes": []       # 支付说明
        }
    }
    
    lines = markdown_content.split('\n')

    for line in lines:
        print(line)
    
    # 1. 从URL中提取商品ID
    if url and 'productId=' in url:
        match = re.search(r'productId=(\d+)', url)
        if match:
            booking_data["product_id"] = match.group(1)
    
    # 如果URL中没有找到，再从markdown内容中查找
    if not booking_data["product_id"]:
        for line in lines:
            # 方式1：从URL参数中提取
            if 'productId=' in line:
                match = re.search(r'productId=(\d+)', line)
                if match:
                    booking_data["product_id"] = match.group(1)
                    break
            # 方式2：从小写的productid中提取
            elif 'productid=' in line:
                match = re.search(r'productid=(\d+)', line)
                if match:
                    booking_data["product_id"] = match.group(1)
                    break
        
        # 如果还没找到，从URL中直接提取
        if not booking_data["product_id"]:
            url_pattern = r'productId=(\d+)'
            for line in lines:
                match = re.search(url_pattern, line, re.IGNORECASE)
                if match:
                    booking_data["product_id"] = match.group(1)
                    break
    
    # 2. 提取旅行社信息
    for line in lines:
        if '代理招徕' in line and '委托社' in line:
            booking_data["travel_agency_info"]["claim"] = line.strip()

            # 提取代理社
            agent_match = re.search(r'由(.+?)代理招徕', line)
            if agent_match:
                booking_data["travel_agency_info"]["agent"] = agent_match.group(1)
            
            # 提取委托社
            delegate_match = re.search(r'委托社为(.+?)，', line)
            if delegate_match:
                booking_data["travel_agency_info"]["delegate"] = delegate_match.group(1)
            break
    
    # 3. 提取预订限制信息
    in_restrictions = False
    for i, line in enumerate(lines):
        if '预订限制' in line:
            in_restrictions = True
            continue
        
        if in_restrictions:
            if '年龄限制' in line:
                # 查找年龄限制的详细内容
                for j in range(i, min(i+5, len(lines))):
                    if lines[j].strip() and not lines[j].startswith('---') and not lines[j].startswith('人群限制'):
                        booking_data["booking_restrictions"]["age_limit"] = lines[j].split('|')[1].strip()
                        break
            elif '人群限制' in line:
                # 查找人群限制的详细内容
                for j in range(i, min(i+5, len(lines))):
                    if lines[j].strip() and not lines[j].startswith('---') and not lines[j].startswith('其他限制'):
                        booking_data["booking_restrictions"]["group_limit"] = lines[j].split('|')[1].strip()
                        break
            elif '其他限制' in line:
                # 查找其他限制的详细内容
                for j in range(i, min(i+5, len(lines))):
                    if lines[j].strip() and not lines[j].startswith('---') and '入住政策' not in lines[j]:
                        booking_data["booking_restrictions"]["other_limit"] = lines[j].split('|')[1].strip()
                        break
            elif '入住政策' in line:
                in_restrictions = False
                break
    
    # 4. 提取住宿政策
    for i, line in enumerate(lines):
        if '入住政策' in line:
            # 查找多人入住政策的详细内容
            for j in range(i+1, min(i+5, len(lines))):
                if lines[j].strip() and not lines[j].startswith('---') and '成团说明' not in lines[j]:
                    booking_data["accommodation_policy"]["multi_person"] = lines[j].split('|')[1].strip()
                    break
            break
    
    # 5. 提取成团说明 - 优化版本
    for i, line in enumerate(lines):
        if '成团说明' in line:
            if '|' in line:
                # 表格格式：成团说明| 内容
                parts = line.split('|')
                if len(parts) > 1:
                    booking_data["group_info"]["group_description"] = parts[1].strip()
            else:
                # 查找后续行的详细内容
                for j in range(i+1, min(i+5, len(lines))):
                    if lines[j].strip() and not lines[j].startswith('---') and '出团通知' not in lines[j]:
                        booking_data["group_info"]["group_description"] = lines[j].strip()
                        break
        elif '出团通知' in line:
            if '|' in line:
                # 表格格式：出团通知| 内容
                parts = line.split('|')
                if len(parts) > 1:
                    booking_data["group_info"]["departure_notice"] = parts[1].strip()
            else:
                # 查找后续行的详细内容
                for j in range(i+1, min(i+5, len(lines))):
                    if lines[j].strip() and not lines[j].startswith('---') and '预订及出行须知' not in lines[j]:
                        booking_data["group_info"]["departure_notice"] = lines[j].strip()
                        break
    
    # 6. 提取预订及出行须知
    in_requirements = False
    for line in lines:
        if '预订及出行须知' in line:
            in_requirements = True
            continue
        
        if in_requirements:
            if '违约条款' in line:
                in_requirements = False
                break
            
            # 收集须知条目
            if line.strip() and not line.startswith('*') and not line.startswith('#') and len(line.strip()) > 20:
                booking_data["booking_requirements"].append(line.strip())
    
    # 7. 提取违约条款
    in_violation = False
    current_violation_type = ""
    
    for i, line in enumerate(lines):
        if '违约条款' in line:
            in_violation = True
            continue
        
        if in_violation:
            if '出行指南' in line:
                in_violation = False
                break
            
            if '旅行社违约' in line:
                current_violation_type = "agency"
                booking_data["violation_terms"]["agency_violation"].append(line.split('：')[1].strip())
                continue
            elif '旅游者违约' in line:
                current_violation_type = "tourist"
                booking_data["violation_terms"]["tourist_violation"].append(line.split('：')[1].strip())
                continue
            
            # 收集违约条款内容
            if line.strip() and not line.startswith('---') and not '行程前|' in line:
                if current_violation_type == "agency":
                    booking_data["violation_terms"]["agency_violation"].append(line.strip())
                elif current_violation_type == "tourist":
                    booking_data["violation_terms"]["tourist_violation"].append(line.strip())
    
    # 8. 提取出行指南
    in_guide = False
    for line in lines:
        if '出行指南' in line:
            in_guide = True
            continue
        
        if in_guide:
            if '保障提示' in line or '支付信息' in line:
                in_guide = False
                break
            
            # 收集出行指南条目
            if line.strip() and len(line.strip()) > 10 and not line.startswith('*') and not line.startswith('#'):
                booking_data["travel_guide"].append(line.strip())
    
    # 9. 提取安全提示（从出行指南中分离出安全相关内容）
    safety_keywords = ['安全', '危险', '风险', '注意', '禁忌', '避免', '谨慎', '警示']
    for guide_item in booking_data["travel_guide"]:
        if any(keyword in guide_item for keyword in safety_keywords):
            booking_data["safety_tips"].append(guide_item)
    
    # 从出行指南中移除已归类为安全提示的内容
    booking_data["travel_guide"] = [item for item in booking_data["travel_guide"] 
                                   if item not in booking_data["safety_tips"]]

    # 10. 提取出行指南
    in_protection = False
    for line in lines:
        if '保障提示' in line:
            in_protection = True
            continue

        if in_protection:
            if '支付信息' in line:
                in_protection = False
                break

            # 收集出行指南条目
            if line.strip() and len(line.strip()) > 10 and not line.startswith('*') and not line.startswith('#'):
                booking_data["protection_tips"].append(line.strip())
    
    # 11. 提取支付信息
    in_payment = False
    for line in lines:
        if '支付信息' in line:
            in_payment = True
            continue
        
        if in_payment:
            if '常见支付问题' in line:
                break
            
            # 提取支持的支付方式
            if '支持' in line and ('现金' in line or '信用卡' in line or '网银' in line):
                # 解析支付方式
                payment_methods = []
                if '现金' in line:
                    payment_methods.append('现金')
                if '信用卡' in line:
                    payment_methods.append('信用卡')
                if '网银' in line or '第三方' in line:
                    payment_methods.append('网银/第三方')
                if '礼品卡' in line:
                    payment_methods.append('礼品卡')
                if '储蓄卡' in line:
                    payment_methods.append('储蓄卡')
                if '现金余额' in line:
                    payment_methods.append('现金余额')
                if '拿去花' in line:
                    payment_methods.append('拿去花')
                
                booking_data["payment_info"]["supported_methods"] = payment_methods
    
    # 12. 提取支付说明
    in_payment_notes = False
    for line in lines:
        if '常见支付问题' in line:
            in_payment_notes = True
            continue
        
        if in_payment_notes:
            if line.strip() and len(line.strip()) > 10:
                booking_data["payment_info"]["payment_notes"].append(line.strip().replace('_', ''))
    
    print(f"✅ 数据提取完成！")
    print(f"   - 商品ID: {booking_data['product_id']}")
    print(f"   - 代理社: {booking_data['travel_agency_info']['agent']}")
    print(f"   - 委托社: {booking_data['travel_agency_info']['delegate']}")
    print(f"   - 预订要求: {len(booking_data['booking_requirements'])} 条")
    print(f"   - 出行指南: {len(booking_data['travel_guide'])} 条")
    print(f"   - 安全提示: {len(booking_data['safety_tips'])} 条")
    print(f"   - 支付方式: {len(booking_data['payment_info']['supported_methods'])} 种")
    
    return booking_data

async def crawl_and_extract_booking_note_data(url):
    """
    爬取携程预订须知页面并提取结构化数据
    """
    print(f"🚀 开始爬取携程预订须知页面: {url}")
    
    # 配置浏览器 - 模拟手机浏览器，优化速度
    browser_config = BrowserConfig(
        browser_type="chromium",
        headless=True,
        viewport_width=375,
        viewport_height=812,
        user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
    )
    
    # 配置爬取参数 - 最大化速度优化
    crawl_config = CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS,
        # wait_for=None,  # 不等待特定条件
        page_timeout=10000,  # 进一步减少超时时间到10秒
        delay_before_return_html=2.0,  # 只等待2秒让页面加载
        js_code="""
        // 极简滚动脚本
        async function fastScroll() {
            // 快速滚动到底部
            window.scrollTo(0, document.body.scrollHeight);
            await new Promise(resolve => setTimeout(resolve, 500));
            
            // 滚动到顶部
            window.scrollTo(0, 0);
            await new Promise(resolve => setTimeout(resolve, 200));
        }
        
        await fastScroll();
        """
    )
    
    async with AsyncWebCrawler(config=browser_config) as crawler:
        try:
            print("📱 正在快速爬取页面内容...")
            result = await crawler.arun(url=url, config=crawl_config)
            
            if result.success:
                print("✅ 页面爬取成功！")
                
                # 生成时间戳
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                
                # # 保存原始HTML
                # html_filename = f"ctrip_booking_note_html_{timestamp}.html"
                # with open(html_filename, 'w', encoding='utf-8') as f:
                #     f.write(result.html)
                # print(f"💾 原始HTML已保存: {html_filename}")
                
                # # 保存Markdown
                # markdown_filename = f"ctrip_booking_note_markdown_{timestamp}.md"
                # with open(markdown_filename, 'w', encoding='utf-8') as f:
                #     f.write(result.markdown)
                # print(f"📝 Markdown已保存: {markdown_filename}")
                
                # 提取结构化数据
                booking_data = extract_booking_note_data_from_markdown(result.markdown, url)
                
                # # 保存JSON数据
                # json_filename = f"ctrip_booking_note_data_{timestamp}.json"
                # with open(json_filename, 'w', encoding='utf-8') as f:
                #     json.dump(booking_data, f, ensure_ascii=False, indent=2)
                # print(f"📊 结构化数据已保存: {json_filename}")
                
                return booking_data
                
            else:
                print(f"❌ 页面爬取失败: {result.error_message}")
                return None
                
        except Exception as e:
            print(f"💥 爬取过程中发生错误: {str(e)}")
            return None

async def main():
    """
    主函数 - 测试爬虫功能
    """
    # 测试URL
    test_url = "https://m.ctrip.com/webapp/vacations/tour/detail_booking_note?productId=61162192"
    
    print("🎯 携程预订须知爬虫测试开始")
    print("=" * 50)
    
    # 执行爬取
    result = await crawl_and_extract_booking_note_data(test_url)
    
    if result:
        print("\n🎉 爬取测试完成！")
        print("=" * 50)
        print("📋 数据摘要:")
        print(f"   商品ID: {result.get('product_id', 'N/A')}")
        print(f"   代理社: {result.get('travel_agency_info', {}).get('agent', 'N/A')}")
        print(f"   委托社: {result.get('travel_agency_info', {}).get('delegate', 'N/A')}")
        print(f"   预订要求: {len(result.get('booking_requirements', []))} 条")
        print(f"   出行指南: {len(result.get('travel_guide', []))} 条")
        print(f"   安全提示: {len(result.get('safety_tips', []))} 条")
        print(f"   支付方式: {len(result.get('payment_info', {}).get('supported_methods', []))} 种")
    else:
        print("\n❌ 爬取测试失败！")

async def crawl_ctrip_booking_notes(url):
    """
    供 FastAPI 调用的预订须知爬取函数
    
    Args:
        url: 携程商品详情页URL
        
    Returns:
        dict: 包含success状态和data数据的字典
    """
    try:
        # 构建预订须知页面URL
        if 'productid=' in url:
            product_id_match = re.search(r'productid=(\d+)', url)
            if product_id_match:
                product_id = product_id_match.group(1)
                booking_note_url = f"https://m.ctrip.com/webapp/vacations/tour/detail_booking_note?productId={product_id}"
            else:
                return {"success": False, "error": "无法从URL中提取产品ID"}
        else:
            return {"success": False, "error": "URL格式不正确"}
        
        # 执行爬取
        result = await crawl_and_extract_booking_note_data(booking_note_url)
        
        if result:
            return {
                "success": True,
                "data": result
            }
        else:
            return {
                "success": False,
                "error": "预订须知数据爬取失败"
            }
            
    except Exception as e:
        return {
            "success": False,
            "error": f"爬取过程中发生错误: {str(e)}"
        }

if __name__ == "__main__":
    asyncio.run(main()) 