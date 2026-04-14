# 模具零部件二轴 CAD → G-code 能力分析报告

**分析日期**: 2026-04-14  
**目标**: 用户上传一张 2D CAD 图纸 → 系统自动输出可直接上机生产的 G-code 程序

---

## 🎯 完整工作流程拆解

```
用户输入                系统处理流程                          最终输出
┌─────────────┐      ┌─────────────────────────────────┐    ┌──────────────┐
│ 2D CAD 图纸  │ ──→  │ 1. 文件解析                      │    │              │
│ (.dxf/.dwg) │      │    - 读取几何实体                │    │              │
│             │      │    - 提取坐标数据                │    │              │
│             │      │    - 识别图层/线型               │    │              │
│             │      └──────────────┬──────────────────┘    │              │
│             │                     ↓                        │              │
│             │      ┌─────────────────────────────────┐    │              │
│             │      │ 2. 特征识别 (AI/规则)            │    │              │
│             │      │    - 圆柱/圆锥/圆弧/螺纹/切槽   │    │              │
│             │      │    - 提取尺寸参数                │    │              │
│             │      │    - 构建工艺特征树              │    │              │
│             │      └──────────────┬──────────────────┘    │              │
│             │                     ↓                        │              │
│             │      ┌─────────────────────────────────┐    │              │
│             │      │ 3. 工艺规划                      │    │              │
│             │      │    - 工序排序 (粗→精→螺纹...)    │    │              │
│             │      │    - 刀具选择                    │    │              │
│             │      │    - 切削参数计算                │    │              │
│             │      │    - 装夹方案                    │    │              │
│             │      └──────────────┬──────────────────┘    │              │
│             │                     ↓                        │              │
│             │      ┌─────────────────────────────────┐    │              │
│             │      │ 4. G-code 生成                   │    │ 生产级       │
│             │      │    - 按工序生成代码段            │    │ G-code 程序  │
│             │      │    - 插入换刀/冷却/安全代码      │───→│ (.nc 文件)   │
│             │      │    - 优化空行程                  │    │              │
│             │      │    - 添加注释/程序头尾           │    │              │
│             │      └─────────────────────────────────┘    │              │
└─────────────┘                                            └──────────────┘
```

---

## 🔍 核心能力需求分析

### 能力一：CAD 文件解析引擎 ⭐⭐⭐⭐⭐

#### 当前状态
- ❌ **完全缺失** - 仅支持上传但无解析逻辑

#### 需要实现
| 子能力 | 技术选型 | 工作量 |
|--------|----------|--------|
| DXF 文件解析 | `ezdxf` (Python) | 2-3 天 |
| DWG 文件解析 | `libredwg` + Python 绑定 / ODA File Converter | 3-5 天 |
| 几何实体提取 | LINE, CIRCLE, ARC, POLYLINE, SPLINE | 2 天 |
| 图层/块解析 | LAYER, BLOCK, INSERT | 1 天 |
| 尺寸标注识别 | DIMENSION, TOLERANCE | 3-5 天 |
| 坐标系统一 | WCS → MCS 转换 | 1 天 |

#### 关键技术点
```python
# 示例：使用 ezdxf 解析 DXF
import ezdxf

doc = ezdxf.readfile("part.dxf")
msp = doc.modelspace()

# 提取所有几何实体
entities = {
    'lines': [],
    'circles': [],
    'arcs': [],
    'polylines': []
}

for entity in msp:
    if entity.dxftype() == 'LINE':
        entities['lines'].append({
            'start': entity.dxf.start,  # (x, y, z)
            'end': entity.dxf.end,
            'layer': entity.dxf.layer
        })
    elif entity.dxftype() == 'CIRCLE':
        entities['circles'].append({
            'center': entity.dxf.center,
            'radius': entity.dxf.radius
        })
    # ... 其他实体类型
```

