"""
微信公众号自动发布 API — 真实微信接口集成

使用微信公众平台的 "发布" 接口（非群发，仅展示在公众号主页）：
- 添加草稿: draft/add
- 发布草稿: freepublish/submit

配置步骤:
1. 登录微信公众号后台 (mp.weixin.qq.com)
2. 开发 → 基本配置 → 获取 AppID 和 AppSecret
3. 将服务器 IP 添加到 IP 白名单
4. 填写本模块配置文件

限制:
- 需要公众号认证（个人订阅号支持有限，建议企业/服务号）
- 封面图片需要先上传到微信素材库
- 每日发布次数有限制（根据账号类型）
"""

from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from pathlib import Path
from datetime import datetime
import json
import time
import requests
import base64
import os


@dataclass
class WechatArticle:
    """微信公众号文章"""
    title: str
    content: str
    author: str = ""
    digest: str = ""  # 摘要
    thumb_media_id: str = ""  # 封面图片素材ID
    content_source_url: str = ""  # 原文链接
    need_open_comment: int = 1  # 开启评论
    only_fans_can_comment: int = 0  # 所有人可评论


@dataclass
class PublishResult:
    """发布结果"""
    success: bool
    message: str
    publish_id: str = ""  # 微信返回的发布ID
    url: str = ""  # 文章链接
    create_time: str = ""
    raw_response: Dict = field(default_factory=dict)


