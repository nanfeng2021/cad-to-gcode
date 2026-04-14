# CAD to G-code 自动化功能使用指南

## 🎯 功能概述

本模块实现了从 **2D CAD 图纸 (DXF)** 到 **生产级 G-code** 的自动化转换流程：

```
用户上传 DXF → 自动解析几何 → 识别加工特征 → 生成 FANUC G-code
```

---

## 📦 依赖安装

```bash
cd /mnt/g/projects/cad-to-gcode
source venv/bin/activate

# 安装 CAD 解析依赖
venv/bin/python -m pip install ezdxf shapely numpy
```

---

## 🚀 快速开始

### 方法 1: 使用测试脚本验证功能

```bash
# 运行端到端测试
venv/bin/python scripts/test_pipeline.py tests/test_dxf_files/simple_shaft.dxf
```

输出示例:
```
======================================================================
Testing: tests/test_dxf_files/simple_shaft.dxf
======================================================================

[Step 1/3] Parsing DXF file...
✓ Parsed successfully
  Format: DXF
  Version: AC1024
  Units: mm
  Entities:
    - Lines: 6
    - Circles: 3
    - Arcs: 2
    - Polylines: 0

[Step 2/3] Recognizing machining features...
✓ Recognized 5 features
  [cyl_001] 外圆：Ø50.0mm × 30.0mm
  [cyl_002] 外圆：Ø40.0mm × 30.0mm
  [cyl_003] 外圆：Ø30.0mm × 40.0mm
  [arc_004] 圆弧面：R2.0mm (90.0°)
  [arc_005] 圆弧面：R2.0mm (90.0°)

[Step 3/3] Generating G-code program...
✓ Generated 35 lines of G-code

✓ Saved G-code to: tests/test_dxf_files/simple_shaft.nc

======================================================================
✓ Pipeline test PASSED
======================================================================
```

---

### 方法 2: 在 Python 代码中使用

#### 步骤 1: 解析 DXF 文件

```python
from src.ai.dxf_parser import parse_dxf, DXFParser

# 解析 DXF 文件
geometry_dict = parse_dxf("path/to/your/part.dxf")

# 查看解析结果
print(f"文件格式：{geometry_dict['metadata']['format']}")
print(f"单位：{geometry_dict['metadata']['units']}")
print(f"线段数量：{geometry_dict['summary']['line_count']}")
print(f"圆弧数量：{geometry_dict['summary']['arc_count']}")
```

#### 步骤 2: 识别加工特征

```python
from src.ai.dxf_parser import DXFParser
from src.ai.feature_recognition import recognize_features

# 解析 DXF 获取几何对象
parser = DXFParser()
geometry = parser.parse_file("path/to/your/part.dxf")

# 识别特征
feature_tree = recognize_features(geometry)

# 查看识别结果
print(f"识别到 {feature_tree['feature_count']} 个特征:")
for feat in feature_tree['features']:
    print(f"  - {feat['id']}: {feat['type']}")
    if feat['type'] == 'external_cylinder':
        dia = feat['parameters']['diameter']
        length = feat['parameters']['length']
        print(f"    直径：Ø{dia}mm, 长度：{length}mm")
```

#### 步骤 3: 生成 G-code

```python
from src.cam.gcode_generator import GCodeGenerator

# 创建生成器
generator = GCodeGenerator(machine_system="FANUC")

# 生成程序头
generator.generate_header("O0001", "MyPart")

# 生成加工代码
# ... (根据特征生成具体代码)

# 生成程序尾
generator.generate_footer()

# 获取 G-code 字符串
gcode = generator.generate()

# 保存到文件
with open("output.nc", "w") as f:
    f.write(gcode)
```

---

### 方法 3: 通过 API 调用 (需启动服务器)

```bash
# 启动 API 服务器
cd /mnt/g/projects/cad-to-gcode
venv/bin/python -m uvicorn src.web.api:app --reload

# 使用 curl 上传 DXF 并获取 G-code
curl -X POST http://localhost:8000/upload-dxf \
  -F "file=@tests/test_dxf_files/simple_shaft.dxf" \
  -o output.nc
```

*注意：文件上传端点待实现*

---

## 📁 支持的 DXF 格式

### 实体类型
- ✅ LINE (线段)
- ✅ CIRCLE (圆)
- ✅ ARC (圆弧)
- ⏳ POLYLINE/LWPOLYLINE (多段线 - 部分支持)
- ❌ SPLINE (样条曲线 - 未来)

### 坐标系统
- **车床坐标系**: X (直径), Z (长度)
- **绘图约定**: DXF 文件应在 XZ 平面绘制
- **对称假设**: 默认提取上半部分轮廓 (Y > 0 或 X > 0)

### 单位支持
- ✅ 毫米 (mm) - 默认
- ✅ 英寸 (inches)
- ✅ 厘米 (cm)
- ✅ 米 (meters)

---

## 🔧 特征识别能力

### 已支持的特征

| 特征类型 | 识别方法 | 精度 |
|----------|----------|------|
| 外圆柱面 | 平行于 Z 轴的直线 | ⭐⭐⭐⭐⭐ |
| 圆弧面 | ARC/CIRCLE 实体 | ⭐⭐⭐⭐⭐ |
| 锥度面 | 倾斜直线段 | ⭐⭐⭐ (需优化) |
| 切槽 | 窄凹槽模式 | ⭐⭐ (待完善) |

### 特征参数输出

每个识别到的特征包含:
- **ID**: 唯一标识符 (如 `cyl_001`)
- **类型**: 特征类型
- **优先级**: 加工顺序 (1=最先)
- **参数**: 直径、长度、锥度等
- **加工区域**: 起点/终点坐标
- **原始几何**: 对应的 DXF 实体数据

