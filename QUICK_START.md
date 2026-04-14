# 🚀 快速启动指南

## ✅ 当前状态

**核心模块测试**: ✅ **通过**
- G-code 生成器正常工作
- 切削参数计算正常
- 已生成测试文件：`output/test_part_20260414_002609.nc`

---

## 📋 启动方式（3 种）

### 方式一：立即测试（无需安装依赖）⭐推荐

**已经成功运行！** 查看生成的 G-code：

```bash
# 在 WSL 中
cat /mnt/g/projects/cad-to-gcode/output/test_part_*.nc

# 或在 Windows 资源管理器中打开
G:\projects\cad-to-gcode\output\
```

**运行更多测试**：
```bash
cd /mnt/g/projects/cad-to-gcode
python3 scripts/minimal_test.py
```

---

### 方式二：完整 API 服务器（需要安装依赖）

#### Windows 环境（推荐）

1. **打开 PowerShell 或 CMD**（在 Windows 中，不是 WSL）

2. **进入项目目录**：
   ```cmd
   G:
   cd G:\projects\cad-to-gcode
   ```

3. **创建虚拟环境**：
   ```cmd
   python -m venv venv
   ```

4. **激活虚拟环境**：
   ```cmd
   venv\Scripts\activate
   ```

5. **安装项目依赖**：
   ```cmd
   pip install -e .
   ```
   
   这会安装：
   - `pydantic` - 数据验证
   - `pyyaml` - YAML 配置解析
   - `numpy` - 数值计算
   - `Pillow` - 图像处理
   - `requests` - HTTP 请求
   - `fastapi` - Web 框架
   - `uvicorn` - ASGI 服务器

6. **启动 API 服务器**：
   ```cmd
   uvicorn src.web.api:app --reload --host 0.0.0.0 --port 8000
   ```

7. **访问浏览器**：
   - 📖 **API 文档**: http://localhost:8000/docs
   - ❤️ **健康检查**: http://localhost:8000/health
   - 📊 **材料列表**: http://localhost:8000/materials

#### WSL 环境

如果你想在 WSL 中运行：

```bash
cd /mnt/g/projects/cad-to-gcode

# 使用已有的 venv
source venv/bin/activate

# 安装依赖（可能需要较长时间）
python -m pip install -e .

# 启动服务器
uvicorn src.web.api:app --reload --host 0.0.0.0 --port 8000
```

---

### 方式三：使用启动脚本

#### Windows

```cmd
cd G:\projects\cad-to-gcode
scripts\start.bat dev
```

#### WSL/Linux

```bash
cd /mnt/g/projects/cad-to-gcode
chmod +x scripts/start.sh
./scripts/start.sh local
```

---

## 🌐 本地访问地址

启动成功后，在**同一台电脑**的浏览器中访问：

| 功能 | URL | 说明 |
|------|-----|------|
| 📖 **Swagger UI** | http://localhost:8000/docs | 交互式 API 文档 |
| 📘 **ReDoc** | http://localhost:8000/redoc | 美观的 API 文档 |
| ❤️ **健康检查** | http://localhost:8000/health | 服务状态 |
| 📊 **材料列表** | http://localhost:8000/materials | 支持的材料 |
| 🔧 **刀具列表** | http://localhost:8000/tools | 可用刀具 |

---

## 🧪 测试 API

### 方法 1: 使用 Swagger UI（最简单）

1. 打开 http://localhost:8000/docs
2. 点击任意端点（如 `POST /gcode/generate`）
3. 点击 "Try it out"
4. 填写参数：
   ```json
   {
     "start_diameter": 50,
     "end_diameter": 30,
     "length": 100,
     "material": "45#钢",
     "machine_system": "FANUC"
   }
   ```
5. 点击 "Execute"
6. 查看返回的 G-code

### 方法 2: 使用 curl

