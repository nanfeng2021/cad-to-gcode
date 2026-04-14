# CAD to G-code Platform - 当前功能清单

**版本**: 0.1.0  
**更新日期**: 2026-04-14  
**状态**: ✅ 核心功能已完成 | 🚧 开发中 | 📋 计划中

---

## 📊 功能总览

| 模块 | 完成度 | 状态 |
|------|--------|------|
| 工艺规划引擎 | 80% | ✅ 可用 |
| G-code 生成器 | 90% | ✅ 可用 |
| REST API | 95% | ✅ 可用 |
| 持久化存储 | 100% | ✅ 完成 |
| CAD 文件解析 | 0% | 📋 计划中 |
| AI 特征识别 | 0% | 📋 计划中 |

---

## ✅ 已实现功能

### 1️⃣ 工艺规划引擎 (`src/core/process_planning.py`)

#### 材料数据库
- ✅ **支持材料类型**:
  - 45#钢 (STEEL_45)
  - 40Cr (STEEL_40CR)
  - 不锈钢 (STAINLESS)
  - 铝合金 (ALUMINUM)
  - 黄铜 (BRASS)
  - 铸钢 (CAST_STEEL)
  - 铸铁 (CAST_IRON)

#### 加工操作类型
- ✅ 粗车 (ROUGH_TURNING)
- ✅ 精车 (FINISH_TURNING)
- ✅ 切槽 (GROOVING)
- ✅ 螺纹 (THREADING)
- ✅ 端面 (FACING)
- ✅ 镗孔 (BORING)
- ✅ 切断 (PARTING)

#### 数控系统支持
- ✅ FANUC
- ✅ Siemens
- ✅ Mitsubishi
- ✅ GSK (广数)
- ✅ HNC (华中)

#### 切削参数计算
- ✅ 主轴转速计算 (n rpm)
- ✅ 进给率计算 (f mm/rev)
- ✅ 切深计算 (ap mm)
- ✅ 切削速度计算 (v_c m/min)
- ✅ 参数验证与安全范围检查
- ✅ FANUC/Siemens 代码格式输出

#### 刀具数据库
- ✅ 外圆车刀定义
- ✅ 切槽刀定义
- ✅ 螺纹刀定义
- ✅ 镗刀定义
- ✅ 刀片材质兼容性
- ✅ 应用场景区匹配

---

### 2️⃣ G-code 生成器 (`src/cam/gcode_generator.py`)

#### 基础功能
- ✅ 程序头生成 (程序名、日期、时间、机床信息)
- ✅ 安全启动代码 (G21/G40/G97/G99)
- ✅ 换刀宏程序
- ✅ 主轴控制 (M03/M04/M05)
- ✅ 冷却液控制 (M08/M09)
- ✅ 程序结束 (M30)

#### 加工循环
- ✅ 外圆粗车循环 (G71)
- ✅ 精车循环 (G70)
- ✅ 切槽循环 (G75)
- ✅ 螺纹切削循环 (G76/G92)
- ✅ 端面车削
- ✅ 锥度车削

#### 多系统支持
- ✅ FANUC 格式输出
- ✅ Siemens 格式输出
- ✅ Mitsubishi 格式输出
- ✅ 系统特定的 M 代码映射

#### 示例程序生成
- ✅ 简单轴类零件 (generate_simple_shaft)
  - 输入：起始直径、终止直径、长度、材料
  - 输出：完整加工程序（粗车 + 精车）

---

### 3️⃣ REST API (`src/web/api.py`)

#### 健康检查
- ✅ `GET /` - API 根路径，返回基本信息
- ✅ `GET /health` - 健康检查端点
  - 返回：状态、版本、材料数量、程序数量

#### 材料管理
- ✅ `GET /materials` - 获取所有支持的材料列表
  - 返回：材料名称、代码、支持的加工操作

#### 切削参数查询
- ✅ `POST /cutting-params` - 获取切削参数
  - 请求：material, operation, tool_diameter(可选)
  - 返回：spindle_speed, feed_rate, depth_of_cut, cutting_speed, fanuc_code

#### G-code 生成
- ✅ `POST /gcode/generate` - 生成 G-code 程序
  - 请求：start_diameter, end_diameter, length, material, machine_system
  - 返回：program_name, gcode, lines, generated_at
  - **自动保存到数据库** ✅