---

## 📊 生成的 G-code 特性

### 支持的控制系统的
- ✅ FANUC (主要支持)
- ⏳ Siemens (待测试)
- ⏳ Mitsubishi (待测试)

### 加工工序
- ✅ 端面加工
- ✅ 粗车外圆 (G71 复合循环)
- ✅ 精车外圆 (G70 循环)
- ❌ 切槽 (待实现)
- ❌ 螺纹 (待实现)

### 程序结构
```gcode
O9999                    ; 程序号
(DATE=2026-04-14)        ; 日期
(MACHINE=FANUC)          ; 控制系统

G21                      ; 公制单位
G40 G97 G99              ; 取消补偿，恒转速，每转进给

T0101 M06                ; 换 1 号刀 (端面刀)
S800 M03                 ; 主轴正转 800 RPM
G00 X55 Z0 M08           ; 快速定位，开冷却

G01 X-2 F0.2             ; 车端面

T0202 M06                ; 换 2 号刀 (粗车刀)
G71 U2.0 R0.5            ; 粗车循环，切深 2mm
G71 P10 Q20 U0.5 W0.2 F0.3  ; 留 0.5mm 精加工余量
N10 G00 X0               ; 轮廓开始
N15 G01 X50.0 Z-40.0     ; 车削轮廓
N20 G01 X55              ; 轮廓结束

T0303 M06                ; 换 3 号刀 (精车刀)
S1200 M03                ; 提高转速
G70 P10 Q20 F0.1         ; 精车循环

M05                      ; 主轴停
M09                      ; 冷却关
G28 U0 W0                ; 回参考点
M30                      ; 程序结束
```

---

## 🧪 测试用例

### 生成测试 DXF 文件

```bash
venv/bin/python scripts/create_test_dxf.py
```

这将生成 3 个测试文件:
1. `simple_shaft.dxf` - 简单阶梯轴
2. `tapered_shaft.dxf` - 锥度轴
3. `shaft_with_groove.dxf` - 带切槽轴

### 运行完整测试

```bash
venv/bin/python scripts/test_pipeline.py tests/test_dxf_files/simple_shaft.dxf
```

查看测试报告: `tests/PIPELINE_TEST_REPORT.md`

---

## ⚠️ 注意事项

### DXF 文件要求
1. **坐标系**: 零件轮廓应在 XZ 平面绘制
2. **对称性**: 只需绘制上半部分 (或明确指定)
3. **连续性**: 轮廓线段应首尾相连 (允许 0.001mm 公差)
4. **图层**: 建议将轮廓线放在独立图层

### 加工限制
- **最大直径**: 受机床规格限制 (代码中无硬性限制)
- **最小特征**: 识别公差 0.001mm
- **材料**: 需在工艺规划中指定 (默认 45#钢)

### 安全提示
⚠️ **生成的 G-code 必须经过人工验证后才能上机使用!**

- 检查尺寸是否正确
- 确认切削参数合理
- 验证刀具选择适当
- 进行仿真或空运行

---

## 🛠️ 故障排除

### 问题 1: "No module named 'ezdxf'"
**解决**:
```bash
venv/bin/python -m pip install ezdxf
```

### 问题 2: "DXF file not found"
**解决**: 使用绝对路径或确保文件存在
```python
from pathlib import Path
assert Path("your_file.dxf").exists()
```

### 问题 3: 特征识别结果为空
**可能原因**:
- DXF 文件为空或只有标注
- 轮廓线不在 XZ 平面
- 线段不连续

**解决**:
1. 用 CAD 软件检查文件
2. 确保轮廓线是 LINE/ARC 实体
3. 运行 `parse_dxf()` 查看解析结果

### 问题 4: 生成的 G-code 无法运行
**检查**:
1. 机床控制系统是否匹配 (FANUC/Siemens/Mitsubishi)
2. 刀具号是否与机床刀库一致
3. 工件坐标系设置 (G54)
4. 安全高度是否足够

---

## 📚 API 参考

### DXFParser 类

```python
class DXFParser:
    def parse_file(filepath: str) -> ParsedGeometry:
        """解析 DXF 文件"""
```

### FeatureRecognizer 类

```python
class FeatureRecognizer:
    def __init__(tolerance: float = 0.001):
        """初始化识别器"""
    
    def recognize(geometry: ParsedGeometry) -> FeatureTree:
        """识别加工特征"""
```

### GCodeGenerator 类

```python
class GCodeGenerator:
    def __init__(machine_system: str = "FANUC"):
        """初始化生成器"""
    
    def generate_header(program_name: str, part_name: str):
        """生成程序头"""
    
    def generate_footer():
        """生成程序尾"""
    
    def setup_tool(tool_number: int, spindle_speed: int):
        """设置刀具和主轴"""
    
    def generate_rough_turning_cycle_fanuc(...):
        """生成 G71 粗车循环"""
    
    def generate_finish_pass(...):
        """生成精车走刀"""
    
    def generate() -> str:
        """输出完整 G-code"""
```

---

## 📝 开发日志

- **2026-04-14**: MVP 发布
  - ✅ DXF 解析器完成
  - ✅ 特征识别引擎完成
  - ✅ G-code 生成器集成
  - ✅ 端到端测试通过

---

## 🔮 未来计划

- [ ] DWG 文件支持
- [ ] 螺纹特征识别
- [ ] 公差/粗糙度处理
- [ ] Web 上传界面
- [ ] AI 增强特征识别
- [ ] 碰撞检查
- [ ] 加工仿真

---

**文档版本**: v0.1  
**更新日期**: 2026-04-14  
**项目**: CAD to G-code Platform
