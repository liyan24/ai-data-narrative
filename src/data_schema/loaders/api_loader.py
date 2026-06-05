"""API 数据源加载器 — 支持 REST API 分页获取"""

from typing import Dict, Any, Optional
import pandas as pd


class RESTAPILoader:
    """REST API 加载器"""
    
    @staticmethod
    def load(url: str, 
             headers: Optional[Dict[str, str]] = None,
             params: Optional[Dict[str, Any]] = None,
             auth: Optional[Any] = None,
             pagination: Optional[str] = None,
             max_pages: int = 10,
             data_path: Optional[str] = None) -> pd.DataFrame:
        """
        从 REST API 加载数据
        
        Args:
            url: API 端点 URL
            headers: HTTP 请求头
            params: 查询参数
            auth: 认证信息 (用户名, 密码) 或 Bearer token
            pagination: 分页方式 ("offset", "page", "cursor", None)
            max_pages: 最大获取页数
            data_path: JSON 响应中数据列表的路径，如 "data.items" 或 "results"
        """
        try:
            import requests
        except ImportError:
            raise ImportError("使用 REST API 需要安装 requests: pip install requests")
        
        all_records = []
        current_page = 0
        current_params = dict(params) if params else {}
        
        while current_page < max_pages:
            # 设置分页参数
            if pagination == "offset":
                current_params["offset"] = len(all_records)
            elif pagination == "page":
                current_params["page"] = current_page + 1
            
            # 发送请求
            request_headers = dict(headers) if headers else {}
            if isinstance(auth, str) and auth.startswith("Bearer "):
                request_headers["Authorization"] = auth

            if isinstance(auth, tuple) and len(auth) == 2:
                response = requests.get(url, headers=request_headers, params=current_params, auth=auth, timeout=30)
            else:
                response = requests.get(url, headers=request_headers, params=current_params, timeout=30)
            
            response.raise_for_status()
            data = response.json()
            
            # 提取记录列表
            records = RESTAPILoader._extract_records(data, data_path)
            if not records:
                break
            
            all_records.extend(records)
            current_page += 1
            
            # 检查是否有更多数据
            if pagination is None:
                break
            if len(records) == 0:
                break
        
        if not all_records:
            raise ValueError("API 返回数据为空")
        
        return pd.json_normalize(all_records)
    
    @staticmethod
    def _extract_records(data: Any, data_path: Optional[str] = None) -> list:
        """从响应数据中提取记录列表"""
        if data_path:
            parts = data_path.split(".")
            current = data
            for part in parts:
                if isinstance(current, dict) and part in current:
                    current = current[part]
                else:
                    return []
            if isinstance(current, list):
                return current
            return []
        
        # 自动探测
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            for key in ["data", "results", "items", "records", "rows"]:
                if key in data and isinstance(data[key], list):
                    return data[key]
            # 如果只有一个键且值为列表
            if len(data) == 1:
                first_value = list(data.values())[0]
                if isinstance(first_value, list):
                    return first_value
        return []


__all__ = ["RESTAPILoader"]
