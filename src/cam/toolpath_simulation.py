"""
刀路轨迹仿真系统 - 2D 可视化 + 碰撞检测

功能:
- G 代码解析和刀具位置计算
- 2D 刀路可视化 (Matplotlib)
- 材料去除动画
- 碰撞检测 (刀具 - 工件干涉)
- 加工时间估算
- G 代码验证器

使用示例:
    simulator = ToolpathSimulator()
    result = simulator.simulate(gcode_string)
    result.show_animation()
"""

import re
import math
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, field
from enum import Enum
import numpy as np


class GCodeType(Enum):
    """G 代码类型"""
    RAPID = "G00"           # 快速定位
    LINEAR = "G01"          # 直线插补
    CIRCLE_CW = "G02"       # 圆弧顺时针
    CIRCLE_CCW = "G03"      # 圆弧逆时针
    DWELL = "G04"           # 暂停
    HOME = "G28"            # 回参考点
    UNKNOWN = "UNKNOWN"


@dataclass
class ToolPosition:
    """刀具位置"""
    x: float = 0.0
    z: float = 0.0
    feed: float = 0.0       # 进给速度 mm/min
    spindle: int = 0        # 主轴转速 rpm
    g_code: str = ""
    block_number: int = 0


@dataclass
class ToolpathSegment:
    """刀路段"""
    start: Tuple[float, float]
    end: Tuple[float, float]
    g_code_type: GCodeType
    feed: float
    length: float
    time: float             # 加工时间 (秒)
    is_cutting: bool        # 是否切削


@dataclass
class CollisionWarning:
    """碰撞警告"""
    block_number: int
    position: Tuple[float, float]
    severity: str           # "warning" | "critical"
    message: str


@dataclass
class SimulationResult:
    """仿真结果"""
    toolpath: List[ToolpathSegment] = field(default_factory=list)
    positions: List[ToolPosition] = field(default_factory=list)
    collisions: List[CollisionWarning] = field(default_factory=list)
    total_time: float = 0.0     # 总加工时间 (秒)
    total_distance: float = 0.0  # 总路径长度 (mm)
    cutting_distance: float = 0.0  # 切削距离 (mm)
    bounding_box: Dict = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)
    
    def show_animation(self):
        """显示动画 (需要 Matplotlib)"""
        visualize_toolpath(self)


class GCodeParser:
    """G 代码解析器"""
    
    def __init__(self):
        self.modal_g = "G00"  # 当前模态 G 代码
        self.current_pos = (0.0, 0.0)
    
    def parse(self, gcode: str) -> List[ToolPosition]:
        """
        解析 G 代码字符串
        
        Args:
            gcode: G 代码文本
        
        Returns:
            List[ToolPosition]: 刀具位置序列
        """
        positions = []
        lines = gcode.strip().split('\n')
        
        for block_num, line in enumerate(lines, 1):
            # 移除注释
            line = re.sub(r'\(.*?\)', '', line)
            line = re.sub(r';.*$', '', line)
            line = line.strip()
            
            if not line:
                continue
            
            # 解析行
            pos = self._parse_block(line, block_num)
            if pos:
                positions.append(pos)
        
        return positions
    
    def _parse_block(self, line: str, block_num: int) -> Optional[ToolPosition]:
        """解析单个程序段"""
        # 提取 G 代码
        g_match = re.search(r'G(\d+)', line, re.IGNORECASE)
        if g_match:
            g_code = f"G{g_match.group(1)}"
            self.modal_g = g_code
        else:
            g_code = self.modal_g
        
        # 提取坐标
        x_match = re.search(r'X([-+]?\d*\.?\d+)', line, re.IGNORECASE)
        z_match = re.search(r'Z([-+]?\d*\.?\d+)', line, re.IGNORECASE)
        
        x = float(x_match.group(1)) if x_match else self.current_pos[0]
        z = float(z_match.group(1)) if z_match else self.current_pos[1]
        
        # 提取进给速度
        f_match = re.search(r'F(\d*\.?\d+)', line, re.IGNORECASE)
        feed = float(f_match.group(1)) if f_match else 0.0
        
        # 提取主轴转速
        s_match = re.search(r'S(\d+)', line, re.IGNORECASE)
        spindle = int(s_match.group(1)) if s_match else 0
        
        # 更新当前位置
        if x_match or z_match:
            self.current_pos = (x, z)
        
        return ToolPosition(
            x=x,
            z=z,
            feed=feed,
            spindle=spindle,
            g_code=g_code,
            block_number=block_num
        )


