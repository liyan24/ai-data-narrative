"""
自动发布 API — 模拟小红书/微信公众号发布接口

提供模拟发布功能，实际发布需接入平台真实 API。
使用方式:
    from src.api_publish.publisher import PlatformPublisher, PublishTask
    
    publisher = PlatformPublisher()
    publisher.publish_xiaohongshu(content, title)
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from pathlib import Path
from datetime import datetime
import json
import time


@dataclass
class PublishTask:
    """发布任务"""
    platform: str
    content: str
    title: str
    media_paths: List[Path] = field(default_factory=list)
    status: str = "pending"  # pending, publishing, published, failed
    created_at: datetime = field(default_factory=datetime.now)
    published_at: Optional[datetime] = None
    error_message: Optional[str] = None
    publish_id: Optional[str] = None


class PlatformPublisher:
    """平台发布器 — 支持多平台发布"""
    
    # 模拟平台 API（实际使用时替换为真实 API）
    PLATFORM_APIS = {
        "xiaohongshu": {
            "name": "小红书",
            "max_words": 1000,
            "supports_images": True,
            "supports_video": False,
            "hashtag_count": 5,
        },
        "wechat_mp": {
            "name": "微信公众号",
            "max_words": 20000,
            "supports_images": True,
            "supports_video": True,
            "supports_rich_text": True,
        },
        "zhihu": {
            "name": "知乎",
            "max_words": 50000,
            "supports_images": True,
            "supports_rich_text": True,
        },
        "juejin": {
            "name": "掘金",
            "max_words": 10000,
            "supports_images": True,
            "supports_markdown": True,
        }
    }
    
    def __init__(self, config_dir: Path = None):
        self.config_dir = config_dir or Path("./publish_config")
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.tasks: List[PublishTask] = []
        self._load_config()
    
    def _load_config(self):
        """加载平台配置"""
        config_file = self.config_dir / "platforms.json"
        if config_file.exists():
            with open(config_file, "r", encoding="utf-8") as f:
                self.config = json.load(f)
        else:
            self.config = {k: {"enabled": False, "api_key": None} 
                          for k in self.PLATFORM_APIS.keys()}
            self._save_config()
    
    def _save_config(self):
        """保存平台配置"""
        config_file = self.config_dir / "platforms.json"
        with open(config_file, "w", encoding="utf-8") as f:
            json.dump(self.config, f, ensure_ascii=False, indent=2)
    
    def configure_platform(self, platform: str, api_key: str, 
                          enabled: bool = True):
        """配置平台"""
        if platform not in self.PLATFORM_APIS:
            raise ValueError(f"不支持的平台: {platform}")
        
        self.config[platform] = {
            "enabled": enabled,
            "api_key": api_key,
            "configured_at": datetime.now().isoformat()
        }
        self._save_config()
    
    def publish_xiaohongshu(self, content: str, title: str = "",
                           images: List[Path] = None) -> Dict[str, Any]:
        """发布到小红书"""
        task = PublishTask(
            platform="xiaohongshu",
            content=content,
            title=title or "数据洞察",
            media_paths=images or []
        )
        
        return self._publish(task)
    
    def publish_wechat(self, content: str, title: str,
                      cover_image: Path = None,
                      author: str = "AI数据叙事") -> Dict[str, Any]:
        """发布到微信公众号"""
        task = PublishTask(
            platform="wechat_mp",
            content=content,
            title=title,
            media_paths=[cover_image] if cover_image else []
        )
        
        return self._publish(task)
    
    def publish(self, platform: str, content: str, title: str = "",
                media: List[Path] = None) -> Dict[str, Any]:
        """通用发布方法"""
        task = PublishTask(
            platform=platform,
            content=content,
            title=title,
            media_paths=media or []
        )
        
        return self._publish(task)
    
    def _publish(self, task: PublishTask) -> Dict[str, Any]:
        """执行发布"""
        self.tasks.append(task)
        
        # 检查平台配置
        platform_config = self.config.get(task.platform, {})
        if not platform_config.get("enabled"):
            task.status = "failed"
            task.error_message = f"{self.PLATFORM_APIS[task.platform]['name']} 未启用"
            return self._build_result(task)
        
        # 模拟发布过程
        task.status = "publishing"
        
        try:
            # 验证内容
            result = self._validate_content(task)
            if not result["valid"]:
                task.status = "failed"
                task.error_message = result["error"]
                return self._build_result(task)
            
            # 模拟 API 调用
            time.sleep(0.5)  # 模拟网络延迟
            
            # 生成发布 ID
            task.publish_id = f"{task.platform}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
            task.status = "published"
            task.published_at = datetime.now()
            
            return self._build_result(task)
            
        except Exception as e:
            task.status = "failed"
            task.error_message = str(e)
            return self._build_result(task)
    
    def _validate_content(self, task: PublishTask) -> Dict[str, Any]:
        """验证内容是否符合平台要求"""
        platform_info = self.PLATFORM_APIS.get(task.platform, {})
        max_words = platform_info.get("max_words", 10000)
        
        # 字数检查
        word_count = len(task.content)
        if word_count > max_words:
            return {
                "valid": False,
                "error": f"内容超过字数限制 ({word_count} > {max_words})"
            }
        
        # 图片检查
        if task.media_paths:
            for img_path in task.media_paths:
                if not img_path.exists():
                    return {
                        "valid": False,
                        "error": f"图片不存在: {img_path}"
                    }
        
        return {"valid": True}
    
    def _build_result(self, task: PublishTask) -> Dict[str, Any]:
        """构建发布结果"""
        return {
            "platform": task.platform,
            "platform_name": self.PLATFORM_APIS.get(task.platform, {}).get("name", task.platform),
            "status": task.status,
            "publish_id": task.publish_id,
            "title": task.title,
            "word_count": len(task.content),
            "media_count": len(task.media_paths),
            "created_at": task.created_at.isoformat() if task.created_at else None,
            "published_at": task.published_at.isoformat() if task.published_at else None,
            "error": task.error_message
        }
    
    def get_tasks(self, platform: str = None, 
                  status: str = None) -> List[Dict[str, Any]]:
        """获取发布任务列表"""
        tasks = self.tasks
        
        if platform:
            tasks = [t for t in tasks if t.platform == platform]
        if status:
            tasks = [t for t in tasks if t.status == status]
        
        return [self._build_result(t) for t in tasks]
    
    def get_status(self, platform: str = None) -> Dict[str, Any]:
        """获取发布状态"""
        if platform:
            tasks = [t for t in self.tasks if t.platform == platform]
        else:
            tasks = self.tasks
        
        total = len(tasks)
        published = len([t for t in tasks if t.status == "published"])
        failed = len([t for t in tasks if t.status == "failed"])
        pending = len([t for t in tasks if t.status == "pending"])
        
        return {
            "total": total,
            "published": published,
            "failed": failed,
            "pending": pending,
            "success_rate": published / total * 100 if total > 0 else 0
        }
    
    def batch_publish(self, contents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """批量发布"""
        results = []
        
        for item in contents:
            result = self.publish(
                platform=item.get("platform", "markdown"),
                content=item.get("content", ""),
                title=item.get("title", ""),
                media=[Path(p) for p in item.get("media", [])] if item.get("media") else None
            )
            results.append(result)
        
        return results


class PublishOrchestrator:
    """发布编排器 — 统一管理多平台发布"""
    
    def __init__(self, publisher: PlatformPublisher = None):
        self.publisher = publisher or PlatformPublisher()
        self.publish_history: List[Dict[str, Any]] = []
    
    def publish_report(self, report_path: Path, 
                      platforms: List[str] = None) -> Dict[str, Any]:
        """发布报告到多个平台"""
        platforms = platforms or ["xiaohongshu", "wechat_mp", "markdown"]
        
        # 读取报告内容
        with open(report_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        title = f"数据报告: {report_path.stem}"
        
        results = {}
        for platform in platforms:
            try:
                result = self.publisher.publish(platform, content, title)
                results[platform] = result
            except Exception as e:
                results[platform] = {
                    "status": "failed",
                    "error": str(e)
                }
        
        self.publish_history.append({
            "timestamp": datetime.now().isoformat(),
            "report": str(report_path),
            "platforms": platforms,
            "results": results
        })
        
        return results
    
    def schedule_publish(self, report_dir: Path, 
                        schedule: str = "daily",
                        platforms: List[str] = None) -> str:
        """定时发布报告"""
        from src.automation.scheduler import TaskScheduler
        
        scheduler = TaskScheduler()
        
        def publish_task(**kwargs):
            # 查找最新报告
            reports = sorted(report_dir.glob("report_*.html"), 
                           key=lambda p: p.stat().st_mtime, reverse=True)
            if reports:
                return self.publish_report(reports[0], platforms)
            return {"error": "No reports found"}
        
        if schedule == "daily":
            task_id = scheduler.schedule_daily(
                hour=9, task=publish_task, name="daily_report_publish"
            )
        elif schedule == "interval":
            task_id = scheduler.schedule_interval(
                minutes=60, task=publish_task, name="hourly_report_publish"
            )
        else:
            raise ValueError(f"不支持的调度: {schedule}")
        
        return task_id
    
    def get_history(self) -> List[Dict[str, Any]]:
        """获取发布历史"""
        return self.publish_history
