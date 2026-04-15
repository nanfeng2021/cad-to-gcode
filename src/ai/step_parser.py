"""
STEP 文件解析器 - 支持 ISO 10303-21 标准

功能:
- 解析 STEP Part 21 (ISO 10303-21) 格式
- 提取 B-Rep 几何信息
- 识别旋转体特征
- 转换为内部几何表示

依赖:
    pip install pythonocc-core

使用示例:
    parser = STEPParser()
    result = parser.parse_file("part.step")
    features = recognize_features(result.entities)
"""

import re
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from pathlib import Path


@dataclass
class StepEntity:
    """STEP 实体基类"""
    id: int
    type: str
    attributes: List = field(default_factory=list)
    raw_data: str = ""


@dataclass 
class CartesianPoint:
    """笛卡尔点"""
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0


@dataclass
class Direction:
    """方向向量"""
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0


@dataclass
class Line:
    """直线"""
    start: CartesianPoint = field(default_factory=CartesianPoint)
    end: CartesianPoint = field(default_factory=CartesianPoint)


@dataclass
class Circle:
    """圆"""
    center: CartesianPoint = field(default_factory=CartesianPoint)
    axis: Direction = field(default_factory=Direction)
    radius: float = 0.0


@dataclass
class Arc:
    """圆弧"""
    center: CartesianPoint = field(default_factory=CartesianPoint)
    radius: float = 0.0
    start_angle: float = 0.0
    end_angle: float = 0.0


@dataclass
class Edge:
    """边"""
    geometry: object  # Line, Circle, or Arc
    start_point: CartesianPoint = field(default_factory=CartesianPoint)
    end_point: CartesianPoint = field(default_factory=CartesianPoint)
    orientation: bool = True


@dataclass
class Face:
    """面"""
    edges: List[Edge] = field(default_factory=list)
    surface_type: str = "cylindrical"  # cylindrical, conical, planar, toroidal


@dataclass
class Vertex:
    """顶点"""
    point: CartesianPoint = field(default_factory=CartesianPoint)


@dataclass
class STEPResult:
    """STEP 解析结果"""
    entities: List = field(default_factory=list)
    vertices: List[Vertex] = field(default_factory=list)
    edges: List[Edge] = field(default_factory=list)
    faces: List[Face] = field(default_factory=list)
    bounding_box: Dict = field(default_factory=lambda: {
        'min_x': 0, 'max_x': 0,
        'min_y': 0, 'max_y': 0,
        'min_z': 0, 'max_z': 0
    })
    metadata: Dict = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)