#### 输出数据结构
```json
{
  "file_info": {
    "format": "DXF",
    "version": "AC1015",
    "units": "mm"
  },
  "geometry": {
    "profiles": [
      {
        "id": "profile_1",
        "layer": "轮廓线",
        "entities": [
          {"type": "line", "start": [0, 0], "end": [50, 0]},
          {"type": "arc", "center": [50, 25], "radius": 25, "start_angle": 270, "end_angle": 90},
          {"type": "line", "start": [50, 50], "end": [0, 50]}
        ]
      }
    ],
    "dimensions": [
      {"type": "linear", "value": 50.0, "unit": "mm", "location": ...},
      {"type": "radius", "value": 25.0, "unit": "mm", "location": ...}
    ]
  }
}
```

---

### 能力二：几何特征识别 ⭐⭐⭐⭐⭐

#### 当前状态
- ❌ **完全缺失** - 无特征识别逻辑

#### 需要实现
| 特征类型 | 识别方法 | 难度 |
|----------|----------|------|
| 外圆柱面 | 平行于 Z 轴的直线段 | ⭐ |
| 圆锥面 | 倾斜直线段 (计算锥度) | ⭐⭐ |
| 圆弧面 | ARC/CIRCLE 实体 | ⭐⭐ |
| 退刀槽 | 窄而深的凹槽轮廓 | ⭐⭐⭐ |
| 螺纹 | 特定线型 + 标注识别 | ⭐⭐⭐⭐ |
| 倒角/倒圆 | 短斜线/小圆弧 | ⭐⭐ |
| 中心孔 | 小直径圆 + 中心线 | ⭐⭐⭐ |

#### 技术方案

**方案 A: 规则引擎 (推荐起步)**
```python
class FeatureRecognizer:
    def recognize_external_profile(self, entities):
        """识别外轮廓特征"""
        features = []
        
        # 1. 找到最外侧轮廓 (最大 X 坐标的连续实体)
        outer_chain = self._find_outermost_chain(entities)
        
        # 2. 分段识别
        for entity in outer_chain:
            if entity.type == 'line':
                if self._is_parallel_to_z(entity):
                    features.append({
                        'type': 'cylinder',
                        'diameter': entity.start.x * 2,
                        'length': abs(entity.end.z - entity.start.z),
                        'start_z': entity.start.z
                    })
                elif self._is_inclined(entity):
                    taper = self._calculate_taper(entity)
                    features.append({
                        'type': 'taper',
                        'start_diameter': entity.start.x * 2,
                        'end_diameter': entity.end.x * 2,
                        'length': abs(entity.end.z - entity.start.z),
                        'taper_ratio': taper
                    })
            elif entity.type == 'arc':
                features.append({
                    'type': 'arc_surface',
                    'radius': entity.radius,
                    'center': entity.center,
                    'sweep_angle': entity.sweep_angle
                })
        
        return features
```

**方案 B: AI 模型 (长期目标)**
- 训练 CNN/Transformer 识别 2D 轮廓特征
- 需要大量标注数据 (CAD 图纸 → 特征标签)
- 工作量：2-3 月 (数据收集 + 训练 + 部署)

#### 输出数据结构
```json
{
  "features": [
    {
      "id": "feat_001",
      "type": "external_cylinder",
      "priority": 1,
      "parameters": {
        "diameter": 50.0,
        "length": 30.0,
        "tolerance": "+0/-0.025",
        "surface_roughness": "Ra1.6"
      },
      "machining_area": {
        "start_z": 0,
        "end_z": -30,
        "start_x": 25,
        "end_x": 25
      }
    },
    {
      "id": "feat_002",
      "type": "groove",
      "priority": 3,
      "parameters": {
        "width": 3.0,
        "depth": 2.0,
        "position_z": -35
      }
    },
    {
      "id": "feat_003",
      "type": "thread",
      "priority": 4,
      "parameters": {
        "type": "metric",
        "nominal_diameter": 24,
        "pitch": 2.0,
        "length": 20,
        "class": "6g"
      }
    }
  ],
  "feature_tree": {
    "setup": "one_setup",
    "sequence": ["feat_001", "feat_002", "feat_003"]
  }
}
```

