"""
插件系统 — 可扩展的数据处理插件

使用方式:
    from src.plugins.manager import PluginManager
    
    manager = PluginManager()
    manager.load_plugins("plugins/")
    manager.run_hook("after_analysis", data)
"""

from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from pathlib import Path
import importlib.util
import json
import sys


@dataclass
class PluginInfo:
    """插件信息"""
    name: str
    version: str
    description: str
    author: str
    hooks: List[str] = field(default_factory=list)
    path: Path = None


class PluginBase:
    """插件基类"""
    
    name = "base"
    version = "1.0"
    description = "基础插件"
    author = "unknown"
    hooks = []
    
    def activate(self):
        """激活插件"""
        pass
    
    def deactivate(self):
        """停用插件"""
        pass
    
    def on_load(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """数据加载后钩子"""
        return data
    
    def on_clean(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """数据清洗后钩子"""
        return data
    
    def on_insight(self, insights: List[Any]) -> List[Any]:
        """洞察生成后钩子"""
        return insights
    
    def on_story(self, sections: List[Any]) -> List[Any]:
        """故事生成后钩子"""
        return sections
    
    def on_report(self, report_path: Path) -> Path:
        """报告生成后钩子"""
        return report_path


class PluginManager:
    """插件管理器"""
    
    HOOKS = [
        "on_load", "on_clean", "on_insight", 
        "on_story", "on_report"
    ]
    
    def __init__(self, plugin_dir: Path = None):
        self.plugin_dir = plugin_dir or Path("./plugins")
        self.plugins: Dict[str, PluginBase] = {}
        self.hooks: Dict[str, List[Callable]] = {h: [] for h in self.HOOKS}
    
    def load_plugin(self, plugin_path: Path) -> Optional[PluginBase]:
        """加载单个插件"""
        if not plugin_path.exists():
            return None
        
        try:
            # 动态导入模块
            spec = importlib.util.spec_from_file_location(
                plugin_path.stem, plugin_path
            )
            module = importlib.util.module_from_spec(spec)
            sys.modules[plugin_path.stem] = module
            spec.loader.exec_module(module)
            
            # 查找插件类
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (isinstance(attr, type) and 
                    issubclass(attr, PluginBase) and 
                    attr != PluginBase):
                    
                    plugin = attr()
                    self.plugins[plugin.name] = plugin
                    
                    # 注册钩子
                    for hook in self.HOOKS:
                        if hasattr(plugin, hook):
                            self.hooks[hook].append(getattr(plugin, hook))
                    
                    plugin.activate()
                    return plugin
                    
        except Exception as e:
            print(f"[PLUGIN] 加载失败 {plugin_path}: {e}")
            return None
    
    def load_plugins(self, plugin_dir: Path = None):
        """加载插件目录中的所有插件"""
        directory = plugin_dir or self.plugin_dir
        if not directory.exists():
            return
        
        for plugin_file in directory.glob("*.py"):
            if plugin_file.name.startswith("_"):
                continue
            self.load_plugin(plugin_file)
        
        print(f"[PLUGIN] 已加载 {len(self.plugins)} 个插件")
    
    def run_hook(self, hook_name: str, data: Any) -> Any:
        """运行钩子"""
        if hook_name not in self.hooks:
            return data
        
        for handler in self.hooks[hook_name]:
            try:
                data = handler(data)
            except Exception as e:
                print(f"[PLUGIN] 钩子执行失败: {e}")
        
        return data
    
    def list_plugins(self) -> List[Dict[str, Any]]:
        """列出已加载的插件"""
        return [
            {
                "name": p.name,
                "version": p.version,
                "description": p.description,
                "author": p.author,
                "hooks": p.hooks
            }
            for p in self.plugins.values()
        ]
    
    def unload_plugin(self, name: str):
        """卸载插件"""
        plugin = self.plugins.pop(name, None)
        if plugin:
            plugin.deactivate()
            # 移除钩子
            for hook_list in self.hooks.values():
                hook_list[:] = [h for h in hook_list if getattr(h, '__self__', None) != plugin]


class SamplePlugin(PluginBase):
    """示例插件 — 添加数据水印"""
    
    name = "watermark"
    version = "1.0"
    description = "为报告添加时间戳水印"
    author = "system"
    hooks = ["on_report"]
    
    def on_report(self, report_path: Path) -> Path:
        """在报告末尾添加水印"""
        from datetime import datetime
        
        if report_path.suffix == ".html":
            with open(report_path, "r", encoding="utf-8") as f:
                content = f.read()
            
            watermark = f"""
            <div style="text-align:center; color:#999; font-size:0.8em; margin-top:50px;">
                <hr/>
                <p>Generated by AI Data Narrative System | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            </div>
            </body>
            """
            content = content.replace("</body>", watermark)
            
            with open(report_path, "w", encoding="utf-8") as f:
                f.write(content)
        
        return report_path


class CustomInsightPlugin(PluginBase):
    """示例插件 — 自定义洞察规则"""
    
    name = "custom_insight"
    version = "1.0"
    description = "添加自定义洞察规则"
    author = "system"
    hooks = ["on_insight"]
    
    def __init__(self):
        super().__init__()
        self.rules = []
    
    def add_rule(self, name: str, check_func: Callable):
        """添加自定义规则"""
        self.rules.append((name, check_func))
    
    def on_insight(self, insights: List[Any]) -> List[Any]:
        """运行自定义规则"""
        for name, check in self.rules:
            try:
                result = check(insights)
                if result:
                    print(f"[PLUGIN] 自定义洞察: {name}")
            except Exception as e:
                print(f"[PLUGIN] 规则执行失败 {name}: {e}")
        
        return insights