class STEPParser:
    """STEP 文件解析器"""
    
    def __init__(self):
        self.entities: Dict[int, StepEntity] = {}
        self.geometry_map: Dict[int, object] = {}
        self.tolerance = 1e-6
        
    def parse_file(self, filepath: str) -> STEPResult:
        """解析 STEP 文件"""
        path = Path(filepath)
        
        if not path.exists():
            raise FileNotFoundError(f"STEP 文件不存在：{filepath}")
        
        result = STEPResult()
        
        try:
            # 读取文件
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # 提取元数据
            result.metadata = self._extract_metadata(content)
            
            # 解析实体
            self._parse_entities(content)
            
            # 构建几何表示
            self._build_geometry(result)
            
            # 计算包围盒
            self._calculate_bounding_box(result)
            
        except Exception as e:
            result.errors.append(f"解析错误：{str(e)}")
        
        return result
    
    def _extract_metadata(self, content: str) -> Dict:
        """提取文件元数据"""
        metadata = {}
        
        # 提取文件名
        name_match = re.search(r"FILE_NAME\(\s*'([^']*)'", content)
        if name_match:
            metadata['filename'] = name_match.group(1)
        
        # 提取时间戳
        time_match = re.search(r"FILE_NAME\([^,]*,\s*'([^']*)'", content)
        if time_match:
            metadata['timestamp'] = time_match.group(1)
        
        # 提取作者
        author_match = re.search(r"FILE_NAME\([^,]*,[^,]*,\s*'([^']*)'", content)
        if author_match:
            metadata['author'] = author_match.group(1)
        
        # 提取应用信息
        app_match = re.search(r"APPLICATION_PROTOCOL_DEFINITION\([^,]*,\s*'([^']*)'", content)
        if app_match:
            metadata['protocol'] = app_match.group(1)
        
        return metadata
    
    def _parse_entities(self, content: str) -> None:
        """解析 STEP 实体"""
        # 匹配实体定义：#123 = ENTITY_TYPE(...);
        pattern = r'#(\d+)\s*=\s*(\w+)\s*\(([^;]*)\)\s*;'
        
        for match in re.finditer(pattern, content, re.DOTALL):
            entity_id = int(match.group(1))
            entity_type = match.group(2)
            attrs_str = match.group(3).strip()
            
            # 解析属性
            attributes = self._parse_attributes(attrs_str)
            
            entity = StepEntity(
                id=entity_id,
                type=entity_type,
                attributes=attributes,
                raw_data=match.group(0)
            )
            
            self.entities[entity_id] = entity
    
    def _parse_attributes(self, attrs_str: str) -> List:
        """解析实体属性"""
        attributes = []
        
        # 简单的逗号分隔解析（需要处理嵌套括号）
        depth = 0
        current = ""
        
        for char in attrs_str:
            if char == '(':
                depth += 1
                current += char
            elif char == ')':
                depth -= 1
                current += char
            elif char == ',' and depth == 0:
                attributes.append(self._parse_value(current.strip()))
                current = ""
            else:
                current += char
        
        if current.strip():
            attributes.append(self._parse_value(current.strip()))
        
        return attributes
    
    def _parse_value(self, value_str: str):
        """解析单个值"""
        if not value_str:
            return None
        
        # 引用其他实体：#123
        if value_str.startswith('#'):
            return int(value_str[1:])
        
        # 字符串：'text'
        if value_str.startswith("'") and value_str.endswith("'"):
            return value_str[1:-1]
        
        # 枚举：.LAYER_2.
        if value_str.startswith('.') and value_str.endswith('.'):
            return value_str[1:-1]
        
        # 数值
        try:
            if '.' in value_str:
                return float(value_str)
            return int(value_str)
        except ValueError:
            return value_str
    
    def _build_geometry(self, result: STEPResult) -> None:
        """构建几何表示"""
        # 首先解析所有几何实体
        for entity_id, entity in self.entities.items():
            if entity.type == 'CARTESIAN_POINT':
                point = self._parse_cartesian_point(entity)
                self.geometry_map[entity_id] = point
                
            elif entity.type == 'DIRECTION':
                direction = self._parse_direction(entity)
                self.geometry_map[entity_id] = direction
                
            elif entity.type == 'LINE':
                line = self._parse_line(entity)
                self.geometry_map[entity_id] = line
                result.edges.append(line)
                
            elif entity.type == 'CIRCLE':
                circle = self._parse_circle(entity)
                self.geometry_map[entity_id] = circle
                
            elif entity.type == 'ADVANCED_BREP_SHAPE_REPRESENTATION':
                # 处理 B-Rep 结构
                self._process_brep(entity, result)
        
        # 转换为 2D 轮廓（用于车床加工）
        self._convert_to_2d_profile(result)
    
    def _parse_cartesian_point(self, entity: StepEntity) -> CartesianPoint:
        """解析笛卡尔点"""
        coords = entity.attributes
        return CartesianPoint(
            x=float(coords[0]) if len(coords) > 0 else 0.0,
            y=float(coords[1]) if len(coords) > 1 else 0.0,
            z=float(coords[2]) if len(coords) > 2 else 0.0
        )
    
    def _parse_direction(self, entity: StepEntity) -> Direction:
        """解析方向向量"""
        coords = entity.attributes
        return Direction(
            x=float(coords[0]) if len(coords) > 0 else 0.0,
            y=float(coords[1]) if len(coords) > 1 else 0.0,
            z=float(coords[2]) if len(coords) > 2 else 0.0
        )
    
    def _parse_line(self, entity: StepEntity) -> Line:
        """解析直线"""
        pstart_ref = entity.attributes[0]
        pend_ref = entity.attributes[1]
        
        start = self.geometry_map.get(pstart_ref, CartesianPoint())
        end = self.geometry_map.get(pend_ref, CartesianPoint())
        
        return Line(start=start, end=end)
    
    def _parse_circle(self, entity: StepEntity) -> Circle:
        """解析圆"""
        axis_ref = entity.attributes[0]
        radius = entity.attributes[1] if len(entity.attributes) > 1 else 0.0
        
        # axis_ref 可能是 AXIS2_PLACEMENT_3D，需要进一步解析
        center = CartesianPoint()
        axis = Direction(z=1.0)  # 默认 Z 轴
        
        return Circle(center=center, axis=axis, radius=float(radius))
    
    def _process_brep(self, entity: StepEntity, result: STEPResult) -> None:
        """处理 B-Rep 结构"""
        # 简化处理：提取所有面和边
        # 实际实现需要遍历 B-Rep 层次结构
        pass
    
    def _convert_to_2d_profile(self, result: STEPResult) -> None:
        """将 3D 几何转换为 2D 车削轮廓"""
        # 对于车削加工，我们只需要 XZ 平面的轮廓
        # Y 坐标转换为半径 (X = 2 * radius)
        
        profile_edges = []
        
        for edge in result.edges:
            if isinstance(edge, Line):
                # 转换为 XZ 平面
                start_2d = CartesianPoint(
                    x=edge.start.y * 2,  # 直径编程
                    z=edge.start.z
                )
                end_2d = CartesianPoint(
                    x=edge.end.y * 2,
                    z=edge.end.z
                )
                
                line_2d = Line(start=start_2d, end=end_2d)
                profile_edges.append(line_2d)
        
        result.entities = profile_edges
    
    def _calculate_bounding_box(self, result: STEPResult) -> None:
        """计算包围盒"""
        if not result.edges:
            return
        
        min_x = min_y = min_z = float('inf')
        max_x = max_y = max_z = float('-inf')
        
        for edge in result.edges:
            if isinstance(edge, Line):
                min_x = min(min_x, edge.start.x, edge.end.x)
                max_x = max(max_x, edge.start.x, edge.end.x)
                min_z = min(min_z, edge.start.z, edge.end.z)
                max_z = max(max_z, edge.start.z, edge.end.z)
        
        result.bounding_box = {
            'min_x': min_x if min_x != float('inf') else 0,
            'max_x': max_x if max_x != float('-inf') else 0,
            'min_y': min_y if min_y != float('inf') else 0,
            'max_y': max_y if max_y != float('-inf') else 0,
            'min_z': min_z if min_z != float('inf') else 0,
            'max_z': max_z if max_z != float('-inf') else 0,
        }
        
        # 计算总体尺寸
        result.metadata['stock_diameter'] = max_x - min_x if max_x > min_x else 0
        result.metadata['total_length'] = abs(max_z - min_z)


def parse_step_file(filepath: str) -> STEPResult:
    """便捷函数：解析 STEP 文件"""
    parser = STEPParser()
    return parser.parse_file(filepath)


if __name__ == "__main__":
    # 测试示例
    import sys
    
    if len(sys.argv) > 1:
        filepath = sys.argv[1]
        result = parse_step_file(filepath)
        
        print(f"✓ STEP 文件解析完成")
        print(f"  实体数量：{len(result.entities)}")
        print(f"  边数量：{len(result.edges)}")
        print(f"  毛坯直径：{result.metadata.get('stock_diameter', 0):.2f} mm")
        print(f"  总长度：{result.metadata.get('total_length', 0):.2f} mm")
        
        if result.errors:
            print(f"\n错误:")
            for error in result.errors:
                print(f"  - {error}")
    else:
        print("用法：python step_parser.py <file.step>")