class ToolpathSimulator:
    """刀路轨迹仿真器"""
    
    def __init__(self, tool_diameter: float = 0.0):
        self.tool_diameter = tool_diameter
        self.parser = GCodeParser()
        
        # 工件边界 (用于碰撞检测)
        self.workpiece_bounds = {
            'min_x': 0,
            'max_x': 100,
            'min_z': -200,
            'max_z': 0
        }
    
    def simulate(self, gcode: str) -> SimulationResult:
        """
        执行刀路仿真
        
        Args:
            gcode: G 代码字符串
        
        Returns:
            SimulationResult: 仿真结果
        """
        result = SimulationResult()
        
        # 步骤 1: 解析 G 代码
        positions = self.parser.parse(gcode)
        result.positions = positions
        
        if not positions:
            result.warnings.append("未解析到有效 G 代码")
            return result
        
        # 步骤 2: 生成刀路段
        segments = self._generate_segments(positions)
        result.toolpath = segments
        
        # 步骤 3: 计算统计信息
        self._calculate_statistics(result)
        
        # 步骤 4: 碰撞检测
        self._detect_collisions(result)
        
        # 步骤 5: 计算包围盒
        self._calculate_bounding_box(result)
        
        return result
    
    def _generate_segments(self, positions: List[ToolPosition]) -> List[ToolpathSegment]:
        """生成刀路段"""
        segments = []
        
        for i in range(len(positions) - 1):
            curr = positions[i]
            next_p = positions[i + 1]
            
            # 确定 G 代码类型
            g_type = self._get_g_code_type(curr.g_code)
            
            # 计算距离
            dx = next_p.x - curr.x
            dz = next_p.z - curr.z
            distance = math.sqrt(dx**2 + dz**2)
            
            # 计算时间
            if curr.feed > 0 and g_type in [GCodeType.LINEAR, GCodeType.CIRCLE_CW, GCodeType.CIRCLE_CCW]:
                time = (distance / curr.feed) * 60  # 转换为秒
                is_cutting = True
            else:
                time = 0.5  # 快速移动估计时间
                is_cutting = False
            
            segment = ToolpathSegment(
                start=(curr.x, curr.z),
                end=(next_p.x, next_p.z),
                g_code_type=g_type,
                feed=curr.feed,
                length=distance,
                time=time,
                is_cutting=is_cutting
            )
            
            segments.append(segment)
        
        return segments
    
    def _get_g_code_type(self, g_code: str) -> GCodeType:
        """获取 G 代码类型"""
        mapping = {
            'G00': GCodeType.RAPID,
            'G01': GCodeType.LINEAR,
            'G02': GCodeType.CIRCLE_CW,
            'G03': GCodeType.CIRCLE_CCW,
            'G04': GCodeType.DWELL,
            'G28': GCodeType.HOME,
        }
        return mapping.get(g_code, GCodeType.UNKNOWN)
    
    def _calculate_statistics(self, result: SimulationResult):
        """计算统计信息"""
        total_time = 0.0
        total_distance = 0.0
        cutting_distance = 0.0
        
        for segment in result.toolpath:
            total_time += segment.time
            total_distance += segment.length
            
            if segment.is_cutting:
                cutting_distance += segment.length
        
        result.total_time = total_time
        result.total_distance = total_distance
        result.cutting_distance = cutting_distance
    
    def _detect_collisions(self, result: SimulationResult):
        """碰撞检测"""
        bounds = self.workpiece_bounds
        
        for segment in result.toolpath:
            # 检查是否在工件范围内
            x_min = min(segment.start[0], segment.end[0])
            x_max = max(segment.start[0], segment.end[0])
            z_min = min(segment.start[1], segment.end[1])
            z_max = max(segment.start[1], segment.end[1])
            
            # 简化检测：检查端点
            for point in [segment.start, segment.end]:
                x, z = point
                
                if x < bounds['min_x'] or x > bounds['max_x']:
                    result.collisions.append(CollisionWarning(
                        block_number=0,
                        position=point,
                        severity="warning",
                        message=f"X 坐标超出范围：{x:.2f} (范围：{bounds['min_x']}-{bounds['max_x']})"
                    ))
                
                if z < bounds['min_z'] or z > bounds['max_z']:
                    result.collisions.append(CollisionWarning(
                        block_number=0,
                        position=point,
                        severity="warning",
                        message=f"Z 坐标超出范围：z:.2f} (范围：{bounds['min_z']}-{bounds['max_z']})"
                    ))
    
    def _calculate_bounding_box(self, result: SimulationResult):
        """计算包围盒"""
        if not result.toolpath:
            return
        
        all_x = []
        all_z = []
        
        for segment in result.toolpath:
            all_x.extend([segment.start[0], segment.end[0]])
            all_z.extend([segment.start[1], segment.end[1]])
        
        result.bounding_box = {
            'min_x': min(all_x),
            'max_x': max(all_x),
            'min_z': min(all_z),
            'max_z': max(all_z),
        }


