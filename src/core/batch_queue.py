"""
批量处理队列模块 - Batch Processing Queue

企业级任务队列管理，支持：
- 优先级调度
- 并发控制
- 进度跟踪
- 失败重试
- 批量导出
"""

import json
import sqlite3
import threading
import time
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


class TaskStatus(str, Enum):
    """任务状态枚举"""
    PENDING = "pending"      # 等待中
    QUEUED = "queued"        # 已入队
    RUNNING = "running"      # 运行中
    COMPLETED = "completed"  # 已完成
    FAILED = "failed"        # 失败
    CANCELLED = "cancelled"  # 已取消
    RETRYING = "retrying"    # 重试中


class TaskPriority(int, Enum):
    """任务优先级枚举 (数字越小优先级越高)"""
    CRITICAL = 0    # 紧急
    HIGH = 1        # 高
    NORMAL = 2      # 普通
    LOW = 3         # 低


@dataclass
class Task:
    """任务数据类"""
    id: Optional[int] = None
    task_type: str = ""           # 任务类型：dxf_to_gcode, batch_export, etc.
    priority: int = TaskPriority.NORMAL
    status: str = TaskStatus.PENDING
    payload: Dict[str, Any] = None  # 任务参数
    result: Optional[Dict[str, Any]] = None  # 执行结果
    error_message: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3
    progress: float = 0.0         # 0-100
    created_at: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    worker_id: Optional[str] = None
    
    def __post_init__(self):
        if self.payload is None:
            self.payload = {}
        if self.created_at is None:
            self.created_at = datetime.now().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Task':
        """从字典创建"""
        return cls(**data)


