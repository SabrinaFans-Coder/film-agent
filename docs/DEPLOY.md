# Film-Agent 部署指南

## 目录
- [前置准备](#前置准备)
- [Docker 化](#docker-化)
- [发布到 GitHub](#发布到-github)
- [GitHub Actions 自动构建（可选）](#github-actions-自动构建可选)
- [常见问题](#常见问题)

---

## 前置准备

### 你需要提供 / 确认的信息

| 项目 | 说明 | 示例 |
|------|------|------|
| GitHub 用户名 | 你的 GitHub 账号 | `SabrinaFans-Coder` |
| 仓库名 | 创建的仓库名称 | `film-agent` |
| MySQL 方案 | A: Docker Compose 内置 MySQL |
| Docker 镜像推送目标 | Docker Hub / GHCR / 仅本地 | Docker Hub |
| Docker Hub 用户名 | 如果推送到 Docker Hub | `SabrinaFansHe` |
| 是否需要 CI/CD | GitHub Actions 自动构建镜像 | 是 |

### 你需要安装的工具

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (Windows/Mac) 或 Docker Engine (Linux)
- [Git](https://git-scm.com/)（已安装则跳过）
- GitHub 账号

---

## Docker 化

### 1. 项目文件结构 (Docker 视角)

```
film-agent/
├── Dockerfile              # 多阶段构建
├── docker-compose.yml      # 编排服务
├── .dockerignore           # 排除不需要的文件
├── requirements.txt
├── app/                    # FastAPI 后端
├── frontend/               # Vue 3 前端 (构建后变为静态文件)
├── data/                   # ChromaDB + SQLite (volume 挂载)
└── .env.example            # 环境变量模板 (可提交到 Git)
```

### 2. 创建 `Dockerfile`

在项目根目录创建 `Dockerfile`：

```dockerfile
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
```

### 3. 创建 `docker-compose.yml`

#### 方案 A：内置 MySQL（推荐，开箱即用）

```yaml
version: "3.8"

services:
  app:
    build: .
    container_name: film-agent
    ports:
      - "8000:8000"
    env_file:
      - .env
    volumes:
      - ./data:/app/data          # ChromaDB + SQLite 持久化
    depends_on:
      mysql:
        condition: service_healthy
    restart: unless-stopped

  mysql:
    image: mysql:8.0
    container_name: film-agent-mysql
    environment:
      MYSQL_ROOT_PASSWORD: ${MYSQL_ROOT_PASSWORD:-filmagent123}
      MYSQL_DATABASE: ${MYSQL_DATABASE:-film_agent}
      MYSQL_USER: ${MYSQL_USER:-filmagent}
      MYSQL_PASSWORD: ${MYSQL_PASSWORD:-filmagent123}
    ports:
      - "3307:3306"               # 映射到 3307 避免与本地 MySQL 冲突
    volumes:
      - mysql_data:/var/lib/mysql
    healthcheck:
      test: ["CMD", "mysqladmin", "ping", "-h", "localhost"]
      interval: 10s
      timeout: 5s
      retries: 5
    restart: unless-stopped

volumes:
  mysql_data:
```

#### 方案 B：连接外部 MySQL

```yaml
version: "3.8"

services:
  app:
    build: .
    container_name: film-agent
    ports:
      - "8000:8000"
    env_file:
      - .env
    volumes:
      - ./data:/app/data
    restart: unless-stopped
```

### 4. 创建 `.dockerignore`

```dockerignore
# Python
__pycache__/
*.pyc
.venv/
.pytest_cache/

# Frontend
frontend/node_modules/
frontend/dist/

# IDE
.idea/
.vscode/

# Git
.git/
.gitignore

# Env (不要打包进镜像!)
.env

# Data (运行时通过 volume 挂载)
data/

# Docs
docs/

# Tests
tests/
```

### 5. 创建 `.env.example`（安全模板，可提交到 Git）

```env
# DeepSeek API
DEEPSEEK_API_KEY=your-deepseek-api-key
DEEPSEEK_BASE_URL=https://api.deepseek.com/v1
DEEPSEEK_MODEL=deepseek-chat

# TMDB API
TMDB_API_KEY=your-tmdb-api-key
TMDB_BASE_URL=https://api.themoviedb.org/3

# MySQL (方案A使用，方案B则填你外部数据库的信息)
MYSQL_ROOT_PASSWORD=filmagent123
MYSQL_DATABASE=film_agent
MYSQL_USER=filmagent
MYSQL_PASSWORD=filmagent123
MYSQL_HOST=mysql
MYSQL_PORT=3306
```

### 6. 更新 `.gitignore` 追加以下内容

```gitignore
# Docker
docker-compose.override.yml

# Env (确保 .env 不会被提交)
.env
.env.local
.env.*.local

# Frontend build
frontend/dist/

# IDE
.vscode/
*.swp
*.swo
```

### 7. 构建与运行

```bash
# 构建镜像
docker compose build

# 启动所有服务 (后台运行)
docker compose up -d

# 查看日志
docker compose logs -f app

# 停止服务
docker compose down

# 停止并删除数据卷 (重置数据库)
docker compose down -v
```

访问 `http://localhost:8000` 即可使用。

### 8. 推送到镜像仓库（可选）

#### Docker Hub

```bash
# 登录
docker login

# 构建并打标签
docker build -t your-dockerhub-username/film-agent:latest .
docker build -t your-dockerhub-username/film-agent:v0.2.0 .

# 推送
docker push your-dockerhub-username/film-agent:latest
docker push your-dockerhub-username/film-agent:v0.2.0
```

#### GitHub Container Registry (GHCR)

```bash
# 登录
echo $GITHUB_TOKEN | docker login ghcr.io -u your-username --password-stdin

# 构建并打标签
docker build -t ghcr.io/your-username/film-agent:latest .

# 推送
docker push ghcr.io/your-username/film-agent:latest
```

---

## 发布到 GitHub

### 前提：处理敏感信息！

发布前**必须**确保 `.env` 不会提交。检查 `.gitignore` 是否包含 `.env`，然后将真实密钥替换为模板：

```bash
# 如果之前错误地提交了 .env，从 Git 历史中移除
git rm --cached .env       # 仅从 Git 移除，保留本地文件
```

### 步骤

#### 1. 在 GitHub 上创建仓库

- 登录 [GitHub](https://github.com) → 右上角 `+` → `New repository`
- 填入仓库名 (例如 `film-agent`)
- 描述 (可选): `AI-powered film recommendation agent`
- 选择 Public 或 Private
- **不要**勾选 "Add a README file"（已有项目，否则会冲突）
- 点击 `Create repository`

#### 2. 添加 Remote 并推送

```bash
# 添加远程仓库
git remote add origin https://github.com/你的用户名/film-agent.git

# 设置默认分支名为 main (如果还不是)
git branch -M main

# 推送代码
git push -u origin main
```

如果 `main` 分支已经存在且叫 `master`：

```bash
git remote add origin https://github.com/你的用户名/film-agent.git
git push -u origin master
```

#### 3. 验证

打开 `https://github.com/你的用户名/film-agent` 确认代码已上传。

#### 4. 在 GitHub 上设置 Secrets (如果使用 CI/CD)

进入仓库 → `Settings` → `Secrets and variables` → `Actions`，添加以下 secrets：

| Secret Name | 说明 |
|-------------|------|
| `DOCKERHUB_USERNAME` | Docker Hub 用户名 |
| `DOCKERHUB_TOKEN` | Docker Hub Access Token |
| `DEEPSEEK_API_KEY` | （仅 CD 部署时需要） |
| `TMDB_API_KEY` | （仅 CD 部署时需要） |

---

## GitHub Actions 自动构建（可选）

在 `.github/workflows/docker-build.yml` 创建：

```yaml
name: Build and Push Docker Image

on:
  push:
    branches: [main, master]
    tags: ['v*']
  pull_request:
    branches: [main, master]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Login to Docker Hub
        uses: docker/login-action@v3
        with:
          username: ${{ secrets.DOCKERHUB_USERNAME }}
          password: ${{ secrets.DOCKERHUB_TOKEN }}

      - name: Extract metadata (tags, labels)
        id: meta
        uses: docker/metadata-action@v5
        with:
          images: your-dockerhub-username/film-agent
          tags: |
            type=ref,event=branch
            type=ref,event=pr
            type=semver,pattern={{version}}
            type=semver,pattern={{major}}.{{minor}}
            type=sha

      - name: Build and push
        uses: docker/build-push-action@v6
        with:
          context: .
          push: ${{ github.event_name != 'pull_request' }}
          tags: ${{ steps.meta.outputs.tags }}
          labels: ${{ steps.meta.outputs.labels }}
          cache-from: type=gha
          cache-to: type=gha,mode=max
```

---

## 常见问题

### Q: Docker 构建时 ChromaDB 报错？

ChromaDB 依赖 `build-essential`（gcc/g++），已在 Dockerfile 中安装。如果 `sentence-transformers` 下载模型很慢，可以在 Dockerfile 中预下载：

```dockerfile
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')"
```

### Q: 前端构建后访问 404？

确认 Dockerfile 中 `COPY --from=frontend-builder` 的路径与 `main.py` 中的 `StaticFiles` 路径一致。本项目中：
- 前端构建输出：`frontend/dist/`
- FastAPI 静态文件路径：`frontend/dist` （相对于 `main.py` 的 `../frontend/dist`）

### Q: MySQL 连接不上？

方案 A 中 MySQL 容器名是 `mysql`，应用内数据库 host 应为 `mysql`（Docker Compose 内部 DNS），端口 `3306`。

在 `.env` 中添加：
```env
MYSQL_HOST=mysql
MYSQL_PORT=3306
MYSQL_USER=filmagent
MYSQL_PASSWORD=filmagent123
MYSQL_DATABASE=film_agent
```

### Q: data 目录的数据如何在容器间共享？

通过 `docker-compose.yml` 中的 `volumes` 挂载：
```yaml
volumes:
  - ./data:/app/data
```
宿主机的 `./data` 目录映射到容器内的 `/app/data`，ChromaDB 和 SQLite 数据会持久化在宿主机上。

### Q: 如何在服务器上部署？

```bash
# 1. 在服务器上克隆代码
git clone https://github.com/你的用户名/film-agent.git
cd film-agent

# 2. 创建 .env 文件并填入真实密钥
cp .env.example .env
vim .env  # 填入真实 API Key

# 3. 启动
docker compose up -d

# 4. 配置 Nginx 反向代理 (可选)
# 将域名指向 localhost:8000 即可
```

---

## 操作清单 (Checklist)

- [ ] 确认 MySQL 方案 (A 或 B)
- [ ] 创建 `Dockerfile`
- [ ] 创建 `docker-compose.yml`
- [ ] 创建 `.dockerignore`
- [ ] 创建 `.env.example`（用模板替换真实密钥）
- [ ] 更新 `.gitignore`（确保 `.env` 不被提交）
- [ ] 检查 `.env` 是否在 Git 历史中，如有则移除
- [ ] 在 GitHub 创建仓库
- [ ] `git remote add` + `git push`
- [ ] 本地测试 `docker compose up -d`
- [ ] （可选）配置 GitHub Actions
- [ ] （可选）推送镜像到 Docker Hub / GHCR
