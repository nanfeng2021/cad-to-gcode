# Thread Recognition Test Report

**Date:** 2026-04-14  
**Status:** ✅ THREAD RECOGNITION COMPLETE

---

## Overview

Successfully implemented thread feature recognition from DXF text annotations and G76 threading cycle support.

---

## Implementation Details

### 1. DXF Parser Enhancement (`src/ai/dxf_parser.py`)

**Added TEXT entity support:**
- New `TextEntity` dataclass with fields: text, insert_point, height, rotation, layer
- Updated `ParsedGeometry` to include `texts: List[TextEntity]`
- Added `_extract_text()` method to parse TEXT entities from DXF
- Updated `to_dict()` for JSON serialization

**Code changes:**
```python
@dataclass
class TextEntity:
    """Text entity from DXF (for thread annotations, etc.)."""
    type: str = "text"
    text: str = ""
    insert_point: Point3D = None
    height: float = 0.0
    rotation: float = 0.0
    layer: str = ""
```

---

### 2. Feature Recognition (`src/ai/feature_recognition.py`)

**Added `_recognize_threads()` method:**

**Detection Strategy:**
1. Scan TEXT entities for thread patterns using regex: `M<diameter>x<pitch>`
2. Parse thread specification (major diameter, pitch)
3. Find corresponding cylinder at thread Z location
4. Calculate minor diameter: `minor = major - 1.0825 × pitch`
5. Create thread feature with machining parameters

**Supported Thread Formats:**
- `M30x1.5` - Metric thread with explicit pitch
- `M20` - Metric thread with default pitch (1.5mm)

**Thread Feature Parameters:**
```python
{
    "thread_type": "metric",
    "designation": "M30.0x1.5",
    "major_diameter": 30.0,
    "minor_diameter": 28.376,
    "pitch": 1.5,
    "length": 20.0,
    "start_z": -63.0,
    "end_z": -43.0
}
```

**Coordinate System Handling:**
- Lathe DXF uses XY plane to represent XZ profile
- Text Y coordinate → Z position in machining
- Smart detection: uses Y if Z is ~0

---

### 3. Test File Generator (`scripts/create_test_dxf.py`)

**Added `create_shaft_with_thread()`:**
- Section 1: Ø50mm × 40mm
- Thread relief groove: Ø46mm × 3mm wide
- Thread section: M30x1.5 × 20mm long
- Text annotation positioned at Y=-53 (Z=-53 in machining coords)

---

### 4. Test Pipeline (`scripts/test_pipeline.py`)

**Added thread display:**
```python
elif feat_type == 'thread':
    designation = feat['parameters']['designation']
    major_dia = feat['parameters']['major_diameter']
    pitch = feat['parameters']['pitch']
    length = feat['parameters']['length']
    print(f"  [{feat_id}] 螺纹：{designation} ...")
```

---

## Test Results

### Test File: `shaft_with_thread.dxf`

**Geometry:**
```
Section 1: Ø50mm cylinder, 40mm long (Z=0 to Z=-40)
Groove:    Ø46mm relief groove, 3mm wide (Z=-40 to Z=-43)
Section 2: Ø50mm cylinder, 37mm long (Z=-43 to Z=-43)
Thread:    M30x1.5 on Ø30mm section, 20mm long (Z=-43 to Z=-63)
```

**Recognition Output:**
```
✓ Recognized 5 features
  [cyl_001] 外圆：Ø50.0mm × 40.0mm
  [cyl_002] 外圆：Ø46.0mm × 3.0mm
  [cyl_003] 外圆：Ø30.0mm × 20.0mm
  [groove_004] 切槽：宽 3.0mm × 深 2.0mm @ Z-41.5
  [thread_005] 螺纹：M30.0x1.5 (大径:30.0mm, 螺距:1.5mm, 长:20.0mm) @ Z-63.0→-43.0
```

✅ **All features correctly recognized!**

---

## G76 Threading Cycle Support

The G-code generator already has `generate_thread()` method with FANUC G76 support:

```python
def generate_thread(self, major_diameter, minor_diameter, pitch, thread_length, start_z):
    # FANUC G76 complex threading cycle
    self._add_block(f"G76 P020060 Q100 R0.05", "Threading cycle params")
    self._add_block(f"G76 X{minor_diameter:.3f} Z{start_z - thread_length:.3f} "
                   f"P{int((major_diameter - minor_diameter)/2*1000):04d} "
                   f"Q100 F{pitch:.3f}", f"Thread M{int(major_diameter)}x{pitch}")
```

**G76 Parameters:**
- `P020060`: 2 finish passes, 0 chamfer, 60° thread angle
- `Q100`: Minimum depth of cut (microns)
- `R0.05`: Finish allowance
- `X`: Minor diameter
- `Z`: End position
- `P`: Thread depth (microns, radius value)
- `Q`: First pass depth (microns)
- `F`: Pitch

---

## All Tests Summary

| Test File | Features | Status |
|-----------|----------|--------|
| `simple_shaft.dxf` | 3 Cylinders | ✅ PASS |
| `tapered_shaft.dxf` | 2 Cylinders + 1 Taper | ✅ PASS |
| `shaft_with_groove.dxf` | 4 Cylinders + 1 Groove | ✅ PASS |
| `shaft_with_thread.dxf` | 3 Cylinders + 1 Groove + **1 Thread** | ✅ PASS |

---

## Files Modified

1. `src/ai/dxf_parser.py` - TEXT entity parsing
2. `src/ai/feature_recognition.py` - Thread recognition algorithm
3. `scripts/create_test_dxf.py` - Thread test file generator
4. `scripts/test_pipeline.py` - Thread display support

---

## Next Steps

1. ✅ **Cylinder Recognition** - Complete
2. ✅ **Taper Recognition** - Complete
3. ✅ **Groove Recognition** - Complete
4. ✅ **Thread Recognition** - Complete
5. ⏳ **DWG Format Support** - Research libredwg or ODA File Converter
6. ⏳ **Web UI** - FastAPI upload interface

---

## Technical Notes

### Thread Detection Limitations

1. **Text-based only**: Requires explicit "Mxx" annotation in DXF
2. **No schematic detection**: Doesn't recognize thread symbols without text
3. **Default pitch**: Uses 1.5mm if not specified (may be incorrect for some sizes)

### Future Enhancements

1. **ISO thread table**: Add standard pitch lookup for common metric threads
2. **Schematic detection**: Recognize thread representation lines (dashed)
3. **Internal threads**: Support nut/internal thread features
4. **Multiple standards**: Add UNC/UNF, BSP, NPT support

---

**Conclusion:** Thread feature recognition successfully implemented using text annotation parsing. The system can now identify metric threads from DXF files and prepare them for G76 threading cycle generation.
