"""
大模型调用封装 — 统一接口调用 LLM
"""

import json
from typing import Optional, List, Dict, Any
from openai import OpenAI
from src.config import LLM_CONFIG


class LLMClient:
    """统一大模型调用客户端"""
    
    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or LLM_CONFIG["api_key"]
        self.base_url = base_url or LLM_CONFIG["base_url"]
        self.model = model or LLM_CONFIG["model"]
        self.temperature = LLM_CONFIG["temperature"]
        self.max_tokens = LLM_CONFIG["max_tokens"]
        
        self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)
    
    def chat(self, messages: List[Dict[str, str]], temperature: Optional[float] = None, **kwargs) -> str:
        """
        通用对话接口
        
        Args:
            messages: 消息列表 [{"role": "system"|"user"|"assistant", "content": str}]
            temperature: 温度参数（覆盖默认）
            
        Returns:
            模型返回的文本内容
        """
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature or self.temperature,
                max_tokens=self.max_tokens,
                **kwargs
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"[LLM调用错误] {str(e)}"
    
    def structured_output(self, prompt: str, schema: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """
        结构化输出 — 让模型返回 JSON
        
        Args:
            prompt: 用户提示
            schema: 期望的输出结构描述
            
        Returns:
            解析后的 JSON 字典
        """
        schema_desc = json.dumps(schema, ensure_ascii=False, indent=2)
        system_msg = f"""你是一个严格遵循 JSON 格式输出的助手。
请确保你的回复是一个合法的 JSON 对象，结构如下：
{schema_desc}
不要输出任何额外的文字，只输出 JSON。"""
        
        messages = [
            {"role": "system", "content": system_msg},
            {"role": "user", "content": prompt}
        ]
        
        try:
            response = self.chat(messages, temperature=0.1, **kwargs)
            # 清理可能的 markdown 代码块
            text = response.strip()
            if text.startswith("```json"):
                text = text[7:]
            if text.startswith("```"):
                text = text[3:]
            if text.endswith("```"):
                text = text[:-3]
            return json.loads(text.strip())
        except json.JSONDecodeError as e:
            return {"error": f"JSON解析失败: {str(e)}", "raw": response}
        except Exception as e:
            return {"error": str(e)}
    
    def summarize(self, text: str, max_length: int = 200) -> str:
        """文本摘要"""
        prompt = f"请用不超过 {max_length} 字总结以下内容：\n\n{text}"
        return self.chat([{"role": "user", "content": prompt}], temperature=0.3)
    
    def analyze_data(self, data_description: str, task: str = "general") -> str:
        """数据洞察分析"""
        prompt = f"""基于以下数据描述，请给出专业的数据洞察和分析建议。

数据描述：
{data_description}

分析任务：{task}

请从以下角度分析：
1. 数据整体特征
2. 可能的异常或问题
3. 有价值的分析方向
4. 建议的可视化方式"""
        return self.chat([{"role": "user", "content": prompt}], temperature=0.5)


# 单例模式
_llm_client: Optional[LLMClient] = None


def get_llm_client() -> LLMClient:
    """获取全局 LLM 客户端实例"""
    global _llm_client
    if _llm_client is None:
        _llm_client = LLMClient()
    return _llm_client