class BatchQueue:
    """批量处理队列管理器"""
    
    def __init__(self, db_path: str = None):
        """
        初始化队列
        
        Args:
            db_path: SQLite 数据库路径，默认使用项目 data 目录
        """
        if db_path is None:
            db_path = Path(__file__).parent.parent / "data" / "batch_queue.db"
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        
        self.db_path = str(db_path)
        self._lock = threading.Lock()
        self._workers: Dict[str, bool] = {}  # worker_id -> is_running
        self._handlers: Dict[str, Callable] = {}  # task_type -> handler function
        
        self._init_database()
        logger.info(f"BatchQueue initialized with database: {self.db_path}")
    
    def _init_database(self):
        """初始化数据库表"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_type TEXT NOT NULL,
                    priority INTEGER DEFAULT 2,
                    status TEXT DEFAULT 'pending',
                    payload TEXT,
                    result TEXT,
                    error_message TEXT,
                    retry_count INTEGER DEFAULT 0,
                    max_retries INTEGER DEFAULT 3,
                    progress REAL DEFAULT 0.0,
                    created_at TEXT,
                    started_at TEXT,
                    completed_at TEXT,
                    worker_id TEXT
                )
            """)
            
            # 创建索引（单独语句）
            conn.execute("CREATE INDEX IF NOT EXISTS idx_status ON tasks(status)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_priority ON tasks(priority)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_type ON tasks(task_type)")
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS queue_stats (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    metric_name TEXT NOT NULL,
                    metric_value REAL NOT NULL,
                    timestamp TEXT NOT NULL,
                    tags TEXT
                )
            """)
            
            conn.commit()
        logger.info("Database tables initialized")
    
    def submit_task(
        self,
        task_type: str,
        payload: Dict[str, Any],
        priority: int = TaskPriority.NORMAL,
        max_retries: int = 3
    ) -> int:
        """
        提交任务到队列
        
        Args:
            task_type: 任务类型
            payload: 任务参数
            priority: 优先级
            max_retries: 最大重试次数
            
        Returns:
            任务 ID
        """
        task = Task(
            task_type=task_type,
            payload=payload,
            priority=priority,
            max_retries=max_retries,
            status=TaskStatus.QUEUED
        )
        
        with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    INSERT INTO tasks (
                        task_type, priority, status, payload, 
                        max_retries, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    task.task_type,
                    task.priority,
                    task.status,
                    json.dumps(task.payload),
                    task.max_retries,
                    task.created_at
                ))
                task.id = cursor.lastrowid
                conn.commit()
        
        logger.info(f"Task submitted: id={task.id}, type={task_type}, priority={priority}")
        self._record_metric("tasks_submitted", 1, {"task_type": task_type})
        return task.id
    
    def get_next_task(self, worker_id: str = None) -> Optional[Task]:
        """
        获取下一个待处理的任务（按优先级排序）
        
        Args:
            worker_id: 工作者 ID
            
        Returns:
            任务对象，如果没有可用任务则返回 None
        """
        with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT id, task_type, priority, status, payload, result,
                           error_message, retry_count, max_retries, progress,
                           created_at, started_at, completed_at, worker_id
                    FROM tasks
                    WHERE status IN ('queued', 'retrying')
                    ORDER BY priority ASC, created_at ASC
                    LIMIT 1
                """)
                
                row = cursor.fetchone()
                if not row:
                    return None
                
                task = Task(
                    id=row[0],
                    task_type=row[1],
                    priority=row[2],
                    status=row[3],
                    payload=json.loads(row[4]) if row[4] else {},
                    result=json.loads(row[5]) if row[5] else None,
                    error_message=row[6],
                    retry_count=row[7],
                    max_retries=row[8],
                    progress=row[9],
                    created_at=row[10],
                    started_at=row[11],
                    completed_at=row[12],
                    worker_id=row[13]
                )
                
                # 标记为运行中
                conn.execute("""
                    UPDATE tasks 
                    SET status = ?, started_at = ?, worker_id = ?
                    WHERE id = ?
                """, (TaskStatus.RUNNING, datetime.now().isoformat(), worker_id, task.id))
                conn.commit()
        
        logger.info(f"Task retrieved: id={task.id}, type={task.task_type}")
        return task
    
    def complete_task(self, task_id: int, result: Dict[str, Any] = None):
        """
        标记任务为完成
        
        Args:
            task_id: 任务 ID
            result: 任务结果
        """
        with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    UPDATE tasks 
                    SET status = ?, result = ?, progress = 100.0, completed_at = ?
                    WHERE id = ?
                """, (
                    TaskStatus.COMPLETED,
                    json.dumps(result) if result else None,
                    datetime.now().isoformat(),
                    task_id
                ))
                conn.commit()
        
        logger.info(f"Task completed: id={task_id}")
        self._record_metric("tasks_completed", 1, {"success": "true"})
    
    def fail_task(self, task_id: int, error_message: str, should_retry: bool = True):
        """
        标记任务为失败
        
        Args:
            task_id: 任务 ID
            error_message: 错误信息
            should_retry: 是否重试
        """
        with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    "SELECT retry_count, max_retries FROM tasks WHERE id = ?",
                    (task_id,)
                )
                row = cursor.fetchone()
                
                if not row:
                    return
                
                retry_count, max_retries = row
                
                if should_retry and retry_count < max_retries:
                    new_status = TaskStatus.RETRYING
                    new_retry_count = retry_count + 1
                    logger.info(f"Task will retry: id={task_id}, attempt={new_retry_count}/{max_retries}")
                else:
                    new_status = TaskStatus.FAILED
                    new_retry_count = retry_count
                    logger.error(f"Task failed permanently: id={task_id}, error={error_message}")
                
                conn.execute("""
                    UPDATE tasks 
                    SET status = ?, error_message = ?, retry_count = ?, 
                        completed_at = ?
                    WHERE id = ?
                """, (
                    new_status,
                    error_message,
                    new_retry_count,
                    datetime.now().isoformat() if new_status == TaskStatus.FAILED else None,
                    task_id
                ))
                
                # 如果需要重试，重新加入队列
                if new_status == TaskStatus.RETRYING:
                    conn.execute("""
                        UPDATE tasks SET status = 'queued' WHERE id = ?
                    """, (task_id,))
                
                conn.commit()
        
        self._record_metric("tasks_failed", 1, {"retry": str(should_retry)})
    
    def update_progress(self, task_id: int, progress: float, metadata: Dict[str, Any] = None):
        """
        更新任务进度
        
        Args:
            task_id: 任务 ID
            progress: 进度 (0-100)
            metadata: 附加元数据
        """
        with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                if metadata:
                    # 将元数据添加到结果的临时字段
                    conn.execute("""
                        UPDATE tasks 
                        SET progress = ?, result = ?
                        WHERE id = ?
                    """, (
                        progress,
                        json.dumps({"_progress_metadata": metadata}),
                        task_id
                    ))
                else:
                    conn.execute("""
                        UPDATE tasks SET progress = ? WHERE id = ?
                    """, (progress, task_id))
                conn.commit()
    
    def cancel_task(self, task_id: int) -> bool:
        """
        取消任务
        
        Args:
            task_id: 任务 ID
            
        Returns:
            是否成功取消
        """
        with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    UPDATE tasks 
                    SET status = ?, completed_at = ?
                    WHERE id = ? AND status IN ('pending', 'queued', 'running')
                """, (TaskStatus.CANCELLED, datetime.now().isoformat(), task_id))
                conn.commit()
                success = cursor.rowcount > 0
        
        if success:
            logger.info(f"Task cancelled: id={task_id}")
            self._record_metric("tasks_cancelled", 1)
        
        return success
    
    def get_task(self, task_id: int) -> Optional[Task]:
        """
        获取任务详情
        
        Args:
            task_id: 任务 ID
            
        Returns:
            任务对象
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT id, task_type, priority, status, payload, result,
                       error_message, retry_count, max_retries, progress,
                       created_at, started_at, completed_at, worker_id
                FROM tasks
                WHERE id = ?
            """, (task_id,))
            
            row = cursor.fetchone()
            if not row:
                return None
            
            return Task(
                id=row[0],
                task_type=row[1],
                priority=row[2],
                status=row[3],
                payload=json.loads(row[4]) if row[4] else {},
                result=json.loads(row[5]) if row[5] else None,
                error_message=row[6],
                retry_count=row[7],
                max_retries=row[8],
                progress=row[9],
                created_at=row[10],
                started_at=row[11],
                completed_at=row[12],
                worker_id=row[13]
            )
    
    def get_queue_status(self) -> Dict[str, Any]:
        """
        获取队列状态统计
        
        Returns:
            队列统计信息
        """
        with sqlite3.connect(self.db_path) as conn:
            # 各状态任务数
            cursor = conn.execute("""
                SELECT status, COUNT(*) as count
                FROM tasks
                GROUP BY status
            """)
            status_counts = {row[0]: row[1] for row in cursor.fetchall()}
            
            # 总任务数
            cursor = conn.execute("SELECT COUNT(*) FROM tasks")
            total = cursor.fetchone()[0]
            
            # 平均等待时间
            cursor = conn.execute("""
                SELECT AVG(
                    CAST(strftime('%s', started_at) AS INTEGER) - 
                    CAST(strftime('%s', created_at) AS INTEGER)
                )
                FROM tasks
                WHERE started_at IS NOT NULL
            """)
            avg_wait_time = cursor.fetchone()[0] or 0
            
            # 平均处理时间
            cursor = conn.execute("""
                SELECT AVG(
                    CAST(strftime('%s', completed_at) AS INTEGER) - 
                    CAST(strftime('%s', started_at) AS INTEGER)
                )
                FROM tasks
                WHERE completed_at IS NOT NULL AND started_at IS NOT NULL
            """)
            avg_process_time = cursor.fetchone()[0] or 0
        
        return {
            "total_tasks": total,
            "status_breakdown": status_counts,
            "pending": status_counts.get("pending", 0) + status_counts.get("queued", 0),
            "running": status_counts.get("running", 0),
            "completed": status_counts.get("completed", 0),
            "failed": status_counts.get("failed", 0),
            "avg_wait_time_seconds": round(avg_wait_time, 2),
            "avg_process_time_seconds": round(avg_process_time, 2)
        }
    
    def list_tasks(
        self,
        status: str = None,
        task_type: str = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Task]:
        """
        列出任务
        
        Args:
            status: 筛选状态
            task_type: 筛选类型
            limit: 返回数量限制
            offset: 偏移量
            
        Returns:
            任务列表
        """
        query = """
            SELECT id, task_type, priority, status, payload, result,
                   error_message, retry_count, max_retries, progress,
                   created_at, started_at, completed_at, worker_id
            FROM tasks
            WHERE 1=1
        """
        params = []
        
        if status:
            query += " AND status = ?"
            params.append(status)
        
        if task_type:
            query += " AND task_type = ?"
            params.append(task_type)
        
        query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(query, params)
            tasks = []
            for row in cursor.fetchall():
                tasks.append(Task(
                    id=row[0],
                    task_type=row[1],
                    priority=row[2],
                    status=row[3],
                    payload=json.loads(row[4]) if row[4] else {},
                    result=json.loads(row[5]) if row[5] else None,
                    error_message=row[6],
                    retry_count=row[7],
                    max_retries=row[8],
                    progress=row[9],
                    created_at=row[10],
                    started_at=row[11],
                    completed_at=row[12],
                    worker_id=row[13]
                ))
        
        return tasks
    
    def clear_completed(self, older_than_days: int = 7) -> int:
        """
        清理已完成的历史任务
        
        Args:
            older_than_days: 清理多少天之前的任务
            
        Returns:
            清理的任务数
        """
        with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    DELETE FROM tasks
                    WHERE status IN ('completed', 'cancelled')
                    AND date(completed_at) < date('now', ?)
                """, (f'-{older_than_days} days',))
                count = cursor.rowcount
                conn.commit()
        
        logger.info(f"Cleared {count} completed tasks older than {older_than_days} days")
        return count
    
    def register_handler(self, task_type: str, handler: Callable[[Dict[str, Any]], Dict[str, Any]]):
        """
        注册任务处理器
        
        Args:
            task_type: 任务类型
            handler: 处理函数，接收 payload，返回 result
        """
        self._handlers[task_type] = handler
        logger.info(f"Handler registered for task type: {task_type}")
    
    def start_worker(self, worker_id: str = None, poll_interval: float = 1.0) -> str:
        """
        启动工作线程
        
        Args:
            worker_id: 工作者 ID，自动生成如果未提供
            poll_interval: 轮询间隔（秒）
            
        Returns:
            工作者 ID
        """
        if worker_id is None:
            worker_id = f"worker_{datetime.now().strftime('%Y%m%d%H%M%S')}_{id(self)}"
        
        self._workers[worker_id] = True
        
        def worker_loop():
            logger.info(f"Worker started: {worker_id}")
            while self._workers.get(worker_id, False):
                task = self.get_next_task(worker_id)
                
                if not task:
                    time.sleep(poll_interval)
                    continue
                
                # 查找处理器
                handler = self._handlers.get(task.task_type)
                if not handler:
                    self.fail_task(task.id, f"No handler for task type: {task.task_type}", should_retry=False)
                    continue
                
                try:
                    # 执行任务
                    result = handler(task.payload)
                    self.complete_task(task.id, result)
                except Exception as e:
                    error_msg = str(e)
                    logger.exception(f"Task execution failed: id={task.id}, error={error_msg}")
                    self.fail_task(task.id, error_msg, should_retry=True)
        
        # 在后台线程运行
        thread = threading.Thread(target=worker_loop, daemon=True)
        thread.start()
        
        return worker_id
    
    def stop_worker(self, worker_id: str):
        """停止工作线程"""
        self._workers[worker_id] = False
        logger.info(f"Worker stopped: {worker_id}")
    
    def _record_metric(self, metric_name: str, metric_value: float, tags: Dict[str, str] = None):
        """记录性能指标"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO queue_stats (metric_name, metric_value, timestamp, tags)
                VALUES (?, ?, ?, ?)
            """, (
                metric_name,
                metric_value,
                datetime.now().isoformat(),
                json.dumps(tags) if tags else None
            ))
            conn.commit()
    
    def get_metrics(self, hours: int = 24) -> Dict[str, Any]:
        """
        获取最近的性能指标
        
        Args:
            hours: 查询最近多少小时
            
        Returns:
            指标统计
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT metric_name, SUM(metric_value) as total, COUNT(*) as count
                FROM queue_stats
                WHERE timestamp >= datetime('now', ?)
                GROUP BY metric_name
            """, (f'-{hours} hours',))
            
            metrics = {}
            for row in cursor.fetchall():
                metrics[row[0]] = {
                    "total": row[1],
                    "count": row[2],
                    "avg": round(row[1] / row[2], 2) if row[2] > 0 else 0
                }
        
        return metrics


# 便捷函数
def create_batch_queue(db_path: str = None) -> BatchQueue:
    """创建批量队列实例"""
    return BatchQueue(db_path)


# CLI 测试
if __name__ == "__main__":
    import sys
    
    print("=" * 60)
    print("批量处理队列测试")
    print("=" * 60)
    
    queue = BatchQueue()
    
    # 注册一个简单的处理器
    def sample_handler(payload: Dict[str, Any]) -> Dict[str, Any]:
        print(f"Processing task: {payload}")
        time.sleep(0.5)  # 模拟处理
        return {"processed": True, "data": payload}
    
    queue.register_handler("test_task", sample_handler)
    
    # 提交几个测试任务
    print("\n提交测试任务...")
    task_ids = []
    for i in range(5):
        task_id = queue.submit_task(
            task_type="test_task",
            payload={"index": i, "data": f"test_data_{i}"},
            priority=i % 4  # 不同优先级
        )
        task_ids.append(task_id)
        print(f"  提交任务 {task_id}")
    
    # 启动工作线程
    print("\n启动工作线程...")
    worker_id = queue.start_worker(poll_interval=0.1)
    
    # 等待任务完成
    print("等待任务处理...")
    time.sleep(3)
    
    # 查看状态
    print("\n队列状态:")
    status = queue.get_queue_status()
    print(f"  总任务数：{status['total_tasks']}")
    print(f"  已完成：{status['completed']}")
    print(f"  平均处理时间：{status['avg_process_time_seconds']}s")
    
    # 查看任务列表
    print("\n任务列表:")
    tasks = queue.list_tasks(limit=10)
    for task in tasks:
        print(f"  [{task.id}] {task.task_type} - {task.status} ({task.progress}%)")
    
    # 停止工作线程
    queue.stop_worker(worker_id)
    
    print("\n测试完成!")
