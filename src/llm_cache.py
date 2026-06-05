"""
LLM 调用缓存 — 基于 prompt hash 缓存结果，避免重复调用

使用场景：
- 同一数据集的多次分析中，用户画像、数据画像等 LLM 调用可以复用
- 降级重试时直接返回缓存结果
- 开发/测试阶段节省 API 调用
"""

import hashlib
import json
import time
from typing import Dict, Any, Optional, List
from pathlib import Path
import pickle


class LLMCache:
    """LLM 调用结果缓存"""
    
    def __init__(self, cache_dir: Optional[Path] = None, ttl_seconds: float = 3600):
        """
        Args:
            cache_dir: 缓存持久化目录（None 则仅内存缓存）
            ttl_seconds: 缓存有效期（秒），默认 1 小时
        """
        self._memory: Dict[str, Dict[str, Any]] = {}
        self.cache_dir = cache_dir
        self.ttl_seconds = ttl_seconds
        
        if cache_dir:
            cache_dir.mkdir(parents=True, exist_ok=True)
            self._load_disk_cache()
    
    def get(self, messages: List[Dict[str, str]], temperature: float, **kwargs) -> Optional[str]:
        """获取缓存结果"""
        key = self._hash_key(messages, temperature, **kwargs)
        
        # 内存缓存
        entry = self._memory.get(key)
        if entry and time.time() - entry["timestamp"] < self.ttl_seconds:
            return entry["result"]
        
        # 磁盘缓存
        if self.cache_dir:
            cache_file = self.cache_dir / f"{key}.pkl"
            if cache_file.exists():
                try:
                    with open(cache_file, "rb") as f:
                        entry = pickle.load(f)
                    if time.time() - entry["timestamp"] < self.ttl_seconds:
                        self._memory[key] = entry  # 回填内存
                        return entry["result"]
                except Exception:
                    pass
        
        return None
    
    def set(self, messages: List[Dict[str, str]], temperature: float, result: str, **kwargs):
        """设置缓存"""
        key = self._hash_key(messages, temperature, **kwargs)
        entry = {
            "timestamp": time.time(),
            "result": result,
            "messages": messages,
            "temperature": temperature,
        }
        
        self._memory[key] = entry
        
        if self.cache_dir:
            cache_file = self.cache_dir / f"{key}.pkl"
            try:
                with open(cache_file, "wb") as f:
                    pickle.dump(entry, f)
            except Exception:
                pass  # 磁盘写入失败不影响内存缓存
    
    def clear(self):
        """清除所有缓存"""
        self._memory.clear()
        if self.cache_dir:
            for f in self.cache_dir.glob("*.pkl"):
                try:
                    f.unlink()
                except Exception:
                    pass
    
    def stats(self) -> Dict[str, Any]:
        """缓存统计"""
        return {
            "memory_entries": len(self._memory),
            "disk_entries": len(list(self.cache_dir.glob("*.pkl"))) if self.cache_dir else 0,
            "ttl_seconds": self.ttl_seconds,
        }
    
    def _hash_key(self, messages: List[Dict[str, str]], temperature: float, **kwargs) -> str:
        """生成缓存 key"""
        content = json.dumps({
            "messages": messages,
            "temperature": temperature,
            "kwargs": {k: str(v) for k, v in kwargs.items()},
        }, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(content.encode("utf-8")).hexdigest()[:32]
    
    def _load_disk_cache(self):
        """加载磁盘缓存到内存"""
        if not self.cache_dir:
            return
        for cache_file in self.cache_dir.glob("*.pkl"):
            try:
                with open(cache_file, "rb") as f:
                    entry = pickle.load(f)
                key = cache_file.stem
                self._memory[key] = entry
            except Exception:
                pass


# 全局默认缓存实例
_default_cache: Optional[LLMCache] = None


def get_default_cache(cache_dir: Optional[Path] = None) -> LLMCache:
    """获取全局默认缓存"""
    global _default_cache
    if _default_cache is None:
        _default_cache = LLMCache(cache_dir=cache_dir)
    return _default_cache


__all__ = ["LLMCache", "get_default_cache"]