- ✅ `POST /gcode/upload-cad` - 上传 CAD 文件并生成 G-code
  - 支持格式：.step, .stp, .igs, .ige, .dxf, .dwg
  - ⚠️ 当前为占位符实现（返回示例程序）

#### 程序管理 (持久化存储)
- ✅ `POST /programs` - 保存 G-code 程序到数据库
  - 请求：filename, content, material, operations(可选), metadata(可选)
  - 返回：program_id, filename, message

- ✅ `GET /programs` - 获取程序列表
  - 支持分页：limit, offset
  - 支持材料过滤：material
  - 返回：程序摘要列表 (id, filename, material, created_at, operation_count)

- ✅ `GET /programs/{id}` - 获取程序详情
  - 返回：完整程序信息 (id, filename, content, material, operations, created_at, metadata)

- ✅ `GET /programs/{id}/download` - 下载程序文件
  - 返回：.nc 文件 (Content-Disposition: attachment)

- ✅ `DELETE /programs/{id}` - 删除程序

#### 系统配置
- ✅ `GET /tools` - 获取可用刀具列表
- ✅ `GET /machine-systems` - 获取支持的数控系统列表

#### 错误处理
- ✅ HTTP 异常统一处理
- ✅ 全局异常捕获与日志记录
- ✅ JSON 格式错误响应

---

### 4️⃣ 持久化存储 (`src/storage/gcode_storage.py`)

#### 数据库特性
- ✅ SQLite 零配置数据库
- ✅ 自动创建表结构
- ✅ 索引优化 (created_at DESC, material)
- ✅ 事务支持与回滚

#### CRUD 操作
- ✅ `save_program()` - 保存程序，返回自增 ID
- ✅ `get_program()` - 根据 ID 获取完整程序
- ✅ `list_programs()` - 分页查询程序列表
- ✅ `delete_program()` - 删除程序
- ✅ `get_program_count()` - 统计程序总数
- ✅ `search_programs()` - 按程序名或材料搜索

#### 数据存储结构
```sql
programs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  filename TEXT NOT NULL,
  content TEXT NOT NULL,          -- G-code 完整内容
  material TEXT,                   -- 材料类型
  operations TEXT,                 -- JSON: 加工操作列表
  created_at TEXT NOT NULL,        -- ISO 格式时间戳
  metadata TEXT                    -- JSON: 额外元数据
)
```

#### 元数据支持
- ✅ 加工参数 (start_diameter, end_diameter, length)
- ✅ 机床系统 (machine_system)
- ✅ 自定义扩展字段

---

### 5️⃣ 测试与验证

#### 集成测试
- ✅ `tests/test_api_integration.py` - 完整 API 流程测试
  - 健康检查 → 生成 G-code → 列表查询 → 详情获取 → 文件下载 → 删除验证

#### 测试结果
```
✓ API Status: healthy
✓ Generated program: O2380 (32 lines)
✓ Found 1 program(s) in database
✓ Program details retrieved (1140 chars)
✓ Downloaded: O2380.nc
✓ Program 1 deleted successfully
✓ All tests passed successfully!
```

---

## 🚧 开发中功能

### CAD 文件解析
- 🚧 DXF 文件解析框架
  - 上传端点已实现 (`/gcode/upload-cad`)
  - 解析逻辑待实现 (TODO 标记)

### 配置文件加载
- ⚠️ YAML 配置解析存在语法问题
  - `config/config.yaml` 需要修复
  - `src/config/cutting_rules.yaml` 缺失

---

## 📋 计划中功能

### 1️⃣ AI 特征识别 (长期目标)
- 📋 STEP/IGES 文件解析
  - 使用 pythonocc-core 或 CadQuery
  - 提取几何特征 (圆柱、圆锥、圆弧、螺纹)
  
- 📋 特征分类与匹配
  - 识别加工特征类型
  - 匹配加工工艺模板

- 📋 智能工艺规划
  - 基于特征的工序排序
  - 自动选择刀具
  - 自动计算切削参数

### 2️⃣ 高级功能
- 📋 批量处理
  - 多零件批量生成 G-code
  - 批量导出 NC 文件

