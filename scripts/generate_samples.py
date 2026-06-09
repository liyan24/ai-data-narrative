"""Generate 4 types of sample data, 5 samples each."""
from __future__ import annotations

import json
import os
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd

BASE = Path(__file__).resolve().parents[1] / "data" / "samples"

# --------------------------------------------------------------------------- #
# 1. Timeseries
# --------------------------------------------------------------------------- #
def gen_timeseries():
    out = BASE / "timeseries"
    out.mkdir(parents=True, exist_ok=True)

    configs = [
        {
            "file": "sales_daily.csv",
            "meta": {"time_period": "日", "value_meaning": "销售额（元）", "description": "某电商店铺2024年每日销售额"},
            "generator": lambda: pd.DataFrame({
                "日期": pd.date_range("2024-01-01", periods=90, freq="D"),
                "销售额": [5000 + i*10 + (i%7)*800 for i in range(90)],
            }),
        },
        {
            "file": "stock_price.csv",
            "meta": {"time_period": "日", "value_meaning": "收盘价（元）", "description": "某科技公司2024年上半年股票收盘价"},
            "generator": lambda: pd.DataFrame({
                "日期": pd.date_range("2024-01-01", periods=120, freq="B"),
                "收盘价": [100 + i*0.5 + (i%20)*2 - (i%15)*1.5 for i in range(120)],
            }),
        },
        {
            "file": "temperature.csv",
            "meta": {"time_period": "小时", "value_meaning": "气温（摄氏度）", "description": "某城市夏季每小时气温记录"},
            "generator": lambda: pd.DataFrame({
                "时间": pd.date_range("2024-07-01", periods=168, freq="h"),
                "气温": [25 + 8*(i%24)/24 + (i//24)*0.5 for i in range(168)],
            }),
        },
        {
            "file": "website_traffic.csv",
            "meta": {"time_period": "小时", "value_meaning": "访问量（PV）", "description": "某网站一周内每小时页面访问量"},
            "generator": lambda: pd.DataFrame({
                "时间": pd.date_range("2024-06-01", periods=168, freq="h"),
                "访问量": [1000 + (i%24)*200 + (i//24)*100 for i in range(168)],
            }),
        },
        {
            "file": "sensor_reading.csv",
            "meta": {"time_period": "分钟", "value_meaning": "振动幅度（mm/s）", "description": "工厂设备传感器每分钟振动幅度"},
            "generator": lambda: pd.DataFrame({
                "时间": pd.date_range("2024-06-01 08:00", periods=1440, freq="min"),
                "振动幅度": [0.5 + 0.3*(i%60)/60 + (i//60)*0.01 for i in range(1440)],
            }),
        },
    ]

    for cfg in configs:
        df = cfg["generator"]()
        df.to_csv(out / cfg["file"], index=False, encoding="utf-8-sig")
        with open(out / f"{cfg['file'].replace('.csv', '_meta.json')}", "w", encoding="utf-8") as f:
            json.dump(cfg["meta"], f, ensure_ascii=False, indent=2)
        print(f"[Timeseries] {cfg['file']} generated.")


# --------------------------------------------------------------------------- #
# 2. Table (multidimensional)
# --------------------------------------------------------------------------- #
def gen_table():
    out = BASE / "table"
    out.mkdir(parents=True, exist_ok=True)

    configs = [
        {
            "file": "employee_info.csv",
            "meta": {"row_meaning": "每位员工", "column_meaning": "员工的基本信息、职位、薪资等属性", "description": "某公司100名员工的人事档案"},
            "generator": lambda: pd.DataFrame({
                "员工编号": [f"EMP_{i:04d}" for i in range(1, 101)],
                "姓名": [f"员工_{i}" for i in range(1, 101)],
                "部门": [["技术部", "销售部", "市场部", "财务部", "人事部"][i % 5] for i in range(100)],
                "职位": [["工程师", "经理", "主管", "专员", "总监"][i % 5] for i in range(100)],
                "学历": [["本科", "硕士", "博士", "本科", "硕士"][i % 5] for i in range(100)],
                "入职年份": [2018 + i % 7 for i in range(100)],
                "月薪": [8000 + i * 100 + (i % 5) * 2000 for i in range(100)],
                "绩效评分": [60 + (i % 40) for i in range(100)],
                "是否在职": [True if i % 10 != 0 else False for i in range(100)],
            }),
        },
        {
            "file": "product_sales.csv",
            "meta": {"row_meaning": "每个产品", "column_meaning": "产品的销售属性与业绩指标", "description": "某公司50款产品的季度销售数据"},
            "generator": lambda: pd.DataFrame({
                "产品编号": [f"PROD_{i:03d}" for i in range(1, 51)],
                "产品名称": [f"产品_{i}" for i in range(1, 51)],
                "类别": [["电子", "家居", "服饰", "食品", "美妆"][i % 5] for i in range(50)],
                "Q1销量": [100 + i * 5 for i in range(50)],
                "Q2销量": [120 + i * 4 for i in range(50)],
                "Q3销量": [150 + i * 6 for i in range(50)],
                "Q4销量": [200 + i * 8 for i in range(50)],
                "单价": [50 + i * 10 for i in range(50)],
                "库存": [500 - i * 5 for i in range(50)],
            }),
        },
        {
            "file": "customer_satisfaction.csv",
            "meta": {"row_meaning": "每位参与调研的客户", "column_meaning": "客户对各维度的满意度评分", "description": "200名客户对服务满意度的问卷结果"},
            "generator": lambda: pd.DataFrame({
                "客户ID": [f"CUST_{i:04d}" for i in range(1, 201)],
                "服务态度评分": [3 + i % 3 for i in range(200)],
                "产品质量评分": [3 + (i + 1) % 3 for i in range(200)],
                "物流速度评分": [3 + (i + 2) % 3 for i in range(200)],
                "售后支持评分": [3 + (i + 3) % 3 for i in range(200)],
                "整体满意度": [3 + (i + 4) % 3 for i in range(200)],
                "是否推荐": ["是" if i % 4 != 0 else "否" for i in range(200)],
            }),
        },
        {
            "file": "hospital_patients.csv",
            "meta": {"row_meaning": "每位住院患者", "column_meaning": "患者的入院信息、诊断、治疗与费用", "description": "某医院肿瘤血液科80名患者的住院记录"},
            "generator": lambda: pd.DataFrame({
                "病历号": [f"PAT_{i:04d}" for i in range(1, 81)],
                "姓名": [f"患者_{i}" for i in range(1, 81)],
                "性别": ["男" if i % 2 == 0 else "女" for i in range(80)],
                "年龄": [30 + i % 60 for i in range(80)],
                "科室": ["肿瘤血液科" for _ in range(80)],
                "入院日期": [(datetime(2024, 1, 1) + timedelta(days=i % 180)).strftime("%Y-%m-%d") for i in range(80)],
                "主要诊断": [["肺癌", "乳腺癌", "白血病", "淋巴瘤", "胃癌"][i % 5] for i in range(80)],
                "住院天数": [3 + i % 20 for i in range(80)],
                "总费用": [5000 + i * 500 for i in range(80)],
                "是否手术": ["是" if i % 3 == 0 else "否" for i in range(80)],
            }),
        },
        {
            "file": "ecommerce_orders.csv",
            "meta": {"row_meaning": "每个订单", "column_meaning": "订单的交易信息、商品与物流状态", "description": "某电商平台150个订单的详细信息"},
            "generator": lambda: pd.DataFrame({
                "订单号": [f"ORD_{i:05d}" for i in range(1, 151)],
                "下单时间": [(datetime(2024, 6, 1) + timedelta(hours=i % 720)).strftime("%Y-%m-%d %H:%M") for i in range(150)],
                "用户ID": [f"USER_{i%50:04d}" for i in range(150)],
                "商品类别": [["数码", "服饰", "食品", "家居", "美妆"][i % 5] for i in range(150)],
                "订单金额": [50 + i * 10 for i in range(150)],
                "支付方式": [["支付宝", "微信支付", "信用卡", "花呗", "货到付款"][i % 5] for i in range(150)],
                "物流状态": [["已签收", "运输中", "待发货", "已取消", "退货中"][i % 5] for i in range(150)],
                "是否优惠券": ["是" if i % 4 == 0 else "否" for i in range(150)],
            }),
        },
    ]

    for cfg in configs:
        df = cfg["generator"]()
        df.to_csv(out / cfg["file"], index=False, encoding="utf-8-sig")
        with open(out / f"{cfg['file'].replace('.csv', '_meta.json')}", "w", encoding="utf-8") as f:
            json.dump(cfg["meta"], f, ensure_ascii=False, indent=2)
        print(f"[Table] {cfg['file']} generated.")


# --------------------------------------------------------------------------- #
# 3. JSON
# --------------------------------------------------------------------------- #
def gen_json():
    out = BASE / "json"
    out.mkdir(parents=True, exist_ok=True)

    configs = [
        {
            "file": "user_behavior_logs.json",
            "meta": {
                "description": "用户在App内的行为日志",
                "key_descriptions": {
                    "user_id": "用户唯一标识",
                    "event": "行为事件类型（点击、浏览、购买）",
                    "timestamp": "事件发生时间戳",
                    "page": "行为发生的页面",
                    "duration_ms": "停留时长（毫秒）",
                },
            },
            "generator": lambda: [
                {
                    "user_id": f"U_{i:04d}",
                    "event": ["click", "view", "purchase", "share"][i % 4],
                    "timestamp": (datetime(2024, 6, 1) + timedelta(minutes=i * 5)).isoformat(),
                    "page": ["/home", "/product", "/cart", "/checkout"][i % 4],
                    "duration_ms": 1000 + i * 100,
                }
                for i in range(50)
            ],
        },
        {
            "file": "api_responses.json",
            "meta": {
                "description": "第三方天气API的响应数据",
                "key_descriptions": {
                    "city": "查询城市",
                    "date": "预报日期",
                    "temperature_high": "最高温度（摄氏度）",
                    "temperature_low": "最低温度（摄氏度）",
                    "weather": "天气状况",
                    "humidity": "相对湿度（%）",
                },
            },
            "generator": lambda: [
                {
                    "city": ["北京", "上海", "广州", "深圳", "杭州"][i % 5],
                    "date": (datetime(2024, 7, 1) + timedelta(days=i)).strftime("%Y-%m-%d"),
                    "temperature_high": 30 + i % 10,
                    "temperature_low": 20 + i % 8,
                    "weather": ["晴", "多云", "小雨", "雷阵雨", "阴"][i % 5],
                    "humidity": 40 + i % 40,
                }
                for i in range(30)
            ],
        },
        {
            "file": "app_config.json",
            "meta": {
                "description": "某SaaS系统的租户级配置项",
                "key_descriptions": {
                    "tenant_id": "租户唯一标识",
                    "feature_flags": "功能开关集合",
                    "quota": "资源配额限制",
                    "theme": "界面主题设置",
                    "notification": "通知渠道配置",
                },
            },
            "generator": lambda: [
                {
                    "tenant_id": f"TENANT_{i:03d}",
                    "feature_flags": {"ai_assistant": i % 2 == 0, "dark_mode": i % 3 == 0, "sso": i % 5 == 0},
                    "quota": {"users": 10 + i * 5, "storage_gb": 50 + i * 10},
                    "theme": ["light", "dark", "auto"][i % 3],
                    "notification": {"email": True, "sms": i % 2 == 0, "webhook": i % 3 == 0},
                }
                for i in range(20)
            ],
        },
        {
            "file": "social_media_posts.json",
            "meta": {
                "description": "社交媒体平台的帖子数据",
                "key_descriptions": {
                    "post_id": "帖子唯一标识",
                    "author": "作者用户名",
                    "content": "帖子文本内容",
                    "posted_at": "发布时间",
                    "likes": "点赞数",
                    "shares": "转发数",
                    "comments": "评论数",
                },
            },
            "generator": lambda: [
                {
                    "post_id": f"POST_{i:05d}",
                    "author": f"user_{i%20:03d}",
                    "content": f"这是一条关于话题{i%10}的示例帖子。",
                    "posted_at": (datetime(2024, 5, 1) + timedelta(hours=i)).isoformat(),
                    "likes": 10 + i * 2,
                    "shares": i % 20,
                    "comments": 5 + i % 10,
                }
                for i in range(60)
            ],
        },
        {
            "file": "iot_device_status.json",
            "meta": {
                "description": "物联网设备的实时状态上报",
                "key_descriptions": {
                    "device_id": "设备唯一标识",
                    "device_type": "设备类型（传感器、摄像头、网关）",
                    "status": "在线状态",
                    "battery_pct": "电池电量百分比",
                    "temperature": "设备温度（摄氏度）",
                    "last_seen": "最近上报时间",
                },
            },
            "generator": lambda: [
                {
                    "device_id": f"DEV_{i:04d}",
                    "device_type": ["sensor", "camera", "gateway", "lock", "meter"][i % 5],
                    "status": "online" if i % 10 != 0 else "offline",
                    "battery_pct": 100 - i % 50,
                    "temperature": 20 + i % 30,
                    "last_seen": (datetime(2024, 6, 15) + timedelta(minutes=i * 10)).isoformat(),
                }
                for i in range(40)
            ],
        },
    ]

    for cfg in configs:
        data = cfg["generator"]()
        with open(out / cfg["file"], "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        with open(out / f"{cfg['file'].replace('.json', '_meta.json')}", "w", encoding="utf-8") as f:
            json.dump(cfg["meta"], f, ensure_ascii=False, indent=2)
        print(f"[JSON] {cfg['file']} generated.")


# --------------------------------------------------------------------------- #
# 4. Network
# --------------------------------------------------------------------------- #
def gen_network():
    out = BASE / "network"
    out.mkdir(parents=True, exist_ok=True)

    configs = [
        {
            "file": "social_network.json",
            "meta": {
                "description": "某企业内部员工的社交网络关系",
                "node_meaning": "员工",
                "edge_meaning": "两人之间存在直接工作协作关系",
                "node_attr_meaning": "员工的部门、职级、入职年限",
                "edge_attr_meaning": "协作频次（近半年邮件往来次数）",
            },
            "generator": lambda: {
                "nodes": [
                    {"id": f"EMP_{i:03d}", "department": ["技术", "销售", "市场", "人事", "财务"][i % 5], "level": i % 5 + 1, "tenure_years": i % 10}
                    for i in range(30)
                ],
                "edges": [
                    {"source": f"EMP_{i%30:03d}", "target": f"EMP_{(i+1)%30:03d}", "weight": 1 + i % 10}
                    for i in range(50)
                ],
            },
        },
        {
            "file": "supply_chain.json",
            "meta": {
                "description": "某制造业企业的供应链上下游关系",
                "node_meaning": "供应商、制造商、分销商或零售商",
                "edge_meaning": "货物从上游流向下游的供应关系",
                "node_attr_meaning": "节点类型、所在地区、年交易额",
                "edge_attr_meaning": "物流批次频率、平均交货周期（天）",
            },
            "generator": lambda: {
                "nodes": [
                    {"id": f"NODE_{i:03d}", "type": ["supplier", "manufacturer", "distributor", "retailer"][i % 4], "region": ["华东", "华南", "华北", "西南"][i % 4], "annual_volume": 100 + i * 50}
                    for i in range(20)
                ],
                "edges": [
                    {"source": f"NODE_{i%20:03d}", "target": f"NODE_{(i+2)%20:03d}", "frequency": 1 + i % 5, "lead_time_days": 3 + i % 10}
                    for i in range(30)
                ],
            },
        },
        {
            "file": "knowledge_graph.json",
            "meta": {
                "description": "医疗领域的知识图谱片段",
                "node_meaning": "医学概念（疾病、症状、药物、检查）",
                "edge_meaning": "概念之间的医学关系",
                "node_attr_meaning": "概念类别、置信度、来源文献",
                "edge_attr_meaning": "关系类型、支持证据数量",
            },
            "generator": lambda: {
                "nodes": [
                    {"id": f"CONCEPT_{i:03d}", "category": ["disease", "symptom", "drug", "test", "gene"][i % 5], "confidence": 0.7 + (i % 30) / 100, "source": f"PMID_{1000+i}"}
                    for i in range(25)
                ],
                "edges": [
                    {"source": f"CONCEPT_{i%25:03d}", "target": f"CONCEPT_{(i+3)%25:03d}", "relation": ["causes", "treats", "indicates", "interacts_with", "associates_with"][i % 5], "evidence_count": 1 + i % 8}
                    for i in range(35)
                ],
            },
        },
        {
            "file": "transport_network.json",
            "meta": {
                "description": "某城市的公共交通网络（地铁+公交换乘）",
                "node_meaning": "交通站点（地铁站或公交枢纽）",
                "edge_meaning": "两站点之间存在直达线路",
                "node_attr_meaning": "站点类型、所属线路、日均客流量",
                "edge_attr_meaning": "线路类型、平均行程时间（分钟）",
            },
            "generator": lambda: {
                "nodes": [
                    {"id": f"STATION_{i:03d}", "type": ["metro", "bus_hub", "transfer"][i % 3], "line": f"Line {1 + i % 5}", "daily_passengers": 5000 + i * 500}
                    for i in range(25)
                ],
                "edges": [
                    {"source": f"STATION_{i%25:03d}", "target": f"STATION_{(i+1)%25:03d}", "line_type": ["metro", "bus", "express"][i % 3], "travel_time_min": 5 + i % 20}
                    for i in range(40)
                ],
            },
        },
        {
            "file": "citation_network.json",
            "meta": {
                "description": "某研究领域近5年的论文引用关系",
                "node_meaning": "学术论文",
                "edge_meaning": "论文A引用了论文B",
                "node_attr_meaning": "发表年份、期刊、被引次数、研究方向",
                "edge_attr_meaning": "引用语境（背景、方法、结果）",
            },
            "generator": lambda: {
                "nodes": [
                    {"id": f"PAPER_{i:03d}", "year": 2020 + i % 5, "journal": ["Nature", "Science", "IEEE", "ACM", "Cell"][i % 5], "citations": 10 + i * 3, "field": ["AI", "Bio", "Physics", "Chem", "Math"][i % 5]}
                    for i in range(30)
                ],
                "edges": [
                    {"source": f"PAPER_{i%30:03d}", "target": f"PAPER_{(i+5)%30:03d}", "context": ["background", "method", "result", "comparison"][i % 4]}
                    for i in range(45)
                ],
            },
        },
    ]

    for cfg in configs:
        data = cfg["generator"]()
        with open(out / cfg["file"], "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        with open(out / f"{cfg['file'].replace('.json', '_meta.json')}", "w", encoding="utf-8") as f:
            json.dump(cfg["meta"], f, ensure_ascii=False, indent=2)
        print(f"[Network] {cfg['file']} generated.")


if __name__ == "__main__":
    gen_timeseries()
    gen_table()
    gen_json()
    gen_network()
    print("\nAll 20 sample datasets generated successfully.")