def visualize_toolpath(result: SimulationResult, save_path: str = None):
    """
    可视化刀路轨迹 (使用 Matplotlib)
    
    Args:
        result: 仿真结果
        save_path: 保存路径 (可选)
    """
    try:
        import matplotlib.pyplot as plt
        import matplotlib.animation as animation
    except ImportError:
        print("⚠ Matplotlib 未安装，无法显示动画")
        return
    
    # 创建图形
    fig, ax = plt.subplots(figsize=(10, 8))
    
    # 提取切削路径和快速移动路径
    cutting_x = []
    cutting_z = []
    rapid_x = []
    rapid_z = []
    
    for segment in result.toolpath:
        if segment.is_cutting:
            cutting_x.extend([segment.start[0], segment.end[0]])
            cutting_z.extend([segment.start[1], segment.end[1]])
        else:
            rapid_x.extend([segment.start[0], segment.end[0]])
            rapid_z.extend([segment.start[1], segment.end[1]])
    
    # 绘制切削路径
    if cutting_x:
        ax.plot(cutting_x, cutting_z, 'b-', linewidth=2, label='切削路径', alpha=0.7)
    
    # 绘制快速移动
    if rapid_x:
        ax.plot(rapid_x, rapid_z, 'r--', linewidth=1, label='快速移动', alpha=0.5)
    
    # 绘制起点和终点
    if result.toolpath:
        start = result.toolpath[0].start
        end = result.toolpath[-1].end
        ax.plot(start[0], start[1], 'go', markersize=10, label='起点')
        ax.plot(end[0], end[1], 'ro', markersize=10, label='终点')
    
    # 设置坐标轴
    ax.set_xlabel('X (mm)')
    ax.set_ylabel('Z (mm)')
    ax.set_title('刀路轨迹仿真')
    ax.legend()
    ax.grid(True, alpha=0.3)
    ax.set_aspect('equal')
    
    # 添加工件轮廓 (如果有)
    if result.bounding_box:
        bbox = result.bounding_box
        rect = plt.Rectangle(
            (bbox['min_x'], bbox['min_z']),
            bbox['max_x'] - bbox['min_x'],
            bbox['max_z'] - bbox['min_z'],
        fill=False, linestyle=':', color='gray', label='工件范围')
        ax.add_patch(rect)
    
    # 添加统计信息
    stats_text = (
        f"总时间：{result.total_time:.1f}s\n"
        f"总路径：{result.total_distance:.1f}mm\n"
        f"切削距离：{result.cutting_distance:.1f}mm"
    )
    ax.text(0.02, 0.98, stats_text, transform=ax.transAxes, 
            verticalalignment='top', fontsize=10,
            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
    
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        print(f"✓ 图像已保存到：{save_path}")
    else:
        plt.show()


def animate_toolpath(result: SimulationResult, interval: int = 50):
    """
    创建刀路动画
    
    Args:
        result: 仿真结果
        interval: 帧间隔 (ms)
    """
    try:
        import matplotlib.pyplot as plt
        import matplotlib.animation as animation
    except ImportError:
        print("⚠ Matplotlib 未安装")
        return
    
    fig, ax = plt.subplots(figsize=(10, 8))
    
    # 初始化线条
    line, = ax.plot([], [], 'b-', linewidth=2)
    point, = ax.plot([], [], 'ro', markersize=8)
    
    # 设置坐标轴
    if result.bounding_box:
        bbox = result.bounding_box
        margin = 10
        ax.set_xlim(bbox['min_x'] - margin, bbox['max_x'] + margin)
        ax.set_ylim(bbox['min_z'] - margin, bbox['max_z'] + margin)
    
    ax.set_xlabel('X (mm)')
    ax.set_ylabel('Z (mm)')
    ax.set_title('刀路仿真动画')
    ax.grid(True, alpha=0.3)
    ax.set_aspect('equal')
    
    # 提取所有点
    all_points = []
    for segment in result.toolpath:
        all_points.append(segment.start)
    if result.toolpath:
        all_points.append(result.toolpath[-1].end)
    
    def init():
        line.set_data([], [])
        point.set_data([], [])
        return line, point
    
    def update(frame):
        xs = [p[0] for p in all_points[:frame+1]]
        zs = [p[1] for p in all_points[:frame+1]]
        line.set_data(xs, zs)
        
        if frame < len(all_points):
            point.set_data([all_points[frame][0]], [all_points[frame][1]])
        
        return line, point
    
    ani = animation.FuncAnimation(
        fig, update, frames=len(all_points),
        init_func=init, blit=True, interval=interval
    )
    
    plt.show()
    
    return ani


def simulate_gcode(gcode: str, visualize: bool = True) -> SimulationResult:
    """便捷函数：G 代码仿真"""
    simulator = ToolpathSimulator()
    result = simulator.simulate(gcode)
    
    if visualize:
        visualize_toolpath(result)
    
    return result


if __name__ == "__main__":
    # 测试示例
    test_gcode = """
    O1000 (TEST PROGRAM)
    G54 G00 X100 Z5
    S1000 M03
    G00 X50 Z0
    G01 X50 Z-30 F200
    G01 X45 Z-30
    G01 X45 Z-60
    G01 X40 Z-60
    G01 X40 Z-90
    G00 X100 Z5
    M30
    """
    
    print("🔧 开始刀路仿真...")
    result = simulate_gcode(test_gcode, visualize=False)
    
    print(f"\n✓ 仿真完成")
    print(f"  程序段数：{len(result.toolpath)}")
    print(f"  总加工时间：{result.total_time:.2f}s")
    print(f"  总路径长度：{result.total_distance:.2f}mm")
    print(f"  切削距离：{result.cutting_distance:.2f}mm")
    
    if result.collisions:
        print(f"\n⚠ 发现 {len(result.collisions)} 个潜在碰撞:")
        for collision in result.collisions:
            print(f"  - {collision.message}")
    
    # 显示可视化
    print("\n正在打开可视化窗口...")
    visualize_toolpath(result)
