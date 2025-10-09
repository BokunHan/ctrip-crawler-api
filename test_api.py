#!/usr/bin/env python3
"""
携程爬虫 API 测试脚本
用于验证三个核心接口是否正常工作
"""

import asyncio
import httpx
import json
import time
import os
from typing import Dict, Any

# 测试配置
API_PORT = os.getenv("API_PORT", "8000")  # 支持环境变量配置端口
BASE_URL = f"http://localhost:{API_PORT}"
TEST_PRODUCT_ID = "61162192"  # 测试用的商品ID

class ApiTester:
    def __init__(self, base_url: str = BASE_URL):
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=60.0)
    
    async def test_health_check(self) -> bool:
        """测试健康检查接口"""
        try:
            print("🔍 测试健康检查接口...")
            response = await self.client.get(f"{self.base_url}/health")
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ 健康检查通过: {data}")
                return True
            else:
                print(f"❌ 健康检查失败: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ 健康检查异常: {str(e)}")
            return False
    
    async def test_root_endpoint(self) -> bool:
        """测试根路径接口"""
        try:
            print("🔍 测试根路径接口...")
            response = await self.client.get(f"{self.base_url}/")
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ 根路径接口正常: {data.get('message', 'N/A')}")
                return True
            else:
                print(f"❌ 根路径接口失败: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ 根路径接口异常: {str(e)}")
            return False
    
    async def test_product_detail(self, product_id: str) -> Dict[str, Any]:
        """测试商品详情接口"""
        try:
            print(f"🔍 测试商品详情接口 (ID: {product_id})...")
            start_time = time.time()
            
            response = await self.client.get(f"{self.base_url}/api/detail/{product_id}")
            
            elapsed_time = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    product_data = data.get("data", {})
                    print(f"✅ 商品详情获取成功 (耗时: {elapsed_time:.2f}s)")
                    print(f"   - 标题: {product_data.get('title', 'N/A')[:50]}...")
                    print(f"   - 价格: {product_data.get('price', 'N/A')}")
                    print(f"   - 图片数量: {len(product_data.get('product_images', []))}")
                    return {"success": True, "time": elapsed_time, "data": data}
                else:
                    print(f"❌ 商品详情获取失败: {data.get('message', 'Unknown error')}")
                    return {"success": False, "error": data.get('message')}
            else:
                print(f"❌ 商品详情接口错误: {response.status_code}")
                return {"success": False, "error": f"HTTP {response.status_code}"}
                
        except Exception as e:
            print(f"❌ 商品详情接口异常: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def test_itinerary(self, product_id: str) -> Dict[str, Any]:
        """测试行程攻略接口"""
        try:
            print(f"🔍 测试行程攻略接口 (ID: {product_id})...")
            start_time = time.time()
            
            response = await self.client.get(f"{self.base_url}/api/itinerary/{product_id}")
            
            elapsed_time = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    itinerary_data = data.get("data", {})
                    print(f"✅ 行程攻略获取成功 (耗时: {elapsed_time:.2f}s)")
                    print(f"   - 行程天数: {len(itinerary_data.get('itinerary', []))}")
                    return {"success": True, "time": elapsed_time, "data": data}
                else:
                    print(f"❌ 行程攻略获取失败: {data.get('message', 'Unknown error')}")
                    return {"success": False, "error": data.get('message')}
            else:
                print(f"❌ 行程攻略接口错误: {response.status_code}")
                return {"success": False, "error": f"HTTP {response.status_code}"}
                
        except Exception as e:
            print(f"❌ 行程攻略接口异常: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def test_booking_note(self, product_id: str) -> Dict[str, Any]:
        """测试预订须知接口"""
        try:
            print(f"🔍 测试预订须知接口 (ID: {product_id})...")
            start_time = time.time()
            
            response = await self.client.get(f"{self.base_url}/api/booking_note/{product_id}")
            
            elapsed_time = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    booking_data = data.get("data", {})
                    print(f"✅ 预订须知获取成功 (耗时: {elapsed_time:.2f}s)")
                    print(f"   - 代理社: {booking_data.get('travel_agency_info', {}).get('agent', 'N/A')}")
                    print(f"   - 预订要求: {len(booking_data.get('booking_requirements', []))} 条")
                    return {"success": True, "time": elapsed_time, "data": data}
                else:
                    print(f"❌ 预订须知获取失败: {data.get('message', 'Unknown error')}")
                    return {"success": False, "error": data.get('message')}
            else:
                print(f"❌ 预订须知接口错误: {response.status_code}")
                return {"success": False, "error": f"HTTP {response.status_code}"}
                
        except Exception as e:
            print(f"❌ 预订须知接口异常: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def run_all_tests(self, product_id: str = TEST_PRODUCT_ID):
        """运行所有测试"""
        print("🚀 开始 API 测试")
        print("=" * 60)
        
        results = {
            "health_check": False,
            "root_endpoint": False,
            "product_detail": {},
            "itinerary": {},
            "booking_note": {}
        }
        
        # 1. 健康检查
        results["health_check"] = await self.test_health_check()
        print()
        
        # 2. 根路径
        results["root_endpoint"] = await self.test_root_endpoint()
        print()
        
        # 3. 商品详情
        results["product_detail"] = await self.test_product_detail(product_id)
        print()
        
        # 4. 行程攻略
        results["itinerary"] = await self.test_itinerary(product_id)
        print()
        
        # 5. 预订须知
        results["booking_note"] = await self.test_booking_note(product_id)
        print()
        
        # 生成测试报告
        await self.generate_test_report(results)
        
        await self.client.aclose()
        return results
    
    async def generate_test_report(self, results: Dict[str, Any]):
        """生成测试报告"""
        print("📊 测试报告")
        print("=" * 60)
        
        # 统计成功率
        total_tests = 0
        passed_tests = 0
        
        # 基础接口测试
        basic_tests = ["health_check", "root_endpoint"]
        for test in basic_tests:
            total_tests += 1
            if results[test]:
                passed_tests += 1
                print(f"✅ {test}: 通过")
            else:
                print(f"❌ {test}: 失败")
        
        # 爬虫接口测试
        crawler_tests = ["product_detail", "itinerary", "booking_note"]
        for test in crawler_tests:
            total_tests += 1
            if results[test].get("success"):
                passed_tests += 1
                time_taken = results[test].get("time", 0)
                print(f"✅ {test}: 通过 (耗时: {time_taken:.2f}s)")
            else:
                error = results[test].get("error", "Unknown error")
                print(f"❌ {test}: 失败 - {error}")
        
        # 总结
        success_rate = (passed_tests / total_tests) * 100
        print(f"\n📈 测试总结:")
        print(f"   - 总测试数: {total_tests}")
        print(f"   - 通过数: {passed_tests}")
        print(f"   - 失败数: {total_tests - passed_tests}")
        print(f"   - 成功率: {success_rate:.1f}%")
        
        if success_rate == 100:
            print("\n🎉 所有测试通过！API 服务运行正常")
        elif success_rate >= 80:
            print("\n⚠️  大部分测试通过，但有部分问题需要关注")
        else:
            print("\n❌ 测试失败较多，请检查服务状态")

async def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="携程爬虫 API 测试工具")
    parser.add_argument("--url", default=BASE_URL, help="API 服务地址")
    parser.add_argument("--product-id", default=TEST_PRODUCT_ID, help="测试用的商品ID")
    
    args = parser.parse_args()
    
    tester = ApiTester(args.url)
    await tester.run_all_tests(args.product_id)

if __name__ == "__main__":
    asyncio.run(main()) 