---

### 能力三：工艺规划引擎增强 ⭐⭐⭐⭐⭐

#### 当前状态
- ✅ **基础可用** - 有切削参数计算
- ❌ **缺少自动工序排序** - 需手动指定操作

#### 需要实现
| 功能 | 描述 | 工作量 |
|------|------|--------|
| 工序自动排序 | 根据特征类型和优先级生成加工顺序 | 3-5 天 |
| 刀具自动选择 | 基于特征尺寸、材料、精度选择刀具 | 3-5 天 |
| 余量分配 | 粗加工余量、半精加工余量、精加工余量 | 2 天 |
| 走刀路径规划 | 计算每刀的起点、终点、切深 | 3-5 天 |
| 装夹方案建议 | 卡盘/顶尖/心轴选择 | 2-3 天 |

#### 工艺规则库示例
```yaml
# cutting_rules_enhanced.yaml

feature_rules:
  external_cylinder:
    sequence_priority: 1
    operations:
      - name: "粗车"
        allowance_left: 0.5  # 留 0.5mm 精加工余量
        max_depth_of_cut: 2.5
        tool_selection:
          min_insert_size: 12mm
          nose_radius: 0.8mm
      - name: "精车"
        allowance_left: 0
        depth_of_cut: 0.2-0.5
        tool_selection:
          min_insert_size: 8mm
          nose_radius: 0.4mm
  
  groove:
    sequence_priority: 3
    operations:
      - name: "切槽"
        tool_selection:
          type: "grooving_tool"
          width: "match_groove_width"
        strategy: "multiple_passes"  # 宽槽多刀
  
  thread:
    sequence_priority: 4
    operations:
      - name: "车螺纹"
        tool_selection:
          type: "threading_insert"
          angle: 60  # 公制螺纹
        passes: "calculated_by_pitch"

material_overrides:
  "不锈钢":
    spindle_speed_factor: 0.6
    feed_rate_factor: 0.8
  "铝合金":
    spindle_speed_factor: 1.5
    feed_rate_factor: 1.2
```

#### 输出数据结构
```json
{
  "process_plan": {
    "part_id": "part_001",
    "material": "45#钢",
    "blank_size": {"diameter": 55, "length": 105},
    "setup": [
      {
        "setup_id": 1,
        "description": "夹持左端，加工右端",
        "chucking_method": "three_jaw_chuck",
        "operations": [
          {
            "op_id": 10,
            "feature_id": "feat_001",
            "operation": "粗车外圆",
            "tool": {
              "tool_id": "T01",
              "name": "外圆粗车刀",
              "insert": "CNMG120408",
              "nose_radius": 0.8
            },
            "cutting_params": {
              "spindle_speed": 800,
              "feed_rate": 0.3,
              "depth_of_cut": 2.0,
              "passes": [
                {"pass": 1, "start_dia": 55, "end_dia": 51},
                {"pass": 2, "start_dia": 51, "end_dia": 47},
                {"pass": 3, "start_dia": 47, "end_dia": 43},
                {"pass": 4, "start_dia": 43, "end_dia": 40.5}
              ]
            }
          },
          {
            "op_id": 20,
            "feature_id": "feat_001",
            "operation": "精车外圆",
            "tool": {
              "tool_id": "T02",
              "name": "外圆精车刀",
              "insert": "VNMG160404",
              "nose_radius": 0.4
            },
            "cutting_params": {
              "spindle_speed": 1200,
              "feed_rate": 0.15,
              "depth_of_cut": 0.5,
              "passes": [
                {"pass": 1, "start_dia": 40.5, "end_dia": 40.0}
              ]
            }
          }
        ]
      }
    ]
  }
}
```

---

### 能力四：智能 G-code 生成器 ⭐⭐⭐⭐

