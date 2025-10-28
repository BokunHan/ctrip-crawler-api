"""
携程数据同步爬虫 API 服务
提供商品详情、行程攻略、预订须知三个核心接口
"""

import asyncio
import json
import logging
import sys
import os
import concurrent.futures
from datetime import datetime
from typing import Dict, Any, Optional
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
from pydantic import BaseModel, Field, HttpUrl

# Windows环境下设置事件循环策略，解决异步冲突问题
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

# 导入爬虫模块
from ctrip_detail_crawler import crawl_and_extract_ctrip_data
from ctrip_itinerary_crawler import extract_ctrip_itinerary
from ctrip_booking_crawler import crawl_ctrip_booking_notes
from ctrip_swiper_crawler import crawl_and_extract_swiper
from ctrip_prices_crawler import crawl_and_extract_prices
from ctrip_snapshot_itinerary_crawler import crawl_and_extract_snapshot
from ctrip_routeId_crawler import crawl_and_extract_route_ids
from ctrip_review_crawler import crawl_and_extract_reviews


# 创建 FastAPI 应用
app = FastAPI(
    title="携程数据同步爬虫 API 测试强制更新版本",
    description="提供携程商品详情、行程攻略、预订须知的数据爬取服务",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# 添加 CORS 中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 响应模型
class ApiResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None
    timestamp: str

class ProductDetailResponse(BaseModel):
    product_id: str
    title: str
    subtitle: str
    price: str
    product_images: list
    detail_images: list
    overview: dict
    features: list
    cost_info: dict

class ItineraryResponse(BaseModel):
    product_info: dict
    itinerary: list
    metadata: dict

class BookingNoteResponse(BaseModel):
    product_id: str
    booking_notes: dict
    metadata: dict

class SnapshotRequest(BaseModel):
    url: HttpUrl = Field(..., description="要爬取的携程产品快照页面的完整URL")

def build_product_url(product_id: str, url_type: str) -> str:
    """根据产品ID和类型构建携程URL"""
    base_urls = {
        "detail": "https://m.ctrip.com/webapp/xtour/detail?rv=1&productid={}&productId={}&isRedirect=tour_h5",
        "itinerary": "https://m.ctrip.com/webapp/xtour/detailComplexRoute?ProductId={}&Alias=A",
        "booking_note": "https://m.ctrip.com/webapp/xtour/detail?rv=1&productid={}&productId={}&isRedirect=tour_h5",
        "swiper": "https://m.ctrip.com/webapp/vacations/tour/detail_picture_list?productId={}",
        "prices": "https://m.ctrip.com/webapp/xtour/detail?rv=1&productid={}&productId={}&isRedirect=tour_h5",
        "route_ids": "https://m.ctrip.com/webapp/xtour/detail?rv=1&productid={}&productId={}&isRedirect=tour_h5",
        "reviews": "https://m.ctrip.com/webapp/vacations/order/public/comment_list?channel=vacations-grp&queryid={}&scene=PRODUCT_QUERY"
    }

    url_template = base_urls[url_type]

    # 检查URL模板需要几个product_id
    num_ids_needed = url_template.count('{}')

    if num_ids_needed == 2:
        # 如果需要两个ID，就传递两次
        return url_template.format(product_id, product_id)
    else:
        # 否则，只传递一次
        return url_template.format(product_id)

# 创建线程池执行器
executor = concurrent.futures.ThreadPoolExecutor(max_workers=3)

@app.get("/", response_model=ApiResponse)
async def root():
    """根路径，返回API信息"""
    return ApiResponse(
        success=True,
        message="携程数据同步爬虫 API 服务运行中",
        data={
            "version": "1.0.0",
            "description": "专为uni云数据库数据同步设计的爬虫服务",
            "endpoints": [
                "/api/detail/{product_id}",
                "/api/itinerary/{product_id}",
                "/api/booking_note/{product_id}",
                "/api/route_ids/{product_id}",
                "/api/reviews/{product_id}"
            ]
        },
        timestamp=datetime.now().isoformat()
    )

@app.get("/health")
async def health_check():
    """健康检查接口"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

@app.get("/api/detail/{product_id}", response_model=ApiResponse)
async def get_product_detail(product_id: str):
    """
    获取商品详情信息
    
    Args:
        product_id: 携程商品ID
        
    Returns:
        商品详情数据，包括标题、价格、图片、特色等信息
    """
    try:

        
        # 构建URL
        url = build_product_url(product_id, "detail")
        
        # 使用线程池执行爬虫函数，避免异步冲突
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            executor, 
            lambda: asyncio.run(crawl_and_extract_ctrip_data(url))
        )
        
        if result["success"]:

            return ApiResponse(
                success=True,
                message="获取商品详情成功",
                data=result["product_data"],
                timestamp=datetime.now().isoformat()
            )
        else:
 
            raise HTTPException(status_code=500, detail=f"爬取失败: {result['error']}")
            
    except Exception as e:

        raise HTTPException(status_code=500, detail=f"服务器内部错误: {str(e)}")

@app.get("/api/itinerary/{product_id}", response_model=ApiResponse)
async def get_product_itinerary(product_id: str):
    """
    获取商品行程攻略
    
    Args:
        product_id: 携程商品ID
        
    Returns:
        详细的行程安排数据，包括每日活动、景点、交通等信息
    """
    try:
        
        # 构建URL
        url = build_product_url(product_id, "itinerary")
        
        # 使用线程池执行爬虫函数，避免异步冲突
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            executor, 
            lambda: asyncio.run(extract_ctrip_itinerary(url))
        )
        
        if result:
            return ApiResponse(
                success=True,
                message="获取行程攻略成功",
                data=result,
                timestamp=datetime.now().isoformat()
            )
        else:
            raise HTTPException(status_code=500, detail="行程数据爬取失败")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"服务器内部错误: {str(e)}")

@app.get("/api/booking_note/{product_id}", response_model=ApiResponse)
async def get_booking_note(product_id: str):
    """
    获取商品预订须知
    
    Args:
        product_id: 携程商品ID
        
    Returns:
        预订须知数据，包括费用说明、退改政策、注意事项等
    """
    try:
        
        # 构建URL
        url = build_product_url(product_id, "booking_note")
        
        # 使用线程池执行爬虫函数，避免异步冲突
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            executor, 
            lambda: asyncio.run(crawl_ctrip_booking_notes(url))
        )
        
        if result and result.get("success"):
            return ApiResponse(
                success=True,
                message="获取预订须知成功",
                data=result["data"],
                timestamp=datetime.now().isoformat()
            )
        else:
            raise HTTPException(status_code=500, detail="预订须知数据爬取失败")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"服务器内部错误: {str(e)}")


@app.get("/api/swiper/{product_id}", response_model=ApiResponse)
async def get_product_swiper(product_id: str):
    """
    获取商品的所有轮播图图片地址

    Args:
        product_id: 携程商品ID

    Returns:
        轮播图图片列表数据
    """
    try:
        # 构建URL
        url = build_product_url(product_id, "swiper")

        # 使用线程池执行爬虫函数
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            executor,
            lambda: asyncio.run(crawl_and_extract_swiper(url))
        )

        if result and result.get("success"):
            return ApiResponse(
                success=True,
                message="获取商品轮播图图片列表成功",
                data=result["data"],
                timestamp=datetime.now().isoformat()
            )
        else:
            error_message = result.get("error", "未知错误")
            raise HTTPException(status_code=500, detail=f"轮播图图片列表数据爬取失败: {error_message}")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"服务器内部错误: {str(e)}")


@app.get("/api/prices/{product_id}", response_model=ApiResponse)
async def get_product_prices(product_id: str):
    """
    获取商品近期的所有每日价格

    Args:
        product_id: 携程商品ID

    Returns:
        商品价格日历数据
    """
    try:
        # 构建URL
        url = build_product_url(product_id, "prices")

        # 使用线程池执行爬虫函数
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            executor,
            lambda: asyncio.run(crawl_and_extract_prices(url))
        )

        if result and result.get("success"):
            return ApiResponse(
                success=True,
                message="获取商品价格日历成功",
                data=result["data"],
                timestamp=datetime.now().isoformat()
            )
        else:
            error_message = result.get("error", "未知错误")
            raise HTTPException(status_code=500, detail=f"价格日历数据爬取失败: {error_message}")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"服务器内部错误: {str(e)}")


@app.post("/api/snapshot_itinerary", response_model=ApiResponse)
async def get_snapshot_itinerary(request: SnapshotRequest):
    """
    接收一个产品快照URL，爬取并返回结构化的行程数据
    """
    try:
        # 直接使用请求中传递的URL
        url = str(request.url)

        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            executor,
            # 注意：这里我们调用的是新脚本里的 crawl_and_extract_snapshot
            lambda: asyncio.run(crawl_and_extract_snapshot(url))
        )

        if result and result.get("success"):
            return ApiResponse(
                success=True,
                message="获取快照行程成功",
                data=result.get("data"),
                timestamp=datetime.now().isoformat()
            )
        else:
            error_message = result.get("error", "未知错误")
            raise HTTPException(status_code=500, detail=f"快照行程爬取失败: {error_message}")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"服务器内部错误: {str(e)}")


@app.get("/api/route_ids/{product_id}", response_model=ApiResponse)
async def get_product_route_ids(product_id: str):
    """
    获取商品详情页面中所有的 multiRouteId_xxxxxxxx 的id

    Args:
        product_id: 携程商品ID

    Returns:
        一个包含所有不重复 route ID 的列表
    """
    try:
        # 构建URL
        url = build_product_url(product_id, "route_ids")

        # 使用线程池执行爬虫函数
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            executor,
            lambda: asyncio.run(crawl_and_extract_route_ids(url))
        )

        if result and result.get("success"):
            return ApiResponse(
                success=True,
                message="获取 Route IDs 成功",
                data=result["data"],
                timestamp=datetime.now().isoformat()
            )
        else:
            error_message = result.get("error", "未知错误")
            raise HTTPException(status_code=500, detail=f"Route IDs 数据爬取失败: {error_message}")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"服务器内部错误: {str(e)}")


@app.get("/api/reviews/{product_id}", response_model=ApiResponse)
async def get_product_reviews(product_id: str):
    """
    获取商品的所有评论（自动滚动到底部）

    Args:
        product_id: 携程商品ID (即 queryid)

    Returns:
        商品评论列表数据
    """
    try:
        # 构建URL
        url = build_product_url(product_id, "reviews")

        # 使用线程池执行爬虫函数
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            executor,
            lambda: asyncio.run(crawl_and_extract_reviews(url))
        )

        if result and result.get("success"):
            return ApiResponse(
                success=True,
                message="获取商品评论列表成功",
                data=result["data"],
                timestamp=datetime.now().isoformat()
            )
        else:
            error_message = result.get("error", "未知错误")
            raise HTTPException(status_code=500, detail=f"评论列表数据爬取失败: {error_message}")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"服务器内部错误: {str(e)}")


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    ) 