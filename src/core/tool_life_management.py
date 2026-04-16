"""
刀具寿命管理模块 - Tool Life Management

企业级刀具管理，支持：
- 刀具使用次数记录
- 寿命预警
- 换刀提醒
- 刀具成本统计
- 供应商信息管理
"""

import json
import sqlite3
import threading
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


class ToolStatus(str, Enum):
    """刀具状态枚举"""
    AVAILABLE = "available"      # 可用
    IN_USE = "in_use"           # 使用中
    MAINTENANCE = "maintenance"  # 维护中
    WORN = "worn"               # 磨损
    REPLACED = "replaced"       # 已更换
    SCRAPPED = "scrapped"       # 已报废


class ToolType(str, Enum):
    """刀具类型枚举"""
    TURNING = "turning"         # 车刀
    GROOVING = "grooving"       # 切槽刀
    THREADING = "threading"     # 螺纹刀
    DRILLING = "drilling"       # 钻头
    BORING = "boring"           # 镗刀
    PARTING = "parting"         # 切断刀


@dataclass
class Tool:
    """刀具数据类"""
    id: Optional[int] = None
    tool_number: str = ""              # 刀具编号 (如 T0101)
    name: str = ""                     # 刀具名称
    tool_type: str = ""                # 刀具类型
    model: str = ""                    # 型号
    insert_material: str = ""          # 刀片材料
    insert_shape: str = ""             # 刀片形状
    manufacturer: str = ""             # 制造商
    supplier: str = ""                 # 供应商
    unit_price: float = 0.0            # 单价（元）
    
    # 寿命管理
    max_life_minutes: int = 600        # 最大寿命（分钟）
    used_life_minutes: int = 0         # 已用寿命（分钟）
    remaining_life_minutes: int = 600  # 剩余寿命（分钟）
    life_warning_threshold: float = 0.2  # 寿命预警阈值（20%）
    
    # 使用统计
    usage_count: int = 0               # 使用次数
    total_parts: int = 0               # 加工零件总数
    
    # 状态
    status: str = ToolStatus.AVAILABLE
    install_date: Optional[str] = None
    last_maintenance_date: Optional[str] = None
    replacement_date: Optional[str] = None
    
    # 备注
    notes: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now().isoformat()
        if self.install_date is None and self.status == ToolStatus.IN_USE:
            self.install_date = datetime.now().isoformat()
        self.updated_at = datetime.now().isoformat()
        
        # 计算剩余寿命
        self.remaining_life_minutes = max(0, self.max_life_minutes - self.used_life_minutes)
    
    @property
    def life_percentage(self) -> float:
        """剩余寿命百分比"""
        if self.max_life_minutes <= 0:
            return 0.0
        return self.remaining_life_minutes / self.max_life_minutes
    
    @property
    def needs_replacement(self) -> bool:
        """是否需要更换"""
        return self.life_percentage <= self.life_warning_threshold
    
    @property
    def estimated_cost_per_part(self) -> float:
        """单件刀具成本估算"""
        if self.total_parts <= 0:
            return 0.0
        return self.unit_price / self.total_parts
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        data = asdict(self)
        data["life_percentage"] = self.life_percentage
        data["needs_replacement"] = self.needs_replacement
        data["estimated_cost_per_part"] = self.estimated_cost_per_part
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Tool':
        """从字典创建"""
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class ToolUsageRecord:
    """刀具使用记录"""
    id: Optional[int] = None
    tool_id: int = 0
    program_id: Optional[int] = None
    program_name: str = ""
    operation_type: str = ""
    duration_minutes: float = 0.0
    parts_count: int = 0
    wear_level: float = 0.0  # 磨损程度 0-1
    notes: Optional[str] = None
    recorded_at: Optional[str] = None
    
    def __post_init__(self):
        if self.recorded_at is None:
            self.recorded_at = datetime.now().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ToolLifeManager:
    """刀具寿命管理器"""
    
    def __init__(self, db_path: str = None):
        """
        初始化刀具管理器
        
        Args:
            db_path: SQLite 数据库路径，默认与 GCodeDatabase 共用
        """
        if db_path is None:
            db_path = Path(__file__).parent.parent / "data" / "gcode.db"
        
        self.db_path = str(db_path)
        self._lock = threading.Lock()
        
        self._init_database()
        logger.info(f"ToolLifeManager initialized with database: {self.db_path}")
    
    def _init_database(self):
        """初始化数据库表"""
        with sqlite3.connect(self.db_path) as conn:
            # 刀具表
            conn.execute("""
                CREATE TABLE IF NOT EXISTS tools (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tool_number TEXT UNIQUE NOT NULL,
                    name TEXT NOT NULL,
                    tool_type TEXT,
                    model TEXT,
                    insert_material TEXT,
                    insert_shape TEXT,
                    manufacturer TEXT,
                    supplier TEXT,
                    unit_price REAL DEFAULT 0.0,
                    
                    max_life_minutes INTEGER DEFAULT 600,
                    used_life_minutes INTEGER DEFAULT 0,
                    life_warning_threshold REAL DEFAULT 0.2,
                    
                    usage_count INTEGER DEFAULT 0,
                    total_parts INTEGER DEFAULT 0,
                    
                    status TEXT DEFAULT 'available',
                    install_date TEXT,
                    last_maintenance_date TEXT,
                    replacement_date TEXT,
                    
                    notes TEXT,
                    created_at TEXT,
                    updated_at TEXT
                )
            """)
            
            # 刀具使用记录表
            conn.execute("""
                CREATE TABLE IF NOT EXISTS tool_usage_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tool_id INTEGER NOT NULL,
                    program_id INTEGER,
                    program_name TEXT,
                    operation_type TEXT,
                    duration_minutes REAL DEFAULT 0.0,
                    parts_count INTEGER DEFAULT 0,
                    wear_level REAL DEFAULT 0.0,
                    notes TEXT,
                    recorded_at TEXT,
                    FOREIGN KEY (tool_id) REFERENCES tools(id)
                )
            """)
            
            # 刀具维护记录表
            conn.execute("""
                CREATE TABLE IF NOT EXISTS tool_maintenance_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tool_id INTEGER NOT NULL,
                    maintenance_type TEXT,
                    description TEXT,
                    cost REAL DEFAULT 0.0,
                    performed_by TEXT,
                    recorded_at TEXT,
                    FOREIGN KEY (tool_id) REFERENCES tools(id)
                )
            """)
            
            # 创建索引
            conn.execute("CREATE INDEX IF NOT EXISTS idx_tools_status ON tools(status)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_tools_type ON tools(tool_type)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_usage_tool ON tool_usage_records(tool_id)")
            
            conn.commit()
        logger.info("Tool management tables initialized")
    
    def add_tool(self, tool: Tool) -> int:
        """
        添加新刀具
        
        Args:
            tool: 刀具对象
            
        Returns:
            刀具 ID
        """
        with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    INSERT INTO tools (
                        tool_number, name, tool_type, model, insert_material,
                        insert_shape, manufacturer, supplier, unit_price,
                        max_life_minutes, used_life_minutes, life_warning_threshold,
                        status, install_date, notes, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    tool.tool_number,
                    tool.name,
                    tool.tool_type,
                    tool.model,
                    tool.insert_material,
                    tool.insert_shape,
                    tool.manufacturer,
                    tool.supplier,
                    tool.unit_price,
                    tool.max_life_minutes,
                    tool.used_life_minutes,
                    tool.life_warning_threshold,
                    tool.status,
                    tool.install_date,
                    tool.notes,
                    tool.created_at,
                    tool.updated_at
                ))
                tool.id = cursor.lastrowid
                conn.commit()
        
        logger.info(f"Tool added: id={tool.id}, number={tool.tool_number}")
        return tool.id
    
    def get_tool(self, tool_id: int) -> Optional[Tool]:
        """获取刀具详情"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT id, tool_number, name, tool_type, model, insert_material,
                       insert_shape, manufacturer, supplier, unit_price,
                       max_life_minutes, used_life_minutes, life_warning_threshold,
                       usage_count, total_parts, status, install_date,
                       last_maintenance_date, replacement_date, notes,
                       created_at, updated_at
                FROM tools
                WHERE id = ?
            """, (tool_id,))
            
            row = cursor.fetchone()
            if not row:
                return None
            
            return Tool(
                id=row[0],
                tool_number=row[1],
                name=row[2],
                tool_type=row[3],
                model=row[4],
                insert_material=row[5],
                insert_shape=row[6],
                manufacturer=row[7],
                supplier=row[8],
                unit_price=row[9],
                max_life_minutes=row[10],
                used_life_minutes=row[11],
                life_warning_threshold=row[12],
                usage_count=row[13],
                total_parts=row[14],
                status=row[15],
                install_date=row[16],
                last_maintenance_date=row[17],
                replacement_date=row[18],
                notes=row[19],
                created_at=row[20],
                updated_at=row[21]
            )
    
    def get_tool_by_number(self, tool_number: str) -> Optional[Tool]:
        """通过刀具编号获取刀具"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT id FROM tools WHERE tool_number = ?
            """, (tool_number,))
            row = cursor.fetchone()
            
            if not row:
                return None
            
            return self.get_tool(row[0])
    
    def list_tools(
        self,
        tool_type: str = None,
        status: str = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Tool]:
        """列出刀具"""
        query = """
            SELECT id, tool_number, name, tool_type, model, insert_material,
                   insert_shape, manufacturer, supplier, unit_price,
                   max_life_minutes, used_life_minutes, life_warning_threshold,
                   usage_count, total_parts, status, install_date,
                   last_maintenance_date, replacement_date, notes,
                   created_at, updated_at
            FROM tools
            WHERE 1=1
        """
        params = []
        
        if tool_type:
            query += " AND tool_type = ?"
            params.append(tool_type)
        
        if status:
            query += " AND status = ?"
            params.append(status)
        
        query += " ORDER BY tool_number LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(query, params)
            tools = []
            for row in cursor.fetchall():
                tools.append(Tool(
                    id=row[0],
                    tool_number=row[1],
                    name=row[2],
                    tool_type=row[3],
                    model=row[4],
                    insert_material=row[5],
                    insert_shape=row[6],
                    manufacturer=row[7],
                    supplier=row[8],
                    unit_price=row[9],
                    max_life_minutes=row[10],
                    used_life_minutes=row[11],
                    life_warning_threshold=row[12],
                    usage_count=row[13],
                    total_parts=row[14],
                    status=row[15],
                    install_date=row[16],
                    last_maintenance_date=row[17],
                    replacement_date=row[18],
                    notes=row[19],
                    created_at=row[20],
                    updated_at=row[21]
                ))
        
        return tools
    
    def update_tool_status(self, tool_id: int, status: str):
        """更新刀具状态"""
        with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    UPDATE tools SET status = ?, updated_at = ? WHERE id = ?
                """, (status, datetime.now().isoformat(), tool_id))
                conn.commit()
        
        logger.info(f"Tool status updated: id={tool_id}, status={status}")
    
    def record_usage(
        self,
        tool_id: int,
        program_name: str,
        operation_type: str,
        duration_minutes: float,
        parts_count: int = 1,
        wear_level: float = 0.0,
        notes: str = None
    ):
        """
        记录刀具使用
        
        Args:
            tool_id: 刀具 ID
            program_name: 加工程序名称
            operation_type: 工序类型
            duration_minutes: 使用时长（分钟）
            parts_count: 加工零件数
            wear_level: 磨损程度 (0-1)
            notes: 备注
        """
        record = ToolUsageRecord(
            tool_id=tool_id,
            program_name=program_name,
            operation_type=operation_type,
            duration_minutes=duration_minutes,
            parts_count=parts_count,
            wear_level=wear_level,
            notes=notes
        )
        
        with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                # 插入使用记录
                conn.execute("""
                    INSERT INTO tool_usage_records (
                        tool_id, program_name, operation_type, duration_minutes,
                        parts_count, wear_level, notes, recorded_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    record.tool_id,
                    record.program_name,
                    record.operation_type,
                    record.duration_minutes,
                    record.parts_count,
                    record.wear_level,
                    record.notes,
                    record.recorded_at
                ))
                
                # 更新刀具累计数据
                conn.execute("""
                    UPDATE tools SET
                        used_life_minutes = used_life_minutes + ?,
                        usage_count = usage_count + 1,
                        total_parts = total_parts + ?,
                        updated_at = ?
                    WHERE id = ?
                """, (
                    duration_minutes,
                    parts_count,
                    datetime.now().isoformat(),
                    tool_id
                ))
                
                # 检查是否需要更换
                cursor = conn.execute("""
                    SELECT used_life_minutes, max_life_minutes, life_warning_threshold
                    FROM tools WHERE id = ?
                """, (tool_id,))
                row = cursor.fetchone()
                
                if row:
                    used, max_life, threshold = row
                    remaining = max_life - used
                    if remaining <= max_life * threshold:
                        conn.execute("""
                            UPDATE tools SET status = 'worn' WHERE id = ?
                        """, (tool_id,))
                
                conn.commit()
        
        logger.info(f"Tool usage recorded: tool_id={tool_id}, duration={duration_minutes}min")
    
    def get_usage_history(self, tool_id: int, days: int = 30) -> List[ToolUsageRecord]:
        """获取刀具使用历史"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT id, tool_id, program_id, program_name, operation_type,
                       duration_minutes, parts_count, wear_level, notes, recorded_at
                FROM tool_usage_records
                WHERE tool_id = ?
                AND date(recorded_at) >= date('now', ?)
                ORDER BY recorded_at DESC
            """, (tool_id, f'-{days} days'))
            
            records = []
            for row in cursor.fetchall():
                records.append(ToolUsageRecord(
                    id=row[0],
                    tool_id=row[1],
                    program_id=row[2],
                    program_name=row[3],
                    operation_type=row[4],
                    duration_minutes=row[5],
                    parts_count=row[6],
                    wear_level=row[7],
                    notes=row[8],
                    recorded_at=row[9]
                ))
        
        return records
    
    def get_tools_needing_replacement(self) -> List[Tool]:
        """获取需要更换的刀具列表"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT id FROM tools
                WHERE (max_life_minutes - used_life_minutes) <= (max_life_minutes * life_warning_threshold)
                AND status NOT IN ('replaced', 'scrapped')
            """)
            
            tools = []
            for row in cursor.fetchall():
                tool = self.get_tool(row[0])
                if tool:
                    tools.append(tool)
        
        return tools
    
    def get_tools_warnings(self) -> List[Dict[str, Any]]:
        """获取刀具预警信息"""
        warnings = []
        
        for tool in self.list_tools():
            if tool.life_percentage <= tool.life_warning_threshold:
                warnings.append({
                    "tool_id": tool.id,
                    "tool_number": tool.tool_number,
                    "name": tool.name,
                    "life_percentage": round(tool.life_percentage * 100, 1),
                    "remaining_minutes": tool.remaining_life_minutes,
                    "severity": "critical" if tool.life_percentage <= 0.1 else "warning",
                    "message": f"刀具 {tool.tool_number} ({tool.name}) 剩余寿命仅 {tool.life_percentage*100:.1f}%"
                })
        
        return sorted(warnings, key=lambda x: x["life_percentage"])
    
    def get_tool_statistics(self) -> Dict[str, Any]:
        """获取刀具统计数据"""
        with sqlite3.connect(self.db_path) as conn:
            # 总刀具数
            cursor = conn.execute("SELECT COUNT(*) FROM tools")
            total_tools = cursor.fetchone()[0]
            
            # 各状态刀具数
            cursor = conn.execute("""
                SELECT status, COUNT(*) FROM tools GROUP BY status
            """)
            status_breakdown = {row[0]: row[1] for row in cursor.fetchall()}
            
            # 平均寿命使用率
            cursor = conn.execute("""
                SELECT AVG(CAST(used_life_minutes AS FLOAT) / max_life_minutes)
                FROM tools WHERE max_life_minutes > 0
            """)
            avg_life_usage = cursor.fetchone()[0] or 0
            
            # 总加工零件数
            cursor = conn.execute("SELECT SUM(total_parts) FROM tools")
            total_parts = cursor.fetchone()[0] or 0
            
            # 总刀具成本
            cursor = conn.execute("SELECT SUM(unit_price) FROM tools")
            total_cost = cursor.fetchone()[0] or 0
        
        return {
            "total_tools": total_tools,
            "status_breakdown": status_breakdown,
            "available": status_breakdown.get("available", 0),
            "in_use": status_breakdown.get("in_use", 0),
            "worn": status_breakdown.get("worn", 0),
            "avg_life_usage_percent": round(avg_life_usage * 100, 1),
            "total_parts_machined": total_parts,
            "total_tool_cost": total_cost,
            "tools_needing_replacement": len(self.get_tools_needing_replacement())
        }
    
    def delete_tool(self, tool_id: int) -> bool:
        """删除刀具"""
        with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("DELETE FROM tools WHERE id = ?", (tool_id,))
                conn.commit()
                success = cursor.rowcount > 0
        
        if success:
            logger.info(f"Tool deleted: id={tool_id}")
        
        return success
    
    def add_maintenance_record(
        self,
        tool_id: int,
        maintenance_type: str,
        description: str,
        cost: float = 0.0,
        performed_by: str = None
    ):
        """添加维护记录"""
        with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO tool_maintenance_records (
                        tool_id, maintenance_type, description, cost,
                        performed_by, recorded_at
                    ) VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    tool_id,
                    maintenance_type,
                    description,
                    cost,
                    performed_by,
                    datetime.now().isoformat()
                ))
                
                # 更新最后维护日期
                conn.execute("""
                    UPDATE tools SET last_maintenance_date = ?, updated_at = ? WHERE id = ?
                """, (datetime.now().isoformat(), datetime.now().isoformat(), tool_id))
                
                conn.commit()
        
        logger.info(f"Maintenance record added: tool_id={tool_id}, type={maintenance_type}")


