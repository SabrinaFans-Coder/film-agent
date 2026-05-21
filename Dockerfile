# ============ 阶段1: 构建前端 ============
FROM node:22-alpine AS frontend-builder

WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# ============ 阶段2: 运行环境 ============
FROM python:3.12-slim

WORKDIR /app

# 安装系统依赖 (ChromaDB 需要)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# 安装 Python 依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制后端代码
COPY app/ ./app/

# 复制构建好的前端静态文件
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist

# 创建数据目录 (运行时通过 volume 挂载)
RUN mkdir -p /app/data

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
