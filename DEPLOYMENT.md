# CAD to G-code Platform - 部署指南

## 📋 系统要求

### 最低要求
- **CPU**: 2 核心
- **内存**: 2GB RAM
- **存储**: 1GB 可用空间
- **Python**: 3.10 或更高版本

### 推荐配置
- **CPU**: 4 核心或更多
- **内存**: 4GB RAM
- **存储**: 5GB 可用空间
- **GPU**: 可选（用于 AI 功能）

## 🚀 快速开始

### 方式一：Docker（推荐）

#### 1. 安装 Docker

**Windows:**
1. 下载 Docker Desktop: https://www.docker.com/products/docker-desktop
2. 安装并启动 Docker Desktop
3. 确保 WSL2 后端已启用

**Linux (Ubuntu/Debian):**
```bash
sudo apt update
sudo apt install docker.io docker-compose
sudo systemctl start docker
sudo systemctl enable docker
```

**macOS:**
1. 下载 Docker Desktop: https://www.docker.com/products/docker-desktop
2. 拖拽到 Applications 文件夹
3. 启动 Docker Desktop

#### 2. 验证 Docker 安装

```bash
docker --version
docker compose version
```

#### 3. 启动服务

**开发模式:**
```bash
# Windows (PowerShell/CMD)
cd G:\projects\cad-to-gcode
scripts\start.bat dev

# Linux/macOS
cd /mnt/g/projects/cad-to-gcode
./scripts/start.sh dev
```

**生产模式:**
```bash
# Windows
scripts\start.bat prod

# Linux/macOS
./scripts/start.sh prod
```

#### 4. 访问 API

打开浏览器访问：
- **API 文档**: http://localhost:8000/docs
- **健康检查**: http://localhost:8000/health
- **材料列表**: http://localhost:8000/materials

#### 5. 常用命令

```bash
# 查看日志
docker-compose logs -f app

# 进入容器
docker-compose exec app bash

# 停止服务
docker-compose down

# 重启服务
docker-compose restart

# 清理所有数据
docker-compose down -v
```

---

### 方式二：本地 Python 环境

#### 1. 创建虚拟环境

```bash
# 进入项目目录
cd G:\projects\cad-to-gcode  # Windows
cd /mnt/g/projects/cad-to-gcode  # WSL/Linux

# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
# Windows:
venv\Scripts\activate

# Linux/macOS:
source venv/bin/activate
```

#### 2. 安装依赖

```bash
# 安装基础依赖
pip install -e .

# 安装开发依赖（可选）
pip install -e ".[dev]"

# 安装 Web 依赖（可选）
pip install -e ".[web]"
```

#### 3. 启动 API 服务器

```bash
# 开发模式（自动重载）
uvicorn src.web.api:app --reload --host 0.0.0.0 --port 8000

# 生产模式
uvicorn src.web.api:app --host 0.0.0.0 --port 8000 --workers 4
```

#### 4. 使用 CLI

```bash
# 查看版本
python -m src.cli version

# 列出支持的材料
python -m src.cli materials

# 列出可用刀具
python -m src.cli tools

# 显示配置
python -m src.cli config show

# 运行测试
python -m src.cli test
```

---

### 方式三：直接从 WSL 访问 Windows 文件

如果你在 WSL2 环境中：

```bash
# 1. 确认 G 盘挂载
ls /mnt/g

# 2. 进入项目目录
cd /mnt/g/projects/cad-to-gcode

# 3. 创建 Python 虚拟环境
python3 -m venv venv
source venv/bin/activate

# 4. 安装依赖
pip install -e .

# 5. 测试模块
python -c "from src.core.process_planning import CuttingRulesEngine; print('OK')"

# 6. 启动 API 服务器
uvicorn src.web.api:app --reload --host 0.0.0.0 --port 8000
```

---

## 🧪 运行测试

### 单元测试

```bash
# 所有测试
pytest tests/ -v

# 特定测试文件
pytest tests/unit/test_process_planning.py -v

# 带覆盖率报告
pytest tests/ --cov=src --cov-report=html

# 快速测试（无覆盖）
pytest tests/unit/ -q
```

### 集成测试

```bash
# 需要 API 服务器运行
pytest tests/integration/ -v -m integration
```

### 在 Docker 中运行测试

```bash
docker-compose run --rm cli test
```

---

## 📝 验证安装

### 1. 健康检查

```bash
curl http://localhost:8000/health
```

预期响应：
```json
{
  "status": "healthy",
  "version": "0.1.0",
  "timestamp": "2026-04-14T00:00:00",
  "config_loaded": true,
  "materials_count": 6
}
```

### 2. 测试 API 端点