# 便捷函数
def get_tool_life_manager(db_path: str = None) -> ToolLifeManager:
    """获取刀具寿命管理器实例"""
    return ToolLifeManager(db_path)


# CLI 测试
if __name__ == "__main__":
    print("=" * 60)
    print("刀具寿命管理测试")
    print("=" * 60)
    
    manager = ToolLifeManager()
    
    # 添加测试刀具
    print("\n添加测试刀具...")
    tool1 = Tool(
        tool_number="T0101",
        name="外圆粗车刀",
        tool_type="turning",
        model="CNMG120408",
        insert_material="硬质合金",
        insert_shape="菱形",
        manufacturer="Sandvik",
        supplier="山特维克中国",
        unit_price=350.0,
        max_life_minutes=600
    )
    tool1_id = manager.add_tool(tool1)
    print(f"  添加刀具：{tool1.tool_number} - {tool1.name} (ID: {tool1_id})")
    
    tool2 = Tool(
        tool_number="T0202",
        name="切槽刀",
        tool_type="grooving",
        model="N123K2-0150",
        insert_material="硬质合金",
        manufacturer="Sandvik",
        unit_price=280.0,
        max_life_minutes=400
    )
    tool2_id = manager.add_tool(tool2)
    print(f"  添加刀具：{tool2.tool_number} - {tool2.name} (ID: {tool2_id})")
    
    # 记录使用
    print("\n记录刀具使用...")
    manager.record_usage(
        tool_id=tool1_id,
        program_name="TEST_PROGRAM_001",
        operation_type="rough_turning",
        duration_minutes=45.5,
        parts_count=10,
        wear_level=0.05
    )
    print(f"  记录 {tool1.tool_number} 使用 45.5 分钟，加工 10 个零件")
    
    # 查看统计
    print("\n刀具统计:")
    stats = manager.get_tool_statistics()
    print(f"  总刀具数：{stats['total_tools']}")
    print(f"  可用：{stats['available']}")
    print(f"  平均寿命使用率：{stats['avg_life_usage_percent']}%")
    print(f"  总加工零件：{stats['total_parts_machined']}")
    
    # 查看预警
    print("\n刀具预警:")
    warnings = manager.get_tools_warnings()
    if warnings:
        for w in warnings:
            print(f"  ⚠️  {w['message']}")
    else:
        print("  无预警")
    
    # 列出刀具
    print("\n刀具列表:")
    tools = manager.list_tools()
    for tool in tools:
        print(f"  [{tool.tool_number}] {tool.name} - {tool.status} "
              f"(寿命：{tool.life_percentage*100:.1f}%, 成本：¥{tool.unit_price})")
    
    print("\n测试完成!")
