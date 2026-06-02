"""
监控与日志系统 — 性能监控、日志记录、健康检查

使用方式:
    from src.monitoring.logger import PipelineLogger, PerformanceMonitor
    
    logger = PipelineLogger()
    logger.info("开始处理")
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from pathlib import Path
from datetime import datetime, timedelta
import time
import json
import logging
import sys
from contextlib import contextmanager


@dataclass
class PipelineEvent:
    """流水线事件"""
    timestamp: datetime
    level: str  # "info", "warning", "error", "success"
    step: str
    message: str
    duration_ms: Optional[float] = None
    details: Dict[str, Any] = field(default_factory=dict)


class PipelineLogger:
    """流水线日志记录器 — 结构化日志"""
    
    LEVELS = {"debug": 0, "info": 1, "warning": 2, "error": 3, "success": 4}
    
    def __init__(self, log_dir: Optional[Path] = None, 
                 log_level: str = "info",
                 console_output: bool = True):
        self.log_dir = Path(log_dir) if log_dir else Path("./logs")
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.log_level = self.LEVELS.get(log_level, 1)
        self.console_output = console_output
        self.events: List[PipelineEvent] = []
        
        # 设置 Python 日志
        self._setup_logging()
    
    def _setup_logging(self):
        """配置 Python 日志"""
        log_file = self.log_dir / f"pipeline_{datetime.now().strftime('%Y%m%d')}.log"
        
        logging.basicConfig(
            level=logging.DEBUG,
            format="%(asctime)s [%(levelname)s] %(message)s",
            handlers=[
                logging.FileHandler(log_file, encoding="utf-8"),
                logging.StreamHandler(sys.stdout) if self.console_output else logging.NullHandler()
            ]
        )
        
        self.logger = logging.getLogger("DataNarrative")
    
    def _log(self, level: str, step: str, message: str, 
             duration_ms: float = None, **details):
        """内部日志方法"""
        if self.LEVELS.get(level, 1) < self.log_level:
            return
        
        event = PipelineEvent(
            timestamp=datetime.now(),
            level=level,
            step=step,
            message=message,
            duration_ms=duration_ms,
            details=details
        )
        self.events.append(event)
        
        # 写入 Python 日志
        log_msg = f"[{step}] {message}"
        if duration_ms is not None:
            log_msg += f" ({duration_ms:.1f}ms)"
        if details:
            log_msg += f" {json.dumps(details, ensure_ascii=False, default=str)}"
        
        if level == "debug":
            self.logger.debug(log_msg)
        elif level == "info":
            self.logger.info(log_msg)
        elif level == "warning":
            self.logger.warning(log_msg)
        elif level == "error":
            self.logger.error(log_msg)
        elif level == "success":
            self.logger.info(f"[OK] {log_msg}")
    
    def debug(self, step: str, message: str, **details):
        self._log("debug", step, message, **details)
    
    def info(self, step: str, message: str, **details):
        self._log("info", step, message, **details)
    
    def warning(self, step: str, message: str, **details):
        self._log("warning", step, message, **details)
    
    def error(self, step: str, message: str, **details):
        self._log("error", step, message, **details)
    
    def success(self, step: str, message: str, duration_ms: float = None, **details):
        self._log("success", step, message, duration_ms, **details)
    
    @contextmanager
    def timed(self, step: str, message: str = None):
        """计时上下文管理器"""
        start = time.time()
        self.info(step, message or f"开始 {step}")
        try:
            yield self
            duration = (time.time() - start) * 1000
            self.success(step, f"完成 {step}", duration_ms=duration)
        except Exception as e:
            duration = (time.time() - start) * 1000
            self.error(step, f"失败 {step}: {str(e)}", duration_ms=duration)
            raise
    
    def get_events(self, level: str = None, step: str = None) -> List[PipelineEvent]:
        """获取事件列表"""
        events = self.events
        if level:
            events = [e for e in events if e.level == level]
        if step:
            events = [e for e in events if e.step == step]
        return events
    
    def get_summary(self) -> Dict[str, Any]:
        """获取日志摘要"""
        total = len(self.events)
        errors = len([e for e in self.events if e.level == "error"])
        warnings = len([e for e in self.events if e.level == "warning"])
        
        # 计算各步骤耗时
        step_times = {}
        for e in self.events:
            if e.duration_ms is not None:
                step_times[e.step] = step_times.get(e.step, 0) + e.duration_ms
        
        return {
            "total_events": total,
            "errors": errors,
            "warnings": warnings,
            "success_rate": (total - errors) / total * 100 if total > 0 else 0,
            "step_times_ms": step_times,
            "total_duration_ms": sum(step_times.values())
        }
    
    def save_json(self, filepath: Optional[Path] = None) -> Path:
        """保存日志为 JSON"""
        filepath = filepath or self.log_dir / f"events_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        data = [
            {
                "timestamp": e.timestamp.isoformat(),
                "level": e.level,
                "step": e.step,
                "message": e.message,
                "duration_ms": e.duration_ms,
                "details": e.details
            }
            for e in self.events
        ]
        
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        return filepath


class PerformanceMonitor:
    """性能监控器 — 跟踪内存、CPU 和运行时间"""
    
    def __init__(self):
        self.measurements: List[Dict[str, Any]] = []
        self._start_time: Optional[float] = None
    
    def start(self):
        """开始监控"""
        self._start_time = time.time()
    
    def snapshot(self, label: str = "") -> Dict[str, Any]:
        """获取性能快照"""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        mem_info = process.memory_info()
        
        data = {
            "timestamp": datetime.now().isoformat(),
            "label": label,
            "memory_mb": mem_info.rss / 1024 / 1024,
            "memory_percent": process.memory_percent(),
            "cpu_percent": process.cpu_percent(),
            "elapsed_seconds": time.time() - self._start_time if self._start_time else 0
        }
        
        self.measurements.append(data)
        return data
    
    def get_report(self) -> Dict[str, Any]:
        """获取性能报告"""
        if not self.measurements:
            return {"status": "no_data"}
        
        mem_values = [m["memory_mb"] for m in self.measurements]
        cpu_values = [m["cpu_percent"] for m in self.measurements]
        
        return {
            "status": "success",
            "measurements_count": len(self.measurements),
            "memory": {
                "peak_mb": max(mem_values),
                "avg_mb": sum(mem_values) / len(mem_values),
                "final_mb": mem_values[-1]
            },
            "cpu": {
                "peak_percent": max(cpu_values),
                "avg_percent": sum(cpu_values) / len(cpu_values)
            },
            "elapsed_seconds": self.measurements[-1]["elapsed_seconds"]
        }
    
    def save_report(self, filepath: Path) -> Path:
        """保存性能报告"""
        report = self.get_report()
        
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        return filepath


class HealthChecker:
    """健康检查器 — 检查系统组件状态"""
    
    CHECKS = [
        "python_version",
        "pandas",
        "numpy",
        "matplotlib",
        "openpyxl",
        "llm_api",
        "disk_space",
        "memory"
    ]
    
    def __init__(self):
        self.results: Dict[str, Dict[str, Any]] = {}
    
    def check_all(self) -> Dict[str, Any]:
        """运行所有检查"""
        self.results = {}
        
        # Python 版本
        self._check_python()
        
        # 依赖
        self._check_dependencies()
        
        # LLM API
        self._check_llm()
        
        # 系统资源
        self._check_system()
        
        return self._compile_report()
    
    def _check_python(self):
        """检查 Python 版本"""
        import sys
        version = sys.version_info
        self.results["python_version"] = {
            "status": "ok" if version >= (3, 9) else "warning",
            "version": f"{version.major}.{version.minor}.{version.micro}",
            "message": "Python 版本正常" if version >= (3, 9) else "建议升级 Python 到 3.9+"
        }
    
    def _check_dependencies(self):
        """检查依赖"""
        deps = {
            "pandas": "pandas",
            "numpy": "numpy",
            "matplotlib": "matplotlib",
            "openpyxl": "openpyxl"
        }
        
        for name, module in deps.items():
            try:
                mod = __import__(module)
                version = getattr(mod, "__version__", "unknown")
                self.results[name] = {
                    "status": "ok",
                    "version": version,
                    "message": f"{name} {version} 已安装"
                }
            except ImportError:
                self.results[name] = {
                    "status": "error",
                    "version": None,
                    "message": f"{name} 未安装"
                }
    
    def _check_llm(self):
        """检查 LLM API"""
        try:
            from src.llm_client import get_llm_client
            client = get_llm_client()
            if client and client.api_key:
                self.results["llm_api"] = {
                    "status": "ok",
                    "message": "LLM API 已配置"
                }
            else:
                self.results["llm_api"] = {
                    "status": "warning",
                    "message": "LLM API 未配置，部分功能将降级"
                }
        except Exception as e:
            self.results["llm_api"] = {
                "status": "error",
                "message": f"LLM 检查失败: {str(e)}"
            }
    
    def _check_system(self):
        """检查系统资源"""
        try:
            import psutil
            
            # 磁盘空间
            disk = psutil.disk_usage(".")
            disk_pct = disk.percent
            self.results["disk_space"] = {
                "status": "ok" if disk_pct < 90 else "warning",
                "total_gb": disk.total / 1024**3,
                "used_gb": disk.used / 1024**3,
                "free_gb": disk.free / 1024**3,
                "percent": disk_pct,
                "message": f"磁盘使用率 {disk_pct:.1f}%"
            }
            
            # 内存
            mem = psutil.virtual_memory()
            self.results["memory"] = {
                "status": "ok" if mem.percent < 90 else "warning",
                "total_gb": mem.total / 1024**3,
                "available_gb": mem.available / 1024**3,
                "percent": mem.percent,
                "message": f"内存使用率 {mem.percent:.1f}%"
            }
            
        except ImportError:
            self.results["disk_space"] = {
                "status": "info",
                "message": "psutil 未安装，跳过系统检查"
            }
            self.results["memory"] = {
                "status": "info",
                "message": "psutil 未安装，跳过系统检查"
            }
    
    def _compile_report(self) -> Dict[str, Any]:
        """编译报告"""
        ok_count = sum(1 for r in self.results.values() if r["status"] == "ok")
        warning_count = sum(1 for r in self.results.values() if r["status"] == "warning")
        error_count = sum(1 for r in self.results.values() if r["status"] == "error")
        
        overall = "ok" if error_count == 0 else "error"
        if warning_count > 0 and error_count == 0:
            overall = "warning"
        
        return {
            "status": overall,
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "ok": ok_count,
                "warning": warning_count,
                "error": error_count,
                "total": len(self.results)
            },
            "checks": self.results
        }


class MetricsCollector:
    """指标收集器 — 收集和统计流水线指标"""
    
    def __init__(self):
        self.metrics: Dict[str, List[Any]] = {}
    
    def record(self, metric_name: str, value: Any):
        """记录指标"""
        if metric_name not in self.metrics:
            self.metrics[metric_name] = []
        self.metrics[metric_name].append({
            "timestamp": datetime.now().isoformat(),
            "value": value
        })
    
    def get_stats(self, metric_name: str) -> Dict[str, Any]:
        """获取指标统计"""
        values = self.metrics.get(metric_name, [])
        if not values:
            return {"count": 0}
        
        numeric = [v["value"] for v in values if isinstance(v["value"], (int, float))]
        
        if not numeric:
            return {
                "count": len(values),
                "values": [v["value"] for v in values]
            }
        
        return {
            "count": len(values),
            "min": min(numeric),
            "max": max(numeric),
            "avg": sum(numeric) / len(numeric),
            "last": numeric[-1]
        }
    
    def get_all_stats(self) -> Dict[str, Dict[str, Any]]:
        """获取所有指标统计"""
        return {name: self.get_stats(name) for name in self.metrics.keys()}
    
    def export(self, filepath: Path):
        """导出指标"""
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(self.metrics, f, ensure_ascii=False, indent=2)
