# 使用微软官方 Playwright Python 镜像 - 已预装 Chromium
FROM mcr.microsoft.com/playwright/python:v1.55.0-noble

# 设置工作目录
WORKDIR /app

# 设置环境变量
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DEFAULT_TIMEOUT=120 \
    PIP_RETRIES=10

# 复制依赖文件
COPY requirements.txt .

RUN apt-get update && apt-get install -y g++ python3-dev \
    curl \
    python3-venv \
    && rm -rf /var/lib/apt/lists/*

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# 安装 Python 依赖
#RUN pip install --no-cache-dir --retries 50 --timeout 60 --upgrade pip --break-system-packages && \
#    pip install --no-cache-dir --retries 50 --timeout 60 -r requirements.txt --index-url https://pypi.org/simple --break-system-packages

RUN pip install --no-cache-dir --upgrade pip \
    -i https://pypi.tuna.tsinghua.edu.cn/simple/ \
    --trusted-host pypi.tuna.tsinghua.edu.cn

RUN pip install --no-cache-dir -r requirements.txt \
    -i https://pypi.tuna.tsinghua.edu.cn/simple/ \
    --trusted-host pypi.tuna.tsinghua.edu.cn \
    --timeout 300 \
    --retries 10

# 复制应用代码
COPY . .

# 创建非 root 用户（如果不存在）
RUN if ! id -u app >/dev/null 2>&1; then \
        useradd --create-home --shell /bin/bash app && \
        mkdir -p /app/logs && \
        chown -R app:app /app; \
    fi

# 切换到非 root 用户
USER app

# 暴露端口
EXPOSE 8000

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# 直接启动热更新模式
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]