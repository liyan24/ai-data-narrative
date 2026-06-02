"""
自动化调度 — 定时任务运行、数据监控、批量处理

使用方式:
    from src.automation.scheduler import TaskScheduler, DataWatcher
    
    scheduler = TaskScheduler()
    scheduler.schedule_daily(hour=9, task=analyze_task)
"""

from typing import Dict, List, Any, Optional, Callable, Tuple
from dataclasses import dataclass, field
from pathlib import Path
from datetime import datetime, timedelta
import time
import threading
import json


@dataclass
class ScheduledTask:
    """定时任务"""
    name: str
    task: Callable
    schedule: str  # "daily", "hourly", "interval", "once"
    params: Dict[str, Any] = field(default_factory=dict)
    next_run: Optional[datetime] = None
    last_run: Optional[datetime] = None
    last_result: Optional[Any] = None
    enabled: bool = True
    run_count: int = 0


class TaskScheduler:
    """任务调度器 — 支持定时和周期性任务"""
    
    def __init__(self, state_file: Optional[Path] = None):
        self.tasks: Dict[str, ScheduledTask] = {}
        self.state_file = state_file
        self._running = False
        self._thread = None
        self._lock = threading.Lock()
        
        if state_file and state_file.exists():
            self._load_state()
    
    def schedule_daily(self, hour: int, minute: int = 0,
                       task: Callable = None, name: str = None,
                       **kwargs) -> str:
        """安排每日任务"""
        task_name = name or f"daily_{hour:02d}{minute:02d}"
        
        # 计算下次运行时间
        now = datetime.now()
        next_run = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if next_run <= now:
            next_run += timedelta(days=1)
        
        self.tasks[task_name] = ScheduledTask(
            name=task_name,
            task=task,
            schedule="daily",
            params={"hour": hour, "minute": minute, **kwargs},
            next_run=next_run
        )
        
        return task_name
    
    def schedule_interval(self, minutes: int,
                          task: Callable = None, name: str = None,
                          **kwargs) -> str:
        """安排间隔任务"""
        task_name = name or f"interval_{minutes}m"
        
        self.tasks[task_name] = ScheduledTask(
            name=task_name,
            task=task,
            schedule="interval",
            params={"minutes": minutes, **kwargs},
            next_run=datetime.now() + timedelta(minutes=minutes)
        )
        
        return task_name
    
    def schedule_once(self, run_time: datetime,
                      task: Callable = None, name: str = None,
                      **kwargs) -> str:
        """安排一次性任务"""
        task_name = name or f"once_{run_time.strftime('%Y%m%d_%H%M')}"
        
        self.tasks[task_name] = ScheduledTask(
            name=task_name,
            task=task,
            schedule="once",
            params=kwargs,
            next_run=run_time
        )
        
        return task_name
    
    def run_task(self, task_name: str) -> Any:
        """立即运行任务"""
        task = self.tasks.get(task_name)
        if not task or not task.task:
            return None
        
        with self._lock:
            task.last_run = datetime.now()
            task.run_count += 1
            
            try:
                # 过滤调度参数，只传递用户自定义参数
                reserved_keys = {"hour", "minute", "minutes", "schedule"}
                task_params = {k: v for k, v in task.params.items() if k not in reserved_keys}
                result = task.task(**task_params)
                task.last_result = result
                
                # 更新下次运行时间
                if task.schedule == "daily":
                    task.next_run = datetime.now() + timedelta(days=1)
                elif task.schedule == "interval":
                    task.next_run = datetime.now() + timedelta(
                        minutes=task.params.get("minutes", 60)
                    )
                elif task.schedule == "once":
                    task.enabled = False
                    task.next_run = None
                
                self._save_state()
                return result
                
            except Exception as e:
                task.last_result = {"error": str(e)}
                self._save_state()
                raise
    
    def check_and_run(self) -> List[Tuple[str, Any]]:
        """检查并运行到期的任务"""
        results = []
        now = datetime.now()
        
        for task_name, task in self.tasks.items():
            if not task.enabled or not task.next_run:
                continue
            
            if task.next_run <= now:
                try:
                    result = self.run_task(task_name)
                    results.append((task_name, result))
                except Exception as e:
                    results.append((task_name, {"error": str(e)}))
        
        return results
    
    def start(self, check_interval: int = 60):
        """启动后台调度"""
        self._running = True
        self._thread = threading.Thread(target=self._loop, 
                                        args=(check_interval,))
        self._thread.daemon = True
        self._thread.start()
    
    def stop(self):
        """停止调度"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
    
    def _loop(self, check_interval: int):
        """调度循环"""
        while self._running:
            self.check_and_run()
            time.sleep(check_interval)
    
    def list_tasks(self) -> List[Dict[str, Any]]:
        """列出所有任务"""
        return [
            {
                "name": t.name,
                "schedule": t.schedule,
                "next_run": t.next_run.strftime("%Y-%m-%d %H:%M") if t.next_run else None,
                "last_run": t.last_run.strftime("%Y-%m-%d %H:%M") if t.last_run else None,
                "run_count": t.run_count,
                "enabled": t.enabled
            }
            for t in self.tasks.values()
        ]
    
    def _save_state(self):
        """保存状态"""
        if not self.state_file:
            return
        
        state = {
            "saved_at": datetime.now().isoformat(),
            "tasks": {
                name: {
                    "schedule": t.schedule,
                    "params": t.params,
                    "next_run": t.next_run.isoformat() if t.next_run else None,
                    "last_run": t.last_run.isoformat() if t.last_run else None,
                    "run_count": t.run_count,
                    "enabled": t.enabled
                }
                for name, t in self.tasks.items()
            }
        }
        
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.state_file, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
    
    def _load_state(self):
        """加载状态"""
        try:
            with open(self.state_file, "r", encoding="utf-8") as f:
                state = json.load(f)
            
            for name, data in state.get("tasks", {}).items():
                next_run = datetime.fromisoformat(data["next_run"]) if data.get("next_run") else None
                last_run = datetime.fromisoformat(data["last_run"]) if data.get("last_run") else None
                
                self.tasks[name] = ScheduledTask(
                    name=name,
                    task=None,  # 需要在运行时重新注册
                    schedule=data["schedule"],
                    params=data.get("params", {}),
                    next_run=next_run,
                    last_run=last_run,
                    run_count=data.get("run_count", 0),
                    enabled=data.get("enabled", True)
                )
        except Exception:
            pass


class DataWatcher:
    """数据文件监控器 — 检测新文件/修改并触发分析"""
    
    def __init__(self, watch_dir: Path, pattern: str = "*.csv"):
        self.watch_dir = Path(watch_dir)
        self.pattern = pattern
        self._known_files: Dict[str, float] = {}
        self._callbacks: List[Callable] = []
    
    def add_callback(self, callback: Callable):
        """添加回调函数"""
        self._callbacks.append(callback)
    
    def scan(self) -> List[Dict[str, Any]]:
        """
        扫描目录，返回新文件或修改的文件
        
        Returns:
            [{"file": str, "status": "new" | "modified", "mtime": float}, ...]
        """
        changes = []
        current_files = {}
        
        for file_path in self.watch_dir.glob(self.pattern):
            if not file_path.is_file():
                continue
            
            mtime = file_path.stat().st_mtime
            file_key = str(file_path)
            current_files[file_key] = mtime
            
            if file_key not in self._known_files:
                changes.append({
                    "file": file_key,
                    "status": "new",
                    "mtime": mtime
                })
            elif mtime > self._known_files[file_key]:
                changes.append({
                    "file": file_key,
                    "status": "modified",
                    "mtime": mtime
                })
        
        # 更新已知文件列表
        self._known_files = current_files
        
        # 触发回调
        for change in changes:
            for callback in self._callbacks:
                try:
                    callback(change)
                except Exception:
                    pass
        
        return changes
    
    def watch(self, interval: int = 300, callback: Callable = None):
        """持续监控（阻塞）"""
        if callback:
            self.add_callback(callback)
        
        print(f"[WATCH] 开始监控 {self.watch_dir} (间隔 {interval}s)")
        
        try:
            while True:
                changes = self.scan()
                if changes:
                    for change in changes:
                        print(f"[WATCH] {change['status']}: {change['file']}")
                time.sleep(interval)
        except KeyboardInterrupt:
            print("[WATCH] 监控已停止")


class BatchProcessor:
    """批量处理器 — 处理多个数据文件"""
    
    def __init__(self, pipeline_factory: Callable):
        self.pipeline_factory = pipeline_factory
        self.results: List[Dict[str, Any]] = []
    
    def process_directory(self, data_dir: Path, pattern: str = "*.csv",
                          **pipeline_kwargs) -> List[Dict[str, Any]]:
        """批量处理目录中的数据文件"""
        data_dir = Path(data_dir)
        files = list(data_dir.glob(pattern))
        
        print(f"[BATCH] 发现 {len(files)} 个文件，开始处理...")
        
        for i, file_path in enumerate(files, 1):
            print(f"[BATCH] 处理 [{i}/{len(files)}]: {file_path.name}")
            
            try:
                pipeline = self.pipeline_factory()
                result = pipeline.run(str(file_path), **pipeline_kwargs)
                
                self.results.append({
                    "file": str(file_path),
                    "status": "success",
                    "result": result
                })
                
            except Exception as e:
                self.results.append({
                    "file": str(file_path),
                    "status": "error",
                    "error": str(e)
                })
        
        # 统计
        success_count = sum(1 for r in self.results if r["status"] == "success")
        error_count = len(self.results) - success_count
        
        print(f"[BATCH] 完成: {success_count} 成功, {error_count} 失败")
        
        return self.results
    
    def get_summary(self) -> Dict[str, Any]:
        """获取批量处理摘要"""
        success = [r for r in self.results if r["status"] == "success"]
        errors = [r for r in self.results if r["status"] == "error"]
        
        return {
            "total": len(self.results),
            "success": len(success),
            "errors": len(errors),
            "error_files": [r["file"] for r in errors],
            "success_files": [r["file"] for r in success]
        }


class AutomationManager:
    """自动化管理器 — 统一调度任务、监控和批量处理"""
    
    def __init__(self, config_dir: Path = None):
        self.config_dir = config_dir or Path("./automation")
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        self.scheduler = TaskScheduler(self.config_dir / "scheduler_state.json")
        self.watcher = None
        self.batch = None
    
    def setup_data_watch(self, watch_dir: Path, pattern: str = "*.csv",
                         pipeline_factory: Callable = None):
        """设置数据监控"""
        self.watcher = DataWatcher(watch_dir, pattern)
        
        if pipeline_factory:
            def on_new_file(change):
                print(f"[AUTO] 新文件触发分析: {change['file']}")
                try:
                    pipeline = pipeline_factory()
                    pipeline.run(change["file"])
                except Exception as e:
                    print(f"[AUTO] 分析失败: {e}")
            
            self.watcher.add_callback(on_new_file)
    
    def setup_batch_schedule(self, data_dir: Path, pattern: str = "*.csv",
                             schedule: str = "daily", hour: int = 9,
                             pipeline_factory: Callable = None):
        """设置定时批量处理"""
        def batch_task(**kwargs):
            batch = BatchProcessor(pipeline_factory)
            return batch.process_directory(data_dir, pattern, **kwargs)
        
        if schedule == "daily":
            return self.scheduler.schedule_daily(
                hour=hour, 
                task=batch_task,
                name="daily_batch_process"
            )
        elif schedule == "interval":
            return self.scheduler.schedule_interval(
                minutes=kwargs.get("minutes", 60),
                task=batch_task,
                name="interval_batch_process"
            )
    
    def start(self):
        """启动所有自动化服务"""
        self.scheduler.start()
        print("[AUTO] 自动化调度已启动")
    
    def stop(self):
        """停止所有自动化服务"""
        self.scheduler.stop()
        print("[AUTO] 自动化调度已停止")
    
    def get_status(self) -> Dict[str, Any]:
        """获取自动化状态"""
        return {
            "scheduler_tasks": self.scheduler.list_tasks(),
            "watcher_dir": str(self.watcher.watch_dir) if self.watcher else None,
            "watcher_pattern": self.watcher.pattern if self.watcher else None
        }