#### 当前状态
- ✅ **基础可用** - 可生成简单轴类程序
- ❌ **缺少复杂循环** - 需支持多特征、多刀具

#### 需要实现
| 功能 | 描述 | 工作量 |
|------|------|--------|
| 多刀具管理 | 自动插入换刀代码、刀补设置 | 2 天 |
| 复合循环 | G71/G72/G73 多段轮廓粗车 | 3 天 |
| 螺纹循环 | G76 多行螺纹切削 | 2 天 |
| 宏程序支持 | 用户自定义宏、参数化编程 | 3-5 天 |
| 空行程优化 | 快速定位路径优化 | 2 天 |
| 碰撞检查 | 简单的干涉检查 | 3 天 |

#### 生成逻辑示例
```python
class IntelligentGCodeGenerator:
    def generate_from_process_plan(self, process_plan):
        """根据工艺计划生成完整 G-code"""
        program = []
        
        # 1. 程序头
        program.extend(self.generate_header(process_plan.part_id))
        
        # 2. 按工序生成代码
        for setup in process_plan.setup:
            program.extend(self.generate_setup_start(setup))
            
            for op in setup.operations:
                # 换刀
                if op.tool != self.current_tool:
                    program.extend(self.generate_tool_change(op.tool))
                
                # 生成该工序的 G-code
                if op.operation == "粗车":
                    program.extend(self.generate_roughing_cycle(op))
                elif op.operation == "精车":
                    program.extend(self.generate_finishing_cycle(op))
                elif op.operation == "切槽":
                    program.extend(self.generate_grooving_cycle(op))
                elif op.operation == "车螺纹":
                    program.extend(self.generate_threading_cycle(op))
            
            program.extend(self.generate_setup_end(setup))
        
        # 3. 程序结束
        program.extend(self.generate_program_end())
        
        return "\n".join(program)
    
    def generate_roughing_cycle(self, op):
        """生成 G71 粗车循环"""
        code = []
        code.append(f"; --- 工序 {op.op_id}: 粗车外圆 ---")
        code.append(f"T{op.tool.tool_id} M06  ; 换 {op.tool.name}")
        code.append(f"G00 X{op.cut_start_x} Z{op.cut_start_z} M08")
        code.append(f"S{op.spindle_speed} M03")
        
        # G71 格式 (FANUC)
        code.append(f"G71 U{op.depth_of_cut} R0.5")
        code.append(f"G71 P{op.start_seq} Q{op.end_seq} U0.5 W0.2 F{op.feed_rate}")
        
        # 轮廓定义 (由特征识别结果生成)
        code.append(f"N{op.start_seq} G00 X{op.profile[0].start_x}")
        for i, segment in enumerate(op.profile):
            if segment.type == 'line':
                code.append(f"G01 X{segment.end_x} Z{segment.end_z}")
            elif segment.type == 'arc':
                direction = "G02" if segment.clockwise else "G03"
                code.append(f"{direction} X{segment.end_x} Z{segment.end_z} R{segment.radius}")
        code.append(f"N{op.end_seq} G01 X{op.finish_diameter}")
        
        return code
```

---

### 能力五：公差与表面粗糙度处理 ⭐⭐⭐

#### 当前状态
- ❌ **完全缺失**

#### 需要实现
| 功能 | 描述 | 工作量 |
|------|------|--------|
| 公差识别 | 从 CAD 标注提取公差带 | 2-3 天 |
| 精度分级 | 根据公差确定加工等级 | 1 天 |
| 余量调整 | 高精度特征增加精加工余量 | 1 天 |
| 粗糙度要求 | 从标注提取 Ra/Rz 要求 | 2 天 |
| 参数优化 | 根据粗糙度调整进给/转速 | 2 天 |