```bash
# 健康检查
curl http://localhost:8000/health

# 获取材料列表
curl http://localhost:8000/materials

# 获取切削参数
curl -X POST http://localhost:8000/cutting-params \
  -H "Content-Type: application/json" \
  -d "{\"material\": \"45#钢\", \"operation\": \"粗车\"}"

# 生成 G-code
curl -X POST http://localhost:8000/gcode/generate \
  -H "Content-Type: application/json" \
  -d "{\"start_diameter\": 50, \"end_diameter\": 30, \"length\": 100, \"material\": \"45#钢\"}"
```

### 方法 3: 使用 Python

```python
import requests

# 健康检查
r = requests.get("http://localhost:8000/health")
print(r.json())

# 生成 G-code
r = requests.post(
    "http://localhost:8000/gcode/generate",
    json={
        "start_diameter": 50,
        "end_diameter": 30,
        "length": 100,
        "material": "45#钢"
    }
)
print(r.json()["gcode"])
```

---

## 📁 项目文件位置

所有文件都在 **G 盘**（避免占用 C 盘空间）：

```
G:\projects\cad-to-gcode\
│
├── 📄 README.md              # 项目说明
├── 📄 DEPLOYMENT.md          # 部署指南
├── 📄 QUICK_START.md         # 本文件
│
├── ⚙️ config/
│   ├── config.yaml           # 主配置
│   └── cutting_rules.yaml    # 切削参数数据库
│
├── 🐍 src/
│   ├── core/
│   │   └── process_planning.py   # 工艺规划
│   ├── cam/
│   │   └── gcode_generator.py    # G-code 生成
│   └── web/
│       └── api.py                # Web API
│
├── 🧪 scripts/
│   ├── start.bat             # Windows 启动脚本
│   ├── start.sh              # Linux 启动脚本
│   ├── minimal_test.py       # 极简测试（✅已运行）
│   └── test_processor.py     # 完整测试
│
├── 📝 output/                # G-code 输出目录
│   └── test_part_*.nc        # 测试生成的文件
│
└── 🐳 Dockerfile             # Docker 配置（可选）
    docker-compose.yml
```

---

## ❓ 常见问题

### Q: 安装依赖很慢怎么办？

**A**: 使用国内镜像：
```cmd
pip install -e . -i https://pypi.tuna.tsinghua.edu.cn/simple
```

### Q: 端口 8000 被占用怎么办？

**A**: 使用其他端口：
```cmd
uvicorn src.web.api:app --reload --port 8001
```
然后访问 http://localhost:8001/docs

### Q: 如何在 Windows 和 WSL 之间访问文件？

**A**: 
- Windows → WSL: `\\wsl$\Ubuntu\mnt\g\projects\cad-to-gcode`
- WSL → Windows: `/mnt/g/projects/cad-to-gcode`

### Q: 没有 Python 怎么办？

**A**: 下载安装：
- 官网：https://www.python.org/downloads/
- 或微软商店：搜索 "Python 3.11"

### Q: 想完全不用安装就能用？

**A**: 使用 Docker（但需要 Docker Desktop）：
1. 安装 Docker Desktop
2. 在项目目录运行：`docker-compose up --build`
3. 访问 http://localhost:8000/docs

---

## 🎯 推荐流程

### 第一次使用：

1. ✅ **已完成**：运行 `python3 scripts/minimal_test.py` 验证核心功能
2. 📥 在 Windows 中安装依赖：`pip install -e .`
3. 🚀 启动 API：`uvicorn src.web.api:app --reload`
4. 🌐 浏览器访问：http://localhost:8000/docs
5. 🧪 在 Swagger UI 中测试各个端点

### 日常开发：

```bash
# WSL 中
cd /mnt/g/projects/cad-to-gcode
source venv/bin/activate  # 如果创建了 venv
python3 scripts/minimal_test.py  # 快速测试

# 或启动 API
uvicorn src.web.api:app --reload
```

---

## 📞 需要帮助？

- 📖 详细文档：`README.md`
- 🔧 部署指南：`DEPLOYMENT.md`
- 🐛 问题反馈：GitHub Issues

---

**最后更新**: 2026-04-14 00:26
**测试状态**: ✅ 核心模块正常工作
