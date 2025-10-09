# 携程数据同步爬虫 API 服务

## 📖 项目简介

这是一个基于 FastAPI 和 crawl4ai 构建的携程数据爬虫 API 服务，专为旅游商家私域商城小程序提供数据同步支持。

## 🎯 核心功能

- **商品详情爬取**: 获取携程商品的完整详细信息
- **行程攻略提取**: 提取结构化的旅游行程数据
- **预订须知获取**: 获取商品的预订要求和政策信息
- **Docker 容器化**: 支持一键部署到服务器
- **API 文档**: 自动生成的 Swagger 文档

## 📋 API 接口

### 服务配置

- **默认端口**: 8000 (可通过环境变量 `API_PORT` 配置)
- **API 文档**: http://localhost:8000/docs
- **健康检查**: http://localhost:8000/health

### 1. 商品详情

```
GET /api/detail/{product_id}
```

获取指定商品的详细信息，包括标题、价格、图片、特色等。

### 2. 行程攻略

```
GET /api/itinerary/{product_id}
```

获取指定商品的完整行程安排，包括每日活动、景点、交通等。

### 3. 预订须知

```
GET /api/booking_note/{product_id}
```

获取指定商品的预订须知，包括费用说明、退改政策等。

### 4. 其他接口

- `GET /` - API 信息
- `GET /health` - 健康检查
- `GET /docs` - API 文档（Swagger UI）

## 🛠️ 技术栈

- **FastAPI**: 现代化的 Python Web 框架
- **crawl4ai**: 强大的异步网页爬取库
- **Docker**: 容器化部署
- **Chromium**: 无头浏览器
- **Pydantic**: 数据验证和序列化

## 📦 快速开始

### 方式一：Docker 部署（推荐）

1. **克隆项目**

```bash
git clone <repository-url>
cd ctrip-crawler-api
```

2. **使用 Docker Compose 启动**

```bash
docker-compose up -d --build
```

3. **检查服务状态**

```bash
curl http://localhost:8000/health
```

4. **访问 API 文档**
   打开浏览器访问: http://localhost:8000/docs

### 方式二：本地开发

1. **安装依赖**

```bash
pip install -r requirements.txt
```

2. **启动服务**

```bash
python main.py
```

## 🔧 部署脚本

项目提供了便捷的部署脚本 `deploy.sh`：

```bash
# 启动服务
./deploy.sh start

# 停止服务
./deploy.sh stop

# 重启服务
./deploy.sh restart

# 查看日志
./deploy.sh logs

# 查看状态
./deploy.sh status

# 清理资源
./deploy.sh cleanup

# 测试 API 接口
./deploy.sh test
```

## 📝 使用示例

### 获取商品详情

```bash
curl "http://localhost:8000/api/detail/61162192"
```

### 获取行程攻略

```bash
curl "http://localhost:8000/api/itinerary/61162192"
```

### 获取预订须知

```bash
curl "http://localhost:8000/api/booking_note/61162192"
```

## 🔍 响应格式

所有接口都返回统一的 JSON 格式：

```json
{
  "success": true,
  "message": "获取数据成功",
  "data": {
    // 具体数据内容
  },
  "timestamp": "2024-01-01T12:00:00"
}
```

## ⚙️ 配置说明

### 环境变量

- `API_PORT`: API 服务端口 (默认: 8000)
- `CHROME_BIN`: Chromium 浏览器路径
- `CHROME_PATH`: Chrome 路径
- `PYTHONUNBUFFERED`: Python 输出缓冲设置

### 端口配置

如需修改服务端口，可以通过以下方式：

1. **环境变量方式**:

```bash
export API_PORT=9000
./deploy.sh start
```

2. **修改配置文件**:

- `docker-compose.yml`: 修改端口映射
- `main.py`: 修改应用端口
- `Dockerfile`: 修改暴露端口

## 🎯 使用场景

本 API 服务专为以下场景设计：

1. **数据同步工具**: 作为携程数据一键同步工具的基础数据源
2. **批量数据获取**: 支持批量获取商品信息并存储到 uni 云数据库
3. **实时数据更新**: 确保获取最新的商品信息，无缓存干扰
4. **数据源头服务**: 作为数据流的起点，后续数据会缓存在云数据库中

## 🚨 注意事项

1. **资源消耗**: 爬虫服务会消耗较多内存和 CPU，建议分配至少 1GB 内存
2. **网络依赖**: 需要稳定的网络连接访问携程网站
3. **反爬机制**: 携程可能有反爬机制，建议合理控制请求频率
4. **数据实时性**: 每次请求都会获取最新数据，确保数据准确性

## 🔧 故障排除

### 常见问题

1. **容器启动失败**

   - 检查 Docker 是否正常运行
   - 查看容器日志：`docker-compose logs`
2. **爬取失败**

   - 检查网络连接
   - 确认携程网站可正常访问
   - 查看应用日志
3. **内存不足**

   - 增加 Docker 容器内存限制
   - 监控系统资源使用情况

### 日志查看

```bash
# 查看实时日志
docker-compose logs -f

# 查看最近100行日志
docker-compose logs --tail=100
```

## 📈 性能优化

1. **并发控制**: 避免同时发起过多爬取请求
2. **资源监控**: 定期监控内存和 CPU 使用情况
3. **定期清理**: 清理临时文件和日志文件
4. **请求频率**: 合理控制请求频率，避免被反爬

## 🤝 贡献指南

1. Fork 项目
2. 创建功能分支
3. 提交更改
4. 发起 Pull Request

## 📄 许可证

本项目采用 MIT 许可证。

## 📞 联系方式

如有问题或建议，请通过以下方式联系：

- 提交 Issue
- 发送邮件

---

**注意**: 本项目仅供学习和研究使用，请遵守相关网站的使用条款和法律法规。