- 📋 模板系统
  - 用户自定义加工模板
  - 企业标准工艺库

- 📋 仿真验证
  - G-code 路径可视化
  - 碰撞检测

- 📋 后处理器
  - 更多数控系统支持 (HAAS, Mazak, Okuma)
  - 用户自定义后处理规则

### 3️⃣ Web 界面
- 📋 React/Vue 前端
  - 可视化参数输入
  - G-code 预览与编辑
  - 程序管理界面

- 📋 用户认证
  - JWT Token 认证
  - 权限管理

### 4️⃣ 部署优化
- 📋 Docker 容器化
  - Dockerfile 已存在，需测试
  - docker-compose.yml 配置

- 📋 数据库迁移
  - PostgreSQL/MySQL 支持 (可选)
  - 数据库迁移脚本

---

## 🔧 技术栈

| 类别 | 技术 |
|------|------|
| **后端框架** | FastAPI 0.104+ |
| **异步服务器** | Uvicorn |
| **数据验证** | Pydantic 2.0+ |
| **数据库** | SQLite 3 |
| **配置文件** | PyYAML |
| **HTTP 客户端** | Requests |
| **测试框架** | Pytest |
| **部署** | Docker, Docker Compose |

---

## 📁 项目结构

```
cad-to-gcode/
├── src/
│   ├── core/
│   │   └── process_planning.py      # 工艺规划引擎
│   ├── cam/
│   │   └── gcode_generator.py       # G-code 生成器
│   ├── storage/
│   │   └── gcode_storage.py         # SQLite 存储模块
│   ├── web/
│   │   └── api.py                   # FastAPI 应用
│   ├── ai/                          # (预留) AI 模块
│   ├── config_loader.py             # 配置加载器
│   └── cli.py                       # 命令行工具
├── config/                          # 配置文件目录
├── data/                            # 数据文件目录
├── output/                          # 输出目录 (含 programs.db)
├── tests/
│   └── test_api_integration.py      # API 集成测试
├── logs/                            # 日志目录
├── docs/                            # 文档目录
├── requirements.txt                 # Python 依赖
├── pyproject.toml                   # 项目配置
└── docker-compose.yml               # Docker 编排
```

---

## 🚀 快速开始

### 1. 环境准备
```bash
cd /mnt/g/projects/cad-to-gcode
source venv/bin/activate
```

### 2. 安装依赖
```bash
venv/bin/pip install fastapi uvicorn pydantic pyyaml python-multipart requests pytest
```

### 3. 启动 API 服务器
```bash
venv/bin/python -m src.web.api
```

### 4. 访问 Swagger UI
打开浏览器访问：http://localhost:8000/docs

### 5. 运行集成测试
```bash
venv/bin/python tests/test_api_integration.py
```

---

## 📝 API 使用示例

### 生成 G-code 程序
```bash
curl -X POST "http://localhost:8000/gcode/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "start_diameter": 50.0,
    "end_diameter": 30.0,
    "length": 100.0,
    "material": "45#钢",
    "machine_system": "FANUC"
  }'
```

### 查询程序列表
```bash
curl "http://localhost:8000/programs?limit=10&offset=0"
```

### 下载程序文件
```bash
curl -O "http://localhost:8000/programs/1/download"
```

### 获取切削参数
```bash
curl -X POST "http://localhost:8000/cutting-params" \
  -H "Content-Type: application/json" \
  -d '{
    "material": "45#钢",
    "operation": "粗车"
  }'
```

---

## 🎯 下一步建议

### 立即可做 (高优先级)
1. **修复配置文件** - 解决 YAML 语法错误
2. **完善切削规则库** - 添加完整的 cutting_rules.yaml
3. **编写单元测试** - 覆盖核心模块
4. **Docker 测试** - 验证容器化部署

### 短期目标 (1-2 周)
1. **DXF 解析实现** - 完成 2D 轮廓解析
2. **批量处理功能** - 支持多零件生成
3. **Web 界面原型** - 基础前端界面

### 长期目标 (1-3 月)
1. **STEP 文件解析** - 3D 特征提取
2. **AI 工艺规划** - 机器学习模型训练
3. **仿真模块** - 加工路径可视化

---

**文档生成时间**: 2026-04-14 12:40  
**最后更新**: 持久化存储功能完成
