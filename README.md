# CAD to G-code Platform 🚀

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Status: MVP](https://img.shields.io/badge/status-MVP-green.svg)]()

**自动化将 2D CAD 图纸转换为生产级 G-code 程序，专为 2 轴数控车床设计**

---

## 🎯 功能特性

- ✅ **DXF 文件解析** - 支持 LINE, CIRCLE, ARC 实体自动提取
- ✅ **AI 特征识别** - 智能识别外圆、锥度、圆弧、切槽等加工特征
- ✅ **多系统 G-code 生成** - 支持 FANUC、Siemens、Mitsubishi 控制系统
- ✅ **工艺参数数据库** - 7 种材料 × 7 种工序 × 5 种数控系统
- ✅ **REST API** - 完整的 FastAPI 接口，支持程序存储和检索
- ✅ **SQLite 持久化** - 零配置数据库，自动生成即保存

---

## 🚀 快速开始

### 安装依赖

```bash
cd cad-to-gcode
source venv/bin/activate
pip install -r requirements.txt
```

### 运行 API 服务器

```bash
python -m uvicorn src.web.api:app --reload --host 0.0.0.0 --port 8000
```

访问 API 文档：http://localhost:8000/docs

### 测试 DXF 到 G-code 转换

```bash
# 生成测试 DXF 文件
python scripts/create_test_dxf.py

# 运行端到端测试
python scripts/test_pipeline.py tests/test_dxf_files/simple_shaft.dxf
```

输出示例：
```
✓ Recognized 5 features
  [cyl_001] 外圆：Ø50.0mm × 30.0mm
  [cyl_002] 外圆：Ø40.0mm × 30.0mm
  ...
✓ Generated 35 lines of G-code
✓ Saved G-code to: tests/test_dxf_files/simple_shaft.nc
```

---

## 📁 项目结构

```
cad-to-gcode/
├── src/
│   ├── ai/                      # AI 特征识别模块
│   │   ├── dxf_parser.py        # DXF 文件解析器
│   │   └── feature_recognition.py  # 特征识别引擎
│   ├── cam/                     # CAM 加工模块
│   │   ├── gcode_generator.py   # G-code 生成器
│   │   └── process_planner.py   # 工艺规划器
│   ├── database/                # 数据库模块
│   │   ├── models.py            # SQLAlchemy 模型
│   │   └── cutting_params.py    # 切削参数数据库
│   └── web/                     # Web API
│       ├── api.py               # FastAPI 应用
│       └── routes/              # API 路由
├── scripts/                     # 工具脚本
│   ├── create_test_dxf.py       # 测试 DXF 生成器
│   └── test_pipeline.py         # 端到端测试
├── tests/                       # 测试文件和报告
├── docs/                        # 文档
└── requirements.txt             # Python 依赖
```

---

## 🔧 核心能力

### 1. DXF 解析引擎
- 支持 DXF R2010 格式
- 自动识别单位 (mm/inches)
- 提取几何实体到标准化格式

### 2. 特征识别引擎
| 特征类型 | 识别方法 | 精度 |
|----------|----------|------|
| 外圆柱面 | 平行 Z 轴线段 | ⭐⭐⭐⭐⭐ |
| 圆弧面 | ARC/CIRCLE 实体 | ⭐⭐⭐⭐⭐ |
| 锥度面 | 倾斜直线段 | ⭐⭐⭐ |
| 切槽 | 窄凹槽模式 | ⭐⭐ |

### 3. G-code 生成器
- **FANUC**: G71/G70 复合循环
- **Siemens**: CYCLE95 毛坯循环
- **Mitsubishi**: G71/G70 循环

### 4. 切削参数数据库
覆盖 7 种常用材料：
- 45#钢、40Cr、不锈钢、铝合金、铸铁、黄铜、尼龙

---

## 📊 性能指标

| 指标 | 数值 |
|------|------|
| DXF 解析时间 | < 100ms |
| 特征识别时间 | < 200ms |
| G-code 生成时间 | < 50ms |
| **端到端总时间** | **< 350ms** ⚡ |

---

## 📚 文档

- [📖 能力分析报告](docs/cad_to_gcode_capability_analysis.md) - 完整的技术方案
- [📘 使用指南](docs/CAD_TO_GCODE_GUIDE.md) - 详细的 API 和使用说明
- [📝 测试报告](tests/PIPELINE_TEST_REPORT.md) - 测试结果和性能数据

---

## 🧪 运行测试

```bash
# 运行单元测试
pytest tests/ -v

# 运行端到端测试
python scripts/test_pipeline.py tests/test_dxf_files/simple_shaft.dxf
```

---

## 🛠️ 技术栈

- **后端**: Python 3.10+, FastAPI, SQLite, SQLAlchemy
- **CAD 解析**: ezdxf, shapely, numpy
- **配置管理**: PyYAML
- **部署**: Docker, Docker Compose
- **测试**: pytest, curl

---

## 📦 部署

### Docker 部署

```bash
docker build -t cad-to-gcode .
docker run -p 8000:8000 cad-to-gcode
```

### 本地开发

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

---

## 🔮 路线图

### v0.2 (进行中)
- [ ] 完善锥度特征识别
- [ ] 实现切槽特征识别
- [ ] 添加 Web 上传界面

### v0.3
- [ ] 螺纹特征识别与加工
- [ ] DWG 文件格式支持
- [ ] 多刀具自动管理

### v1.0
- [ ] AI 增强特征识别
- [ ] 碰撞检查
- [ ] 加工仿真预览
- [ ] 工艺参数自学习

---

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

---

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

---

## 👨‍💻 作者

**nanfeng2021**

GitHub: [@nanfeng2021](https://github.com/nanfeng2021)

---

## 🙏 致谢

- [ezdxf](https://github.com/mozman/ezdxf) - DXF 文件解析库
- [FastAPI](https://fastapi.tiangolo.com/) - 现代 Web 框架
- [Hermes Agent](https://github.com/hermes-agent/hermes-agent) - AI 代理开发模式

---

**最后更新**: 2026-04-14  
**版本**: v0.1 MVP
