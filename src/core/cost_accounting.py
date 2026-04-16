"""
成本核算模块 - Cost Accounting

企业级成本核算，支持：
- 加工成本计算（刀具 + 材料 + 机器时间）
- 单件成本分析
- 成本报表生成
- 成本趋势分析
- 预算与实际对比
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


class CostType(str, Enum):
    """成本类型枚举"""
    TOOL = "tool"              # 刀具成本
    MATERIAL = "material"      # 材料成本
    MACHINE_TIME = "machine_time"  # 机器时间成本
    LABOR = "labor"            # 人工成本
    OVERHEAD = "overhead"      # 间接费用
    MAINTENANCE = "maintenance"  # 维护成本


class CostCategory(str, Enum):
    """成本分类枚举"""
    VARIABLE = "variable"      # 可变成本
    FIXED = "fixed"           # 固定成本


@dataclass
class CostRecord:
    """成本记录数据类"""
    id: Optional[int] = None
    program_id: Optional[int] = None
    program_name: str = ""
    cost_type: str = ""
    category: str = ""
    amount: float = 0.0
    unit: str = ""             # 单位：元/分钟，元/件，元/kg 等
    quantity: float = 0.0      # 数量
    total: float = 0.0         # 总计
    notes: Optional[str] = None
    created_at: Optional[str] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now().isoformat()
        if self.total <= 0 and self.amount > 0 and self.quantity > 0:
            self.total = self.amount * self.quantity
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class JobCostSummary:
    """加工任务成本汇总"""
    program_id: int
    program_name: str
    tool_cost: float = 0.0
    material_cost: float = 0.0
    machine_time_cost: float = 0.0
    labor_cost: float = 0.0
    overhead_cost: float = 0.0
    maintenance_cost: float = 0.0
    total_cost: float = 0.0
    parts_count: int = 0
    cost_per_part: float = 0.0
    machining_time_minutes: float = 0.0
    
    def calculate_totals(self):
        """计算总成本和单件成本"""
        self.total_cost = (
            self.tool_cost +
            self.material_cost +
            self.machine_time_cost +
            self.labor_cost +
            self.overhead_cost +
            self.maintenance_cost
        )
        if self.parts_count > 0:
            self.cost_per_part = self.total_cost / self.parts_count
    
    def to_dict(self) -> Dict[str, Any]:
        self.calculate_totals()
        return asdict(self)


@dataclass
class CostParameters:
    """成本参数配置"""
    machine_hourly_rate: float = 150.0      # 机器小时费率（元/小时）
    labor_hourly_rate: float = 80.0         # 人工小时费率（元/小时）
    overhead_rate: float = 0.3              # 间接费率（占直接成本比例）
    material_waste_factor: float = 1.2      # 材料浪费系数
    default_tool_life_minutes: int = 600    # 默认刀具寿命（分钟）
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class CostAccountingManager:
    """成本核算管理器"""
    
    def __init__(self, db_path: str = None):
        """
        初始化成本核算管理器
        
        Args:
            db_path: SQLite 数据库路径
        """
        if db_path is None:
            db_path = Path(__file__).parent.parent / "data" / "gcode.db"
        
        self.db_path = str(db_path)
        self._lock = threading.Lock()
        
        # 默认成本参数
        self.default_params = CostParameters()
        
        self._init_database()
        self._load_parameters()
        logger.info(f"CostAccountingManager initialized with database: {self.db_path}")
    
    def _init_database(self):
        """初始化数据库表"""
        with sqlite3.connect(self.db_path) as conn:
            # 成本记录表
            conn.execute("""
                CREATE TABLE IF NOT EXISTS cost_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    program_id INTEGER,
                    program_name TEXT NOT NULL,
                    cost_type TEXT NOT NULL,
                    category TEXT NOT NULL,
                    amount REAL DEFAULT 0.0,
                    unit TEXT,
                    quantity REAL DEFAULT 0.0,
                    total REAL DEFAULT 0.0,
                    notes TEXT,
                    created_at TEXT
                )
            """)
            
            # 成本参数表
            conn.execute("""
                CREATE TABLE IF NOT EXISTS cost_parameters (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    param_name TEXT UNIQUE NOT NULL,
                    param_value REAL NOT NULL,
                    description TEXT,
                    updated_at TEXT
                )
            """)
            
            # 材料价格表
            conn.execute("""
                CREATE TABLE IF NOT EXISTS material_prices (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    material_name TEXT NOT NULL,
                    price_per_kg REAL NOT NULL,
                    supplier TEXT,
                    updated_at TEXT
                )
            """)
            
            # 创建索引
            conn.execute("CREATE INDEX IF NOT EXISTS idx_cost_program ON cost_records(program_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_cost_type ON cost_records(cost_type)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_cost_created ON cost_records(created_at)")
            
            # 插入默认参数
            self._insert_default_parameters(conn)
            
            conn.commit()
        logger.info("Cost accounting tables initialized")
    
    def _insert_default_parameters(self, conn):
        """插入默认成本参数"""
        defaults = [
            ("machine_hourly_rate", self.default_params.machine_hourly_rate, "机器小时费率（元/小时）"),
            ("labor_hourly_rate", self.default_params.labor_hourly_rate, "人工小时费率（元/小时）"),
            ("overhead_rate", self.default_params.overhead_rate, "间接费率（占直接成本比例）"),
            ("material_waste_factor", self.default_params.material_waste_factor, "材料浪费系数"),
            ("default_tool_life_minutes", self.default_params.default_tool_life_minutes, "默认刀具寿命（分钟）"),
        ]
        
        for name, value, desc in defaults:
            conn.execute("""
                INSERT OR IGNORE INTO cost_parameters (param_name, param_value, description, updated_at)
                VALUES (?, ?, ?, ?)
            """, (name, value, desc, datetime.now().isoformat()))
    
    def _load_parameters(self):
        """加载成本参数"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT param_name, param_value FROM cost_parameters")
            for name, value in cursor.fetchall():
                if hasattr(self.default_params, name):
                    setattr(self.default_params, name, value)
    
    def set_parameter(self, param_name: str, value: float, description: str = None):
        """设置成本参数"""
        with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO cost_parameters 
                    (param_name, param_value, description, updated_at)
                    VALUES (?, ?, ?, ?)
                """, (param_name, value, description, datetime.now().isoformat()))
                conn.commit()
        
        # 更新本地缓存
        if hasattr(self.default_params, param_name):
            setattr(self.default_params, param_name, value)
        
        logger.info(f"Cost parameter updated: {param_name}={value}")
    
    def get_parameter(self, param_name: str) -> float:
        """获取成本参数"""
        if hasattr(self.default_params, param_name):
            return getattr(self.default_params, param_name)
        return 0.0
    
    def add_cost_record(
        self,
        program_name: str,
        cost_type: str,
        amount: float,
        quantity: float = 1.0,
        unit: str = "元",
        category: str = "variable",
        program_id: int = None,
        notes: str = None
    ) -> int:
        """
        添加成本记录
        
        Args:
            program_name: 加工程序名称
            cost_type: 成本类型
            amount: 单价
            quantity: 数量
            unit: 单位
            category: 成本分类
            program_id: 程序 ID
            notes: 备注
            
        Returns:
            成本记录 ID
        """
        record = CostRecord(
            program_id=program_id,
            program_name=program_name,
            cost_type=cost_type,
            category=category,
            amount=amount,
            unit=unit,
            quantity=quantity,
            notes=notes
        )
        
        with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    INSERT INTO cost_records (
                        program_id, program_name, cost_type, category,
                        amount, unit, quantity, total, notes, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    record.program_id,
                    record.program_name,
                    record.cost_type,
                    record.category,
                    record.amount,
                    record.unit,
                    record.quantity,
                    record.total,
                    record.notes,
                    record.created_at
                ))
                record.id = cursor.lastrowid
                conn.commit()
        
        logger.info(f"Cost record added: program={program_name}, type={cost_type}, total={record.total}")
        return record.id
    
    def calculate_job_cost(self, program_id: int, program_name: str = None) -> JobCostSummary:
        """
        计算加工任务总成本
        
        Args:
            program_id: 程序 ID
            program_name: 程序名称（如果未提供则从数据库查询）
            
        Returns:
            成本汇总对象
        """
        summary = JobCostSummary(program_id=program_id, program_name=program_name or "")
        
        with sqlite3.connect(self.db_path) as conn:
            # 按成本类型汇总
            cursor = conn.execute("""
                SELECT cost_type, SUM(total) as total_cost
                FROM cost_records
                WHERE program_id = ?
                GROUP BY cost_type
            """, (program_id,))
            
            for row in cursor.fetchall():
                cost_type, total = row
                if cost_type == CostType.TOOL:
                    summary.tool_cost = total
                elif cost_type == CostType.MATERIAL:
                    summary.material_cost = total
                elif cost_type == CostType.MACHINE_TIME:
                    summary.machine_time_cost = total
                elif cost_type == CostType.LABOR:
                    summary.labor_cost = total
                elif cost_type == CostType.OVERHEAD:
                    summary.overhead_cost = total
                elif cost_type == CostType.MAINTENANCE:
                    summary.maintenance_cost = total
        
        # 计算机器时间（从机器时间成本反推）
        hourly_rate = self.get_parameter("machine_hourly_rate")
        if hourly_rate > 0 and summary.machine_time_cost > 0:
            summary.machining_time_minutes = (summary.machine_time_cost / hourly_rate) * 60
        
        summary.calculate_totals()
        
        return summary
    
    def record_machining_job(
        self,
        program_id: int,
        program_name: str,
        machining_time_minutes: float,
        parts_count: int,
        material_weight_kg: float = 0.0,
        material_price_per_kg: float = 0.0,
        tool_usage_records: List[Dict] = None
    ):
        """
        记录完整加工任务的成本
        
        Args:
            program_id: 程序 ID
            program_name: 程序名称
            machining_time_minutes: 加工时间（分钟）
            parts_count: 零件数量
            material_weight_kg: 材料重量（kg）
            material_price_per_kg: 材料单价（元/kg）
            tool_usage_records: 刀具使用记录列表
        """
        with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                # 1. 机器时间成本
                machine_rate = self.get_parameter("machine_hourly_rate")
                machine_cost = (machining_time_minutes / 60) * machine_rate
                conn.execute("""
                    INSERT INTO cost_records (
                        program_id, program_name, cost_type, category,
                        amount, unit, quantity, total, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    program_id,
                    program_name,
                    CostType.MACHINE_TIME,
                    CostCategory.VARIABLE,
                    machine_rate / 60,  # 元/分钟
                    "元/分钟",
                    machining_time_minutes,
                    machine_cost,
                    datetime.now().isoformat()
                ))
                
                # 2. 人工成本
                labor_rate = self.get_parameter("labor_hourly_rate")
                labor_cost = (machining_time_minutes / 60) * labor_rate
                conn.execute("""
                    INSERT INTO cost_records (
                        program_id, program_name, cost_type, category,
                        amount, unit, quantity, total, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    program_id,
                    program_name,
                    CostType.LABOR,
                    CostCategory.VARIABLE,
                    labor_rate / 60,
                    "元/分钟",
                    machining_time_minutes,
                    labor_cost,
                    datetime.now().isoformat()
                ))
                
                # 3. 材料成本
                if material_weight_kg > 0 and material_price_per_kg > 0:
                    waste_factor = self.get_parameter("material_waste_factor")
                    material_cost = material_weight_kg * material_price_per_kg * waste_factor
                    conn.execute("""
                        INSERT INTO cost_records (
                            program_id, program_name, cost_type, category,
                            amount, unit, quantity, total, created_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        program_id,
                        program_name,
                        CostType.MATERIAL,
                        CostCategory.VARIABLE,
                        material_price_per_kg,
                        "元/kg",
                        material_weight_kg * waste_factor,
                        material_cost,
                        datetime.now().isoformat()
                    ))
                
                # 4. 刀具成本
                if tool_usage_records:
                    total_tool_cost = 0.0
                    for tool_rec in tool_usage_records:
                        # 根据使用时长分摊刀具成本
                        duration = tool_rec.get("duration_minutes", 0)
                        tool_life = tool_rec.get("tool_life_minutes", self.default_params.default_tool_life_minutes)
                        tool_price = tool_rec.get("tool_price", 0.0)
                        
                        if tool_life > 0:
                            tool_cost = (duration / tool_life) * tool_price
                            total_tool_cost += tool_cost
                    
                    if total_tool_cost > 0:
                        conn.execute("""
                            INSERT INTO cost_records (
                                program_id, program_name, cost_type, category,
                                amount, unit, quantity, total, created_at
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            program_id,
                            program_name,
                            CostType.TOOL,
                            CostCategory.VARIABLE,
                            total_tool_cost,
                            "元",
                            1,
                            total_tool_cost,
                            datetime.now().isoformat()
                        ))
                
                # 5. 间接费用（基于直接成本）
                direct_cost = machine_cost + labor_cost
                if material_weight_kg > 0:
                    direct_cost += material_cost
                if tool_usage_records:
                    direct_cost += total_tool_cost
                
                overhead_rate = self.get_parameter("overhead_rate")
                overhead_cost = direct_cost * overhead_rate
                conn.execute("""
                    INSERT INTO cost_records (
                        program_id, program_name, cost_type, category,
                        amount, unit, quantity, total, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    program_id,
                    program_name,
                    CostType.OVERHEAD,
                    CostCategory.FIXED,
                    overhead_rate,
                    "比率",
                    direct_cost,
                    overhead_cost,
                    datetime.now().isoformat()
                ))
                
                conn.commit()
        
        logger.info(f"Machining job cost recorded: program={program_name}, parts={parts_count}")
    
    def get_cost_statistics(self, days: int = 30) -> Dict[str, Any]:
        """获取成本统计"""
        with sqlite3.connect(self.db_path) as conn:
            # 总成本
            cursor = conn.execute("""
                SELECT SUM(total) FROM cost_records
                WHERE date(created_at) >= date('now', ?)
            """, (f'-{days} days',))
            total_cost = cursor.fetchone()[0] or 0.0
            
            # 各类型成本
            cursor = conn.execute("""
                SELECT cost_type, SUM(total) as total
                FROM cost_records
                WHERE date(created_at) >= date('now', ?)
                GROUP BY cost_type
            """, (f'-{days} days',))
            cost_by_type = {row[0]: row[1] for row in cursor.fetchall()}
            
            # 平均单件成本
            cursor = conn.execute("""
                SELECT AVG(total) FROM cost_records
                WHERE cost_type = 'tool'
                AND date(created_at) >= date('now', ?)
            """, (f'-{days} days',))
            avg_tool_cost = cursor.fetchone()[0] or 0.0
            
            # 任务数量
            cursor = conn.execute("""
                SELECT COUNT(DISTINCT program_id) FROM cost_records
                WHERE date(created_at) >= date('now', ?)
            """, (f'-{days} days',))
            job_count = cursor.fetchone()[0] or 0
        
        return {
            "total_cost": round(total_cost, 2),
            "cost_by_type": cost_by_type,
            "tool_cost": round(cost_by_type.get("tool", 0), 2),
            "material_cost": round(cost_by_type.get("material", 0), 2),
            "machine_time_cost": round(cost_by_type.get("machine_time", 0), 2),
            "labor_cost": round(cost_by_type.get("labor", 0), 2),
            "overhead_cost": round(cost_by_type.get("overhead", 0), 2),
            "avg_tool_cost": round(avg_tool_cost, 2),
            "job_count": job_count,
            "period_days": days
        }
    
    def get_cost_trend(self, days: int = 30, group_by: str = "day") -> List[Dict[str, Any]]:
        """获取成本趋势"""
        if group_by == "day":
            format_str = "%Y-%m-%d"
        elif group_by == "week":
            format_str = "%Y-W%W"
        elif group_by == "month":
            format_str = "%Y-%m"
        else:
            format_str = "%Y-%m-%d"
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(f"""
                SELECT strftime('{format_str}', created_at) as period,
                       SUM(total) as total_cost,
                       COUNT(*) as record_count
                FROM cost_records
                WHERE date(created_at) >= date('now', ?)
                GROUP BY period
                ORDER BY period
            """, (f'-{days} days',))
            
            trend = []
            for row in cursor.fetchall():
                trend.append({
                    "period": row[0],
                    "total_cost": round(row[1], 2),
                    "record_count": row[2]
                })
        
        return trend
    
    def set_material_price(self, material_name: str, price_per_kg: float, supplier: str = None):
        """设置材料价格"""
        with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO material_prices 
                    (material_name, price_per_kg, supplier, updated_at)
                    VALUES (?, ?, ?, ?)
                """, (
                    material_name,
                    price_per_kg,
                    supplier,
                    datetime.now().isoformat()
                ))
                conn.commit()
        
        logger.info(f"Material price set: {material_name} = ¥{price_per_kg}/kg")
    
    def get_material_price(self, material_name: str) -> Optional[float]:
        """获取材料价格"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT price_per_kg FROM material_prices
                WHERE material_name = ?
                ORDER BY updated_at DESC LIMIT 1
            """, (material_name,))
            row = cursor.fetchone()
            return row[0] if row else None
    
    def list_material_prices(self) -> List[Dict[str, Any]]:
        """列出材料价格"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT material_name, price_per_kg, supplier, updated_at
                FROM material_prices
                ORDER BY material_name
            """)
            
            return [
                {
                    "material_name": row[0],
                    "price_per_kg": row[1],
                    "supplier": row[2],
                    "updated_at": row[3]
                }
                for row in cursor.fetchall()
            ]


# 便捷函数
def get_cost_accounting_manager(db_path: str = None) -> CostAccountingManager:
    """获取成本核算管理器实例"""
    return CostAccountingManager(db_path)


# CLI 测试
if __name__ == "__main__":
    print("=" * 60)
    print("成本核算模块测试")
    print("=" * 60)
    
    manager = CostAccountingManager()
    
    # 设置成本参数
    print("\n设置成本参数...")
    manager.set_parameter("machine_hourly_rate", 150.0, "机器小时费率")
    manager.set_parameter("labor_hourly_rate", 80.0, "人工小时费率")
    print("  机器费率：¥150/小时")
    print("  人工费率：¥80/小时")
    
    # 设置材料价格
    print("\n设置材料价格...")
    manager.set_material_price("45#钢", 8.5, "宝钢")
    manager.set_material_price("铝合金", 25.0, "西南铝")
    print("  45#钢：¥8.5/kg")
    print("  铝合金：¥25.0/kg")
    
    # 记录加工任务
    print("\n记录加工任务成本...")
    manager.record_machining_job(
        program_id=1,
        program_name="TEST_PART_001",
        machining_time_minutes=45.5,
        parts_count=10,
        material_weight_kg=2.5,
        material_price_per_kg=8.5,
        tool_usage_records=[
            {"duration_minutes": 30, "tool_life_minutes": 600, "tool_price": 350.0},
            {"duration_minutes": 15, "tool_life_minutes": 400, "tool_price": 280.0}
        ]
    )
    print("  程序：TEST_PART_001")
    print("  加工时间：45.5 分钟")
    print("  零件数：10 个")
    
    # 计算成本
    print("\n成本汇总:")
    summary = manager.calculate_job_cost(program_id=1, program_name="TEST_PART_001")
    print(f"  机器时间成本：¥{summary.machine_time_cost:.2f}")
    print(f"  人工成本：¥{summary.labor_cost:.2f}")
    print(f"  材料成本：¥{summary.material_cost:.2f}")
    print(f"  刀具成本：¥{summary.tool_cost:.2f}")
    print(f"  间接费用：¥{summary.overhead_cost:.2f}")
    print(f"  ---")
    print(f"  总成本：¥{summary.total_cost:.2f}")
    print(f"  单件成本：¥{summary.cost_per_part:.2f}")
    
    # 查看统计
    print("\n成本统计 (最近 30 天):")
    stats = manager.get_cost_statistics(days=30)
    print(f"  总成本：¥{stats['total_cost']}")
    print(f"  任务数：{stats['job_count']}")
    print(f"  机器时间成本：¥{stats['machine_time_cost']}")
    print(f"  刀具成本：¥{stats['tool_cost']}")
    
    print("\n测试完成!")