#### 关键规则
```python
# 公差与加工策略映射
tolerance_strategy = {
    "IT11-IT12": {"rough_only": True, "finish_allowance": 0},
    "IT8-IT10": {"rough_finish": True, "finish_allowance": 0.3, "finish_feed": 0.15},
    "IT6-IT7": {"rough_semi_finish": True, "finish_allowance": 0.15, "finish_feed": 0.08},
    "IT5+": {"grinding_required": True}  # 需磨削，超出车削范围
}

# 表面粗糙度与进给率关系
roughness_feed_map = {
    "Ra6.3": {"max_feed": 0.4, "nose_radius": 0.8},
    "Ra3.2": {"max_feed": 0.25, "nose_radius": 0.8},
    "Ra1.6": {"max_feed": 0.15, "nose_radius": 0.4},
    "Ra0.8": {"max_feed": 0.08, "nose_radius": 0.2, "high_speed": True}
}
```

---

### 能力六：人工交互与确认界面 ⭐⭐⭐

#### 当前状态
- ❌ **完全缺失**

#### 需要实现
| 功能 | 描述 | 工作量 |
|------|------|--------|
| 特征预览 | 可视化显示识别出的特征 | 3-5 天 |
| 工艺确认 | 让用户确认/修改工序顺序 | 2-3 天 |
| 参数调整 | 允许手动调整切削参数 | 1-2 天 |
| 代码预览 | 高亮显示生成的 G-code | 1 天 |
| 导出选项 | 选择机床系统、后处理 | 1 天 |

---

## 📊 开发工作量估算

### 阶段一：MVP (最小可行产品) - 4-6 周
| 模块 | 工作量 | 优先级 |
|------|--------|--------|
| DXF 解析引擎 | 5 天 | ⭐⭐⭐⭐⭐ |
| 基础特征识别 (圆柱/圆锥/圆弧) | 7 天 | ⭐⭐⭐⭐⭐ |
| 规则引擎工艺规划 | 7 天 | ⭐⭐⭐⭐⭐ |
| G-code 生成器增强 | 7 天 | ⭐⭐⭐⭐⭐ |
| API 端点扩展 | 3 天 | ⭐⭐⭐⭐ |
| **合计** | **29 天** | |

**MVP 能力范围**:
- ✅ 支持 DXF 格式
- ✅ 识别简单轴类零件 (外圆 + 锥度 + 圆弧)
- ✅ 自动生成粗车 + 精车工序
- ✅ 输出 FANUC 格式 G-code
- ❌ 不支持螺纹/切槽自动识别
- ❌ 不支持公差/粗糙度处理

### 阶段二：生产就绪 - 6-8 周
| 模块 | 工作量 | 优先级 |
|------|--------|--------|
| DWG 文件支持 | 5 天 | ⭐⭐⭐⭐ |
| 螺纹/切槽特征识别 | 7 天 | ⭐⭐⭐⭐ |
| 公差/粗糙度处理 | 5 天 | ⭐⭐⭐ |
| 多刀具管理 | 5 天 | ⭐⭐⭐⭐ |
| 工艺规则库完善 | 7 天 | ⭐⭐⭐⭐ |
| Web 界面原型 | 10 天 | ⭐⭐⭐ |
| **合计** | **39 天** | |

### 阶段三：高级功能 - 8-12 周
| 模块 | 工作量 | 优先级 |
|------|--------|--------|
| AI 特征识别模型 | 30 天 | ⭐⭐ |
| 宏程序支持 | 7 天 | ⭐⭐ |
| 碰撞检查 | 7 天 | ⭐⭐⭐ |
| 批量处理 | 5 天 | ⭐⭐ |
| 仿真预览 | 15 天 | ⭐⭐ |
| **合计** | **64 天** | |

---

## 🛠️ 技术栈推荐

### CAD 解析
```toml
[dependencies]
ezdxf = ">=1.1.0"        # DXF 解析 (纯 Python，活跃维护)
cad-to-blender = "*"     # 可选：DWG 转换
pythonocc-core = ">=7.7" # STEP/IGES 解析 (OCCT 绑定)
```