class WechatPublisher:
    """
    微信公众号发布器
    
    支持功能:
    - 获取 access_token（自动刷新）
    - 上传图片到微信素材库（获取 thumb_media_id）
    - 添加草稿（draft/add）
    - 发布草稿（freepublish/submit）
    - 查询发布状态（freepublish/get）
    - 删除已发布（freepublish/delete）
    """
    
    API_BASE = "https://api.weixin.qq.com/cgi-bin"
    
    def __init__(self, app_id: str = None, app_secret: str = None, 
                 config_file: Path = None):
        """
        初始化微信发布器
        
        Args:
            app_id: 微信公众号 AppID
            app_secret: 微信公众号 AppSecret
            config_file: 配置文件路径（JSON格式，包含 app_id, app_secret）
        """
        self.config_file = config_file or Path("config/wechat.json")
        self.config = {}
        self.access_token = ""
        self.token_expires = 0  # access_token 过期时间戳
        
        # 加载配置
        if app_id and app_secret:
            self.config = {
                "app_id": app_id,
                "app_secret": app_secret,
                "ip_whitelist": []
            }
        elif self.config_file.exists():
            with open(self.config_file, "r", encoding="utf-8") as f:
                self.config = json.load(f)
        else:
            self.config = {"app_id": "", "app_secret": ""}
    
    def _get_access_token(self) -> str:
        """
        获取 access_token（带缓存，自动刷新）
        
        Returns:
            有效的 access_token
        """
        # 检查缓存是否有效（提前5分钟刷新）
        if self.access_token and time.time() < self.token_expires - 300:
            return self.access_token
        
        app_id = self.config.get("app_id")
        app_secret = self.config.get("app_secret")
        
        if not app_id or not app_secret:
            raise ValueError("缺少 AppID 或 AppSecret，请先配置微信公众号凭证")
        
        url = f"{self.API_BASE}/token"
        params = {
            "grant_type": "client_credential",
            "appid": app_id,
            "secret": app_secret
        }
        
        try:
            resp = requests.get(url, params=params, timeout=30)
            data = resp.json()
            
            if "access_token" in data:
                self.access_token = data["access_token"]
                # 微信 access_token 默认有效期 7200 秒
                expires_in = data.get("expires_in", 7200)
                self.token_expires = time.time() + expires_in
                return self.access_token
            else:
                errcode = data.get("errcode", -1)
                errmsg = data.get("errmsg", "未知错误")
                raise RuntimeError(f"获取 access_token 失败: [{errcode}] {errmsg}")
        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"请求微信接口失败: {e}")
    
    def upload_image(self, image_path: Path) -> str:
        """
        上传图片到微信素材库（获取 thumb_media_id）
        
        注意：封面图片必须是永久素材，通过 /material/add_material 上传
        
        Args:
            image_path: 图片文件路径
            
        Returns:
            media_id（素材ID）
        """
        token = self._get_access_token()
        url = f"{self.API_BASE}/material/add_material?access_token={token}&type=image"
        
        with open(image_path, "rb") as f:
            files = {"media": (image_path.name, f, "image/jpeg")}
            resp = requests.post(url, files=files, timeout=60)
        
        data = resp.json()
        if "media_id" in data:
            return data["media_id"]
        else:
            errcode = data.get("errcode", -1)
            errmsg = data.get("errmsg", "未知错误")
            raise RuntimeError(f"上传图片失败: [{errcode}] {errmsg}")
    
    def add_draft(self, article: WechatArticle) -> str:
        """
        添加草稿（draft/add）
        
        Args:
            article: 微信文章对象
            
        Returns:
            media_id（草稿素材ID）
        """
        token = self._get_access_token()
        url = f"{self.API_BASE}/draft/add?access_token={token}"
        
        # 构造文章数据
        payload = {
            "articles": [{
                "title": article.title,
                "content": article.content,
                "author": article.author,
                "digest": article.digest,
                "thumb_media_id": article.thumb_media_id,
                "content_source_url": article.content_source_url,
                "need_open_comment": article.need_open_comment,
                "only_fans_can_comment": article.only_fans_can_comment
            }]
        }
        
        resp = requests.post(url, json=payload, timeout=60)
        data = resp.json()
        
        if "media_id" in data:
            return data["media_id"]
        else:
            errcode = data.get("errcode", -1)
            errmsg = data.get("errmsg", "未知错误")
            raise RuntimeError(f"添加草稿失败: [{errcode}] {errmsg}")
    
    def publish(self, media_id: str) -> PublishResult:
        """
        发布草稿（freepublish/submit）
        
        Args:
            media_id: 草稿素材ID
            
        Returns:
            PublishResult 对象
        """
        token = self._get_access_token()
        url = f"{self.API_BASE}/freepublish/submit?access_token={token}"
        
        payload = {"media_id": media_id}
        resp = requests.post(url, json=payload, timeout=60)
        data = resp.json()
        
        if data.get("errcode") == 0:
            return PublishResult(
                success=True,
                message="发布成功",
                publish_id=data.get("publish_id", ""),
                raw_response=data
            )
        else:
            errcode = data.get("errcode", -1)
            errmsg = data.get("errmsg", "未知错误")
            return PublishResult(
                success=False,
                message=f"发布失败: [{errcode}] {errmsg}",
                raw_response=data
            )
    
    def get_publish_status(self, publish_id: str) -> Dict:
        """
        查询发布状态（freepublish/get）
        
        Args:
            publish_id: 发布ID
            
        Returns:
            发布状态信息
        """
        token = self._get_access_token()
        url = f"{self.API_BASE}/freepublish/get?access_token={token}"
        
        payload = {"publish_id": publish_id}
        resp = requests.post(url, json=payload, timeout=60)
        return resp.json()
    
    def delete_publish(self, article_id: str, index: int = 0) -> bool:
        """
        删除已发布文章（freepublish/delete）
        
        Args:
            article_id: 文章ID（article_id）
            index: 要删除的文章在图文消息中的位置（第一篇为0）
            
        Returns:
            是否删除成功
        """
        token = self._get_access_token()
        url = f"{self.API_BASE}/freepublish/delete?access_token={token}"
        
        payload = {"article_id": article_id, "index": index}
        resp = requests.post(url, json=payload, timeout=60)
        data = resp.json()
        
        return data.get("errcode") == 0
    
    def publish_article(self, title: str, content: str, 
                       author: str = "", digest: str = "",
                       thumb_media_id: str = "",
                       content_source_url: str = "") -> PublishResult:
        """
        一键发布文章（添加草稿 + 发布）
        
        Args:
            title: 文章标题
            content: 文章内容（HTML格式）
            author: 作者名
            digest: 摘要
            thumb_media_id: 封面图片素材ID（可选）
            content_source_url: 原文链接（可选）
            
        Returns:
            PublishResult 对象
        """
        try:
            article = WechatArticle(
                title=title,
                content=content,
                author=author,
                digest=digest,
                thumb_media_id=thumb_media_id,
                content_source_url=content_source_url
            )
            
            # 1. 添加草稿
            media_id = self.add_draft(article)
            
            # 2. 发布草稿
            result = self.publish(media_id)
            result.raw_response["media_id"] = media_id
            
            return result
            
        except Exception as e:
            return PublishResult(
                success=False,
                message=f"发布失败: {str(e)}"
            )
    
    def save_config(self):
        """保存配置到文件"""
        self.config_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_file, "w", encoding="utf-8") as f:
            json.dump(self.config, f, ensure_ascii=False, indent=2)
    
    def test_connection(self) -> Tuple[bool, str]:
        """
        测试连接（验证凭证是否有效）
        
        Returns:
            (是否成功, 消息)
        """
        try:
            self._get_access_token()
            return True, "连接成功，access_token 获取正常"
        except Exception as e:
            return False, str(e)