```bash
# 获取材料列表
curl http://localhost:8000/materials

# 获取切削参数
curl -X POST http://localhost:8000/cutting-params \
  -H "Content-Type: application/json" \
  -d '{"material": "45#钢", "operation": "粗车"}'

# 生成 G-code
curl -X POST http://localhost:8000/gcode/generate \
  -H "Content-Type: application/json" \
  -d '{
    "start_diameter": 50,
    "end_diameter": 30,
    "length": 100,
    "material": "45#钢"
  }'
```

### 3. 测试 CLI

```bash
python -m src.cli materials
python -m src.cli tools
```

### 4. 运行示例脚本

```bash
python scripts/test_processor.py
```

---

## 🔧 故障排除

### Docker 相关问题

**问题**: `docker-compose: command not found`

**解决**:
```bash
# 使用新语法
docker compose up -d

# 或安装 docker-compose
sudo apt install docker-compose
```

**问题**: `Cannot connect to the Docker daemon`

**解决**:
```bash
# Windows: 启动 Docker Desktop
# Linux: 
sudo systemctl start docker
sudo usermod -aG docker $USER
# 重新登录
```

**问题**: `Port 8000 is already in use`

**解决**:
```bash
# 查找占用端口的进程
lsof -i :8000  # Linux/macOS
netstat -ano | findstr :8000  # Windows

# 停止占用进程或使用不同端口
docker-compose --project-directory . up -d
```

### Python 相关问题

**问题**: `ModuleNotFoundError: No module named 'src'`

**解决**:
```bash
# 确保在项目根目录
cd /mnt/g/projects/cad-to-gcode

# 重新安装包
pip install -e .
```

**问题**: `uvicorn: command not found`

**解决**:
```bash
# 安装 uvicorn
pip install uvicorn[standard]
```

**问题**: 中文编码错误

**解决**:
```bash
# 设置环境变量
export PYTHONIOENCODING=utf-8
export LANG=C.UTF-8
```

### 配置文件问题

**问题**: `Config file not found`

**解决**:
```bash
# 检查配置文件是否存在
ls config/config.yaml

# 创建默认配置
cp config/config.yaml.example config/config.yaml
```

---

## 📊 性能优化

### Docker 性能

```yaml
# docker-compose.yml 中添加:
deploy:
  resources:
    limits:
      cpus: '4.0'
      memory: 4G
```

### Python 性能

```bash
# 使用 PyPy（可选）
pypy -m pip install -e .

# 启用优化
export PYTHONOPTIMIZE=2
```

### 数据库优化（未来）

```bash
# 启用 Redis 缓存
docker-compose --profile with-redis up -d
```

---

## 🔐 安全建议

### 生产环境

1. **修改默认密码**
   ```yaml
   # docker-compose.yml
   environment:
     POSTGRES_PASSWORD: <strong_password>
   ```

2. **限制 CORS**
   ```python
   # src/web/api.py
   app.add_middleware(
       CORSMiddleware,
       allow_origins=["https://your-domain.com"],
       ...
   )
   ```

3. **启用 HTTPS**
   ```bash
   # 使用反向代理
   docker run -d \
     -p 443:443 \
     -v /etc/ssl/certs:/etc/ssl/certs \
     nginx:alpine
   ```

4. **限制上传大小**
   ```yaml
   # config/config.yaml
   security:
     max_file_size_mb: 10
   ```

---

## 📈 监控和日志

### 查看日志

```bash
# Docker 日志
docker-compose logs -f app

# 应用日志
tail -f logs/cad2gcode.log

# 系统日志
journalctl -u docker -f  # Linux
```

### 健康检查

```bash
# 定期检查
watch -n 5 'curl -s http://localhost:8000/health | jq .'
```

### 性能监控

```bash
# Docker 统计
docker stats cad2gcode-app

# Python 性能
pip install memory-profiler
python -m memory_profiler src/web/api.py
```

---

## 🆘 获取帮助

### 文档

- API 文档：http://localhost:8000/docs
- README: [README.md](README.md)
- AGENTS.md: [AGENTS.md](AGENTS.md)

### 社区

- GitHub Issues: https://github.com/nanfeng2021/cad-to-gcode/issues
- 邮件：nanfeng@example.com

### 调试模式

```bash
# 启用详细日志
export LOG_LEVEL=DEBUG
docker-compose up -d

# 或在配置文件中
# config/config.yaml:
# logging:
#   level: DEBUG
```

---

## ✅ 安装检查清单

- [ ] Docker 已安装并运行
- [ ] 或 Python 3.10+ 已安装
- [ ] 项目目录已克隆
- [ ] 依赖已安装
- [ ] API 服务器可访问（http://localhost:8000/docs）
- [ ] 健康检查通过
- [ ] 测试通过
- [ ] 示例 G-code 已生成

---

**最后更新**: 2026-04-13
**版本**: 0.1.0
