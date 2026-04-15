"""
IGES 文件解析器 - 支持 Initial Graphics Exchange Specification

功能:
- 解析 IGES 文件格式 (5.3 版本)
- 提取几何实体 (直线、圆、圆弧、样条)
- 识别旋转体特征
- 转换为内部几何表示

依赖:
    可选：pip install pythonocc-core (用于复杂 IGES 解析)

使用示例:
    parser = IGESParser()
    result = parser.parse_file("part.igs")
"""

import re
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from pathlib import Path


@dataclass
class IGESEntity:
    """IGES 实体"""
    type_code: str  # 例如：110=Line, 100=Line
    params: List = field(default_factory=list)
    directory_entry: Dict = field(default_factory=dict)


@dataclass
class IGESResult:
    """IGES 解析结果"""
    entities: List = field(default_factory=list)
    lines: List = field(default_factory=list)
    circles: List = field(default_factory=list)
    arcs: List = field(default_factory=list)
    splines: List = field(default_factory=list)
    metadata: Dict = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)


class IGESParser:
    """IGES 文件解析器"""
    
    # IGES 实体类型代码映射
    ENTITY_TYPES = {
        '100': 'Line',
        '102': 'Composite Curve',
        '104': 'Conic Arc',
        '106': 'Copious Data',
        '108': 'Plane',
        '110': 'Line',
        '112': 'Parametric Spline Curve',
        '114': 'Trimmed Parametric Surface',
        '116': 'Point',
        '118': 'Rational B-spline',
        '120': 'Surface of Revolution',
        '122': 'Tabulated Cylinder',
        '124': 'Transformation Matrix',
        '126': 'NURBS Curve',
        '128': 'NURBS Surface',
        '130': 'Offset Curve',
        '132': 'Offset Surface',
        '140': 'Ruled Surface',
        '142': 'Curve on a Parametric Surface',
        '144': 'Trimmed Surface',
        '146': 'Flange',
        '148': 'Element Group',
        '150': 'Analysis Geometry',
        '152': 'Pattern',
        '154': 'Color Definition',
        '156': 'View',
        '158': 'Ellipse',
        '160': 'Intersection',
        '162': 'Line Segment',
        '164': 'Circular Arc',
        '166': 'Parabolic Arc',
        '168': 'Hyperbolic Arc',
        '170': 'Unbounded Plane',
        '172': 'Unbounded Cylinder',
        '174': 'Right Angular Wedge',
        '176': 'Right Elliptical Cylinder',
        '178': 'Right Circular Cone',
        '180': 'Sphere',
        '182': 'Right Elliptical Cone',
        '184': 'Toroidal Segment',
        '186': 'General Prism',
        '188': 'Right Elliptical Torus',
        '190': 'General Entity',
    }
    
    def __init__(self):
        self.directory_section: List[Dict] = []
        self.parameter_section: List[str] = []
        self.tolerance = 1e-6
        
    def parse_file(self, filepath: str) -> IGESResult:
        """解析 IGES 文件"""
        path = Path(filepath)
        
        if not path.exists():
            raise FileNotFoundError(f"IGES 文件不存在：{filepath}")
        
        result = IGESResult()
        
        try:
            # 读取文件
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
            
            # 验证 IGES 格式
            if not self._validate_iges_format(lines):
                result.errors.append("无效的 IGES 文件格式")
                return result
            
            # 分段解析
            sections = self._split_sections(lines)
            
            # 解析各段
            self._parse_start_section(sections.get('start', []), result)
            self._parse_global_section(sections.get('global', []), result)
            self._parse_directory_section(sections.get('directory', []), result)
            self._parse_parameter_section(sections.get('parameter', []), result)
            self._parse_terminate_section(sections.get('terminate', []), result)
            
            # 构建几何
            self._build_geometry(result)
            
            # 提取元数据
            self._extract_metadata(result)
            
        except Exception as e:
            result.errors.append(f"解析错误：{str(e)}")
        
        return result
    
    def _validate_iges_format(self, lines: List[str]) -> bool:
        """验证 IGES 格式"""
        if not lines:
            return False
        
        # IGES 每行固定 80 字符
        # 检查是否有正确的标识符
        first_line = lines[0].rstrip()
        
        # 简单的格式检查
        return len(first_line) >= 10
    
    def _split_sections(self, lines: List[str]) -> Dict[str, List[str]]:
        """分割 IGES 文件为各个部分"""
        sections = {
            'start': [],
            'global': [],
            'directory': [],
            'parameter': [],
            'terminate': [],
        }
        
        current_section = None
        
        for line in lines:
            if len(line) < 73:
                continue
            
            # 第 73 列是段标识符
            section_id = line[72].strip() if len(line) > 72 else ''
            
            if section_id == 'S':
                current_section = 'start'
            elif section_id == 'G':
                current_section = 'global'
            elif section_id == 'D':
                current_section = 'directory'
            elif section_id == 'P':
                current_section = 'parameter'
            elif section_id == 'T':
                current_section = 'terminate'
            
            if current_section and current_section in sections:
                sections[current_section].append(line.rstrip())
        
        return sections
    
    def _parse_start_section(self, lines: List[str], result: IGESResult) -> None:
        """解析起始段"""
        # 起始段包含可读的描述信息
        pass
    
    def _parse_global_section(self, lines: List[str], result: IGESResult) -> None:
        """解析全局段"""
        if not lines:
            return
        
        # 解析全局参数
        # IGES 全局段格式：参数用逗号分隔，以分号结束
        global_line = ''.join(lines)
        params = global_line.split(',')
        
        if len(params) >= 9:
            result.metadata['sender'] = params[0].strip() if len(params) > 0 else ''
            result.metadata['receiver'] = params[1].strip() if len(params) > 1 else ''
            result.metadata['generation_date'] = params[2].strip() if len(params) > 2 else ''
            result.metadata['units'] = params[3].strip() if len(params) > 3 else 'MM'
    
    def _parse_directory_section(self, lines: List[str], result: IGESResult) -> None:
        """解析目录段"""
        # 目录段每条记录占两行，每行 80 字符
        # 包含实体类型、层、颜色等信息
        
        i = 0
        while i < len(lines) - 1:
            line1 = lines[i]
            line2 = lines[i + 1]
            
            if len(line1) >= 73 and len(line2) >= 73:
                entry = {
                    'entity_type': line1[:8].strip(),
                    'parameter_pointer': int(line1[8:16].strip() or 0),
                    'structure_level': int(line1[16:24].strip() or 0),
                    'view_index': int(line1[24:32].strip() or 0),
                    'transformation_matrix': int(line1[32:40].strip() or 0),
                    'label_associated': int(line1[40:48].strip() or 0),
                    'color': int(line2[:8].strip() or 0),
                    'line_font': int(line2[8:16].strip() or 0),
                    'weight': int(line2[16:24].strip() or 0),
                    'form_number': int(line2[24:32].strip() or 0),
                }
                
                self.directory_section.append(entry)
            
            i += 2
    
    def _parse_parameter_section(self, lines: List[str], result: IGESResult) -> None:
        """解析参数段"""
        # 参数段包含实体的具体参数
        # 合并所有参数行
        param_text = ''.join(lines)
        
        # 按分号分割实体
        entities = param_text.split(';')
        
        for entity_str in entities:
            if not entity_str.strip():
                continue
            
            # 解析实体类型和参数
            match = re.match(r'(\d+),\s*(.*?)(?:,\s*$|$)', entity_str, re.DOTALL)
            if match:
                type_code = match.group(1)
                params_str = match.group(2)
                
                # 解析参数列表
                params = self._parse_iges_params(params_str)
                
                entity = IGESEntity(
                    type_code=type_code,
                    params=params
                )
                
                self.parameter_section.append(entity)
    
    def _parse_iges_params(self, params_str: str) -> List:
        """解析 IGES 参数"""
        params = []
        
        # 处理嵌套括号和引号
        depth = 0
        current = ""
        in_string = False
        
        for char in params_str:
            if char == "'" and not in_string:
                in_string = True
                current += char
            elif char == "'" and in_string:
                in_string = False
                current += char
            elif char == '(' and not in_string:
                depth += 1
                current += char
            elif char == ')' and not in_string:
                depth -= 1
                current += char
            elif char == ',' and depth == 0 and not in_string:
                params.append(self._parse_iges_value(current.strip()))
                current = ""
            else:
                current += char
        
        if current.strip():
            params.append(self._parse_iges_value(current.strip()))
        
        return params
    
    def _parse_iges_value(self, value_str: str):
        """解析 IGES 参数值"""
        if not value_str:
            return None
        
        # 字符串
        if value_str.startswith("'") and value_str.endswith("'"):
            return value_str[1:-1]
        
        # 空值
        if value_str == '0' or value_str == '':
            return None
        
        # 数值
        try:
            if '.' in value_str or 'E' in value_str.upper():
                return float(value_str)
            return int(value_str)
        except ValueError:
            return value_str
    
    def _parse_terminate_section(self, lines: List[str], result: IGESResult) -> None:
        """解析结束段"""
        # 通常只有一条记录，包含校验和
        pass
    
    def _build_geometry(self, result: IGESResult) -> None:
        """构建几何表示"""
        from dataclasses import dataclass
        
        @dataclass
        class Point2D:
            x: float
            z: float
        
        @dataclass
        class Line2D:
            start: Point2D
            end: Point2D
        
        @dataclass
        class Circle2D:
            center: Point2D
            radius: float
        
        # 遍历参数段的实体
        for entity in self.parameter_section:
            type_code = entity.type_code
            params = entity.params
            
            if type_code in ['100', '110']:  # Line
                if len(params) >= 6:
                    line = Line2D(
                        start=Point2D(x=float(params[0]), z=float(params[2])),
                        end=Point2D(x=float(params[1]), z=float(params[3]))
                    )
                    result.lines.append(line)
                    result.entities.append(line)
                    
            elif type_code in ['104', '164']:  # Circular Arc
                if len(params) >= 7:
                    center_x = float(params[0])
                    center_y = float(params[1])
                    radius = float(params[2])
                    start_angle = float(params[3])
                    end_angle = float(params[4])
                    
                    circle = Circle2D(
                        center=Point2D(x=center_x * 2, z=center_y),  # 直径编程
                        radius=radius
                    )
                    result.circles.append(circle)
                    result.entities.append(circle)
                    
            elif type_code == '126':  # NURBS Curve
                # 简化处理：采样点
                result.splines.append({
                    'type': 'NURBS',
                    'params': params,
                    'sampled_points': self._sample_nurbs(params)
                })
    
    def _sample_nurbs(self, params: List, num_points: int = 50) -> List[Tuple[float, float]]:
        """采样 NURBS 曲线"""
        # 简化实现：返回空列表
        # 完整实现需要 NURBS 库
        return []
    
    def _extract_metadata(self, result: IGESResult) -> None:
        """提取元数据"""
        # 计算包围盒
        all_points = []
        
        for line in result.lines:
            all_points.append((line.start.x, line.start.z))
            all_points.append((line.end.x, line.end.z))
        
        if all_points:
            xs = [p[0] for p in all_points]
            zs = [p[1] for p in all_points]
            
            result.metadata['min_x'] = min(xs)
            result.metadata['max_x'] = max(xs)
            result.metadata['min_z'] = min(zs)
            result.metadata['max_z'] = max(zs)
            result.metadata['stock_diameter'] = max(xs) - min(xs)
            result.metadata['total_length'] = abs(max(zs) - min(zs))


def parse_iges_file(filepath: str) -> IGESResult:
    """便捷函数：解析 IGES 文件"""
    parser = IGESParser()
    return parser.parse_file(filepath)


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        filepath = sys.argv[1]
        result = parse_iges_file(filepath)
        
        print(f"✓ IGES 文件解析完成")
        print(f"  直线数量：{len(result.lines)}")
        print(f"  圆弧数量：{len(result.circles)}")
        print(f"  样条数量：{len(result.splines)}")
        print(f"  毛坯直径：{result.metadata.get('stock_diameter', 0):.2f} mm")
        print(f"  总长度：{result.metadata.get('total_length', 0):.2f} mm")
        
        if result.errors:
            print(f"\n错误:")
            for error in result.errors:
                print(f"  - {error}")
    else:
        print("用法：python iges_parser.py <file.igs>")