def create_wechat_config_template():
    """
    创建微信配置文件模板
    
    使用方式:
        from src.api_publish.wechat_real import create_wechat_config_template
        create_wechat_config_template()
    """
    template = {
        "app_id": "YOUR_APPID_HERE",
        "app_secret": "YOUR_APPSECRET_HERE",
        "note": "从微信公众号后台获取：开发 -> 基本配置 -> 公众号开发信息",
        "ip_whitelist": [
            "你的服务器公网IP地址"
        ],
        "help": "配置步骤：1.登录mp.weixin.qq.com 2.开发->基本配置 3.获取AppID和AppSecret 4.设置IP白名单"
    }
    
    config_path = Path("config/wechat.json")
    config_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(template, f, ensure_ascii=False, indent=2)
    
    print(f"✅ 微信配置文件模板已创建: {config_path}")
    print("⚠️  请编辑此文件，填写你的 AppID 和 AppSecret")
    print("📖 获取方式：微信公众号后台 -> 开发 -> 基本配置 -> 公众号开发信息")
    
    return config_path


class WechatPublishOrchestrator:
    """
    微信发布编排器 — 整合流水线输出，自动发布到公众号
    
    使用方式:
        from src.api_publish.wechat_real import WechatPublishOrchestrator
        
        orchestrator = WechatPublishOrchestrator()
        orchestrator.load_pipeline_result(pipeline_result)
        orchestrator.publish_wechat(title="Day 2 总结", author="小李")
    """
    
    def __init__(self, publisher: WechatPublisher = None):
        self.publisher = publisher or WechatPublisher()
        self.pipeline_result = None
    
    def load_pipeline_result(self, result: Dict):
        """加载流水线结果"""
        self.pipeline_result = result
    
    def publish_wechat(self, title: str = None, author: str = "") -> PublishResult:
        """
        将流水线结果发布到微信公众号
        
        Args:
            title: 文章标题（默认使用流水线中的故事标题）
            author: 作者名
            
        Returns:
            PublishResult 对象
        """
        if not self.pipeline_result:
            return PublishResult(
                success=False,
                message="未加载流水线结果，请先调用 load_pipeline_result()"
            )
        
        # 获取标题
        if not title:
            story = self.pipeline_result.get("story", {})
            title = story.get("title", "数据分析报告")
        
        # 构建 HTML 内容
        content = self._build_html_content()
        
        # 生成摘要
        digest = self._generate_digest()
        
        return self.publisher.publish_article(
            title=title,
            content=content,
            author=author,
            digest=digest
        )
    
    def _build_html_content(self) -> str:
        """构建微信文章 HTML 内容"""
        parts = []
        
        # 标题
        story = self.pipeline_result.get("story", {})
        parts.append(f"<h1>{story.get('title', '数据报告')}</h1>")
        
        # 故事章节
        for section in story.get("sections", []):
            title = section.get("title", "")
            content = section.get("content", "")
            if title:
                parts.append(f"<h2>{title}</h2>")
            if content:
                parts.append(f"<p>{content}</p>")
        
        # 洞察
        insights = self.pipeline_result.get("insights", [])
        if insights:
            parts.append("<h2>💡 数据洞察</h2>")
            for insight in insights:
                title = insight.get("title", "")
                desc = insight.get("description", "")
                parts.append(f"<p><strong>{title}</strong>：{desc}</p>")
        
        # 图表
        charts = self.pipeline_result.get("charts", [])
        if charts:
            parts.append("<h2>📊 数据图表</h2>")
            for chart in charts:
                chart_data = chart.get("data", "")
                if chart_data:
                    # 使用 base64 图片
                    parts.append(f'<p><img src="{chart_data}" style="max-width:100%"></p>')
        
        # 性能信息
        perf = self.pipeline_result.get("performance", {})
        if perf:
            parts.append("<h2>⚡ 性能指标</h2>")
            parts.append(f"<p>内存峰值: {perf.get('peak_mb', 'N/A')} MB</p>")
            parts.append(f"<p>处理耗时: {perf.get('elapsed_seconds', 'N/A')} 秒</p>")
        
        return "\n".join(parts)
    
    def _generate_digest(self, max_length: int = 120) -> str:
        """生成文章摘要"""
        story = self.pipeline_result.get("story", {})
        sections = story.get("sections", [])
        
        if sections:
            first_content = sections[0].get("content", "")
            if first_content:
                return first_content[:max_length] + "..." if len(first_content) > max_length else first_content
        
        insights = self.pipeline_result.get("insights", [])
        if insights:
            first = insights[0].get("title", "")
            return f"本文分析了数据中的关键洞察：{first}"
        
        return "AI自动生成的数据叙事报告"


if __name__ == "__main__":
    # 测试/创建配置模板
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "init":
        create_wechat_config_template()
    else:
        # 测试连接
        publisher = WechatPublisher()
        success, msg = publisher.test_connection()
        print(f"连接测试: {'✅' if success else '❌'} {msg}")