### 几何计算
```toml
shapely = ">=2.0"        # 2D 几何运算
numpy = ">=1.24"         # 数值计算
scipy = ">=1.10"         # 曲线拟合、优化
```

### AI/ML (可选)
```toml
torch = ">=2.0"          # 深度学习框架
transformers = ">=4.30"  # 预训练模型
opencv-python = ">=4.8"  # 图像处理
```

### Web 界面
```toml
# 后端 (已有)
fastapi = ">=0.104"
uvicorn = ">=0.24"

# 前端 (新增)
# 方案 A: 轻量级
htmx = "*" + Alpine.js    # 无需复杂前端框架

# 方案 B: 现代化
react + vite             # 完整前端生态
three.js                 # 3D 可视化
```

---

## 🎯 推荐实施路线

### 第一周：DXF 解析 PoC
```bash
# 目标：能读取 DXF 并提取基本几何实体
1. 安装 ezdxf
2. 编写解析脚本
3. 测试标准 DXF 文件
4. 输出 JSON 格式几何数据
```

### 第二 - 三周：特征识别引擎
```bash
# 目标：从几何实体识别出圆柱/圆锥/圆弧
1. 实现轮廓链提取算法
2. 实现特征分类规则
3. 单元测试覆盖常见零件
4. 输出特征树 JSON
```

### 第四 - 五周：工艺规划集成
```bash
# 目标：特征 → 工序 → 刀具 → 参数
1. 扩展现有 cutting_rules.yaml
2. 实现工序排序算法
3. 实现刀具选择逻辑
4. 集成到现有 API
```

### 第六周：G-code 生成器升级
```bash
# 目标：支持多特征、多刀具程序
1. 实现 G71/G70 多段轮廓
2. 实现换刀逻辑
3. 优化空行程
4. 端到端测试
```

### 第七周：Web 界面 MVP
```bash
# 目标：用户上传 DXF → 下载 NC
1. 文件上传端点
2. 特征预览页面
3. 参数确认页面
4. G-code 预览/下载
```

---

## ⚠️ 风险与挑战

### 技术风险
| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|----------|
| DWG 解析困难 | 高 | 高 | 优先支持 DXF，DWG 用转换器 |
| 特征识别准确率低 | 中 | 高 | 提供人工确认界面 |
| 复杂零件无法处理 | 中 | 中 | 明确 MVP 范围 (简单轴类) |
| 生成代码不可用 | 低 | 高 | 邀请机械工程师参与测试 |

### 数据风险
- ❌ **缺乏训练数据** (如果用 AI 方案)
  - 解决：先用规则引擎，积累数据后再训练模型

### 业务风险
- ⚠️ **责任问题** - 生成的 G-code 导致撞机/废品
  - 解决：添加免责声明，要求人工确认

---

## 📝 结论与建议

### 立即可开始的工作
1. **本周**: 安装 `ezdxf`，编写 DXF 解析 PoC
2. **下周**: 实现基础特征识别 (圆柱/圆锥)
3. **第三周**: 集成到现有 API，端到端测试

### MVP 范围建议
**聚焦简单轴类零件**:
- ✅ 外圆柱面
- ✅ 圆锥面
- ✅ 圆弧面
- ✅ 简单倒角
- ❌ 暂不支持：螺纹、切槽、偏心、异形

**预期效果**:
- 用户上传 DXF → 10 秒内生成可运行的 G-code
- 准确率 > 90% (针对简单轴类)
- 仍需人工确认，但大幅减少编程时间

### 长期愿景
- AI 驱动的特征识别 (支持复杂零件)
- 自适应工艺优化 (学习历史数据)
- 云端仿真验证
- 对接 MES/ERP 系统

---

**下一步行动**: 
你想从哪个模块开始？我建议先从 **DXF 解析 PoC** 开始，这是整个流程的入口，技术风险最低，能快速验证可行性。
