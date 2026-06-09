"""Generate 4 types of sample data with rich nested metadata."""
from __future__ import annotations

import json
import os
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd

BASE = Path(__file__).resolve().parents[1] / "data" / "samples"
INDEX: list[dict] = []


def save_meta(out_dir: Path, meta: dict):
    with open(out_dir / "meta.json", "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)


def register(data_type: str, slug: str, title: str, description: str):
    INDEX.append({
        "data_type": data_type,
        "slug": slug,
        "title": title,
        "description": description,
        "path": f"data/samples/{data_type}/{slug}",
    })


# =============================================================================
# 1. Timeseries
# =============================================================================
def gen_timeseries():
    out = BASE / "timeseries"
    out.mkdir(parents=True, exist_ok=True)

    # ---- 1.1 电商销售（多字段时序） ----
    slug = "sales_daily"
    d = out / slug
    d.mkdir(exist_ok=True)
    df = pd.DataFrame({
        "日期": pd.date_range("2024-01-01", periods=90, freq="D"),
        "销售额": [5000 + i*10 + (i%7)*800 for i in range(90)],
        "订单量": [80 + i//3 + (i%7)*15 for i in range(90)],
        "客单价": [62 + (i%10)*2 for i in range(90)],
        "退货率": [0.03 + (i%30)/1000 for i in range(90)],
    })
    df.to_csv(d / "data.csv", index=False, encoding="utf-8-sig")
    meta = {
        "data_type": "timeseries",
        "title": "电商每日销售时序数据",
        "description": "某电商店铺2024年第一季度每日销售核心指标，包含销售额、订单量、客单价及退货率。",
        "schema": {
            "time_field": {
                "name": "日期",
                "description": "交易发生的日期",
                "format": "YYYY-MM-DD",
                "period": "日"
            },
            "value_fields": [
                {"name": "销售额", "description": "当日所有成交订单的总金额", "type": "numeric", "unit": "元", "aggregation": "sum", "statistics": {"min": 4500, "max": 15000, "mean": 8500}},
                {"name": "订单量", "description": "当日成交的订单笔数", "type": "integer", "unit": "笔", "aggregation": "sum"},
                {"name": "客单价", "description": "当日每笔订单的平均金额", "type": "numeric", "unit": "元", "formula": "销售额 / 订单量"},
                {"name": "退货率", "description": "当日退货订单占成交订单的比例", "type": "numeric", "unit": "比例", "range": [0, 1]},
            ]
        }
    }
    save_meta(d, meta)
    register("timeseries", slug, meta["title"], meta["description"])

    # ---- 1.2 股票行情（高频时序） ----
    slug = "stock_intraday"
    d = out / slug
    d.mkdir(exist_ok=True)
    df = pd.DataFrame({
        "时间": pd.date_range("2024-06-01 09:30", periods=240, freq="min"),
        "开盘价": [100 + i*0.02 for i in range(240)],
        "最高价": [101 + i*0.02 + (i%10)*0.1 for i in range(240)],
        "最低价": [99 + i*0.02 - (i%10)*0.1 for i in range(240)],
        "收盘价": [100 + i*0.02 + (i%5)*0.05 for i in range(240)],
        "成交量": [1000 + i*10 for i in range(240)],
    })
    df.to_csv(d / "data.csv", index=False, encoding="utf-8-sig")
    meta = {
        "data_type": "timeseries",
        "title": "股票日内分时行情",
        "description": "某科技公司2024年6月1日交易时段（9:30-15:30）的分钟级K线数据，含OHLC及成交量。",
        "schema": {
            "time_field": {"name": "时间", "description": "交易分钟", "format": "YYYY-MM-DD HH:MM", "period": "分钟"},
            "value_fields": [
                {"name": "开盘价", "description": "该分钟第一笔成交价", "type": "numeric", "unit": "元"},
                {"name": "最高价", "description": "该分钟内最高成交价", "type": "numeric", "unit": "元"},
                {"name": "最低价", "description": "该分钟内最低成交价", "type": "numeric", "unit": "元"},
                {"name": "收盘价", "description": "该分钟最后一笔成交价", "type": "numeric", "unit": "元"},
                {"name": "成交量", "description": "该分钟成交的总手数", "type": "integer", "unit": "手"},
            ]
        }
    }
    save_meta(d, meta)
    register("timeseries", slug, meta["title"], meta["description"])

    # ---- 1.3 传感器（多设备多指标） ----
    slug = "sensor_multidevice"
    d = out / slug
    d.mkdir(exist_ok=True)
    records = []
    for hour in range(24):
        for dev in ["DEV_A", "DEV_B", "DEV_C"]:
            records.append({
                "时间": (datetime(2024, 6, 1) + timedelta(hours=hour)).strftime("%Y-%m-%d %H:%M"),
                "设备ID": dev,
                "温度": 25 + hour * 0.5 + (ord(dev[-1]) - 65) * 2,
                "湿度": 40 + hour * 0.3,
                "压力": 1013 + (hour % 5),
                "振动": 0.1 + (hour % 7) * 0.05,
            })
    df = pd.DataFrame(records)
    df.to_csv(d / "data.csv", index=False, encoding="utf-8-sig")
    meta = {
        "data_type": "timeseries",
        "title": "工业传感器多设备时序数据",
        "description": "3台工业设备24小时连续采集的温度、湿度、压力及振动数据。",
        "schema": {
            "time_field": {"name": "时间", "description": "数据采集时间", "format": "YYYY-MM-DD HH:MM", "period": "小时"},
            "value_fields": [
                {"name": "温度", "description": "设备表面温度", "type": "numeric", "unit": "摄氏度", "threshold": {"warning": 45, "critical": 55}},
                {"name": "湿度", "description": "环境相对湿度", "type": "numeric", "unit": "%"},
                {"name": "压力", "description": "设备内部气压", "type": "numeric", "unit": "hPa"},
                {"name": "振动", "description": "设备振动幅度", "type": "numeric", "unit": "mm/s", "threshold": {"warning": 0.5, "critical": 1.0}},
            ],
            "dimension_fields": [
                {"name": "设备ID", "description": "传感器所属设备编号", "type": "categorical", "values": ["DEV_A", "DEV_B", "DEV_C"]}
            ]
        }
    }
    save_meta(d, meta)
    register("timeseries", slug, meta["title"], meta["description"])

    # ---- 1.4 网站流量（带来源维度） ----
    slug = "traffic_source"
    d = out / slug
    d.mkdir(exist_ok=True)
    records = []
    for day in range(30):
        for src in ["自然搜索", "付费广告", "社交媒体", "直接访问", "邮件营销"]:
            records.append({
                "日期": (datetime(2024, 6, 1) + timedelta(days=day)).strftime("%Y-%m-%d"),
                "来源": src,
                "访问量": 500 + day * 10 + (ord(src[0]) % 5) * 200,
                "跳出率": 0.3 + (day % 10) / 100,
                "平均停留": 60 + (day % 20) * 5,
            })
    df = pd.DataFrame(records)
    df.to_csv(d / "data.csv", index=False, encoding="utf-8-sig")
    meta = {
        "data_type": "timeseries",
        "title": "网站流量来源分日时序",
        "description": "某网站30天内按流量来源（5个渠道）拆分的日访问量、跳出率和平均停留时长。",
        "schema": {
            "time_field": {"name": "日期", "description": "统计日期", "format": "YYYY-MM-DD", "period": "日"},
            "value_fields": [
                {"name": "访问量", "description": "该来源当日的独立访客数", "type": "integer", "unit": "UV"},
                {"name": "跳出率", "description": "只看了一页就离开的访客比例", "type": "numeric", "unit": "比例", "range": [0, 1]},
                {"name": "平均停留", "description": "访客在站内的平均停留时间", "type": "numeric", "unit": "秒"},
            ],
            "dimension_fields": [
                {"name": "来源", "description": "流量来源渠道", "type": "categorical", "values": ["自然搜索", "付费广告", "社交媒体", "直接访问", "邮件营销"]}
            ]
        }
    }
    save_meta(d, meta)
    register("timeseries", slug, meta["title"], meta["description"])

    # ---- 1.5 气象（嵌套JSON value） ----
    slug = "weather_nested"
    d = out / slug
    d.mkdir(exist_ok=True)
    records = []
    for i in range(30):
        records.append({
            "日期": (datetime(2024, 7, 1) + timedelta(days=i)).strftime("%Y-%m-%d"),
            "温度": json.dumps({"最高": 30 + i % 10, "最低": 20 + i % 8, "平均": 25 + i % 6}),
            "降水": json.dumps({"概率": 0.1 + (i % 5) * 0.15, "量级": ["无", "小雨", "中雨", "大雨"][i % 4]}),
            "风速": 2 + i % 8,
            "空气质量": ["优", "良", "轻度污染", "中度污染"][i % 4],
        })
    df = pd.DataFrame(records)
    df.to_csv(d / "data.csv", index=False, encoding="utf-8-sig")
    meta = {
        "data_type": "timeseries",
        "title": "城市气象日数据（含嵌套JSON字段）",
        "description": "某城市30天气象记录。温度字段为JSON格式（含最高/最低/平均），降水字段为JSON格式（含概率和量级）。",
        "schema": {
            "time_field": {"name": "日期", "description": "预报日期", "format": "YYYY-MM-DD", "period": "日"},
            "value_fields": [
                {"name": "温度", "description": "当日温度统计，JSON格式内含最高/最低/平均", "type": "json", "inner_schema": {"最高": {"type": "numeric", "unit": "摄氏度"}, "最低": {"type": "numeric", "unit": "摄氏度"}, "平均": {"type": "numeric", "unit": "摄氏度"}}},
                {"name": "降水", "description": "当日降水信息，JSON格式内含概率和量级", "type": "json", "inner_schema": {"概率": {"type": "numeric", "unit": "比例", "range": [0, 1]}, "量级": {"type": "categorical", "values": ["无", "小雨", "中雨", "大雨"]}}},
                {"name": "风速", "description": "当日平均风速", "type": "numeric", "unit": "m/s"},
                {"name": "空气质量", "description": "当日AQI等级", "type": "categorical", "values": ["优", "良", "轻度污染", "中度污染"]},
            ]
        }
    }
    save_meta(d, meta)
    register("timeseries", slug, meta["title"], meta["description"])


# =============================================================================
# 2. Table
# =============================================================================
def gen_table():
    out = BASE / "table"
    out.mkdir(parents=True, exist_ok=True)

    # ---- 2.1 员工信息 ----
    slug = "employee_info"
    d = out / slug
    d.mkdir(exist_ok=True)
    df = pd.DataFrame({
        "员工编号": [f"EMP_{i:04d}" for i in range(1, 101)],
        "姓名": [f"员工_{i}" for i in range(1, 101)],
        "性别": ["男" if i % 2 == 0 else "女" for i in range(100)],
        "年龄": [22 + i % 40 for i in range(100)],
        "部门": [["技术部", "销售部", "市场部", "财务部", "人事部"][i % 5] for i in range(100)],
        "职位": [["工程师", "经理", "主管", "专员", "总监"][i % 5] for i in range(100)],
        "学历": [["本科", "硕士", "博士", "本科", "硕士"][i % 5] for i in range(100)],
        "入职年份": [2018 + i % 7 for i in range(100)],
        "月薪": [8000 + i * 100 + (i % 5) * 2000 for i in range(100)],
        "绩效评分": [60 + (i % 40) for i in range(100)],
        "是否在职": [True if i % 10 != 0 else False for i in range(100)],
    })
    df.to_csv(d / "data.csv", index=False, encoding="utf-8-sig")
    meta = {
        "data_type": "table",
        "title": "企业员工人事档案",
        "description": "某公司100名员工的完整人事信息，涵盖基础属性、岗位信息及薪酬绩效。",
        "schema": {
            "row_meaning": "每位在职或已离职的员工",
            "column_meaning": "员工的各项人事属性",
            "columns": [
                {"name": "员工编号", "description": "公司内唯一标识", "type": "string", "role": "primary_key", "example": "EMP_0001"},
                {"name": "姓名", "description": "员工中文名", "type": "string", "role": "label"},
                {"name": "性别", "description": "生理性别", "type": "categorical", "values": ["男", "女"]},
                {"name": "年龄", "description": "当前周岁", "type": "integer", "unit": "岁", "range": [22, 62]},
                {"name": "部门", "description": "所属一级部门", "type": "categorical", "values": ["技术部", "销售部", "市场部", "财务部", "人事部"]},
                {"name": "职位", "description": "岗位职级", "type": "categorical", "values": ["工程师", "经理", "主管", "专员", "总监"]},
                {"name": "学历", "description": "最高学历", "type": "categorical", "values": ["本科", "硕士", "博士"]},
                {"name": "入职年份", "description": "首次加入公司年份", "type": "integer", "unit": "年"},
                {"name": "月薪", "description": "税前固定月薪", "type": "numeric", "unit": "元", "aggregation": "avg", "statistics": {"min": 8000, "max": 18000}},
                {"name": "绩效评分", "description": "最近年度绩效考核得分", "type": "integer", "unit": "分", "range": [60, 100]},
                {"name": "是否在职", "description": "当前劳动关系状态", "type": "boolean", "values": [True, False]},
            ]
        }
    }
    save_meta(d, meta)
    register("table", slug, meta["title"], meta["description"])

    # ---- 2.2 产品销售 ----
    slug = "product_sales"
    d = out / slug
    d.mkdir(exist_ok=True)
    df = pd.DataFrame({
        "产品编号": [f"PROD_{i:03d}" for i in range(1, 51)],
        "产品名称": [f"产品_{i}" for i in range(1, 51)],
        "类别": [["电子", "家居", "服饰", "食品", "美妆"][i % 5] for i in range(50)],
        "Q1销量": [100 + i * 5 for i in range(50)],
        "Q2销量": [120 + i * 4 for i in range(50)],
        "Q3销量": [150 + i * 6 for i in range(50)],
        "Q4销量": [200 + i * 8 for i in range(50)],
        "单价": [50 + i * 10 for i in range(50)],
        "成本": [30 + i * 6 for i in range(50)],
        "库存": [500 - i * 5 for i in range(50)],
    })
    df.to_csv(d / "data.csv", index=False, encoding="utf-8-sig")
    meta = {
        "data_type": "table",
        "title": "产品季度销售数据",
        "description": "某公司50款产品在四个季度的销量、定价、成本及库存数据。",
        "schema": {
            "row_meaning": "每一款独立SKU产品",
            "column_meaning": "产品的销售与财务属性",
            "columns": [
                {"name": "产品编号", "description": "SKU唯一编码", "type": "string", "role": "primary_key"},
                {"name": "产品名称", "description": "内部命名", "type": "string"},
                {"name": "类别", "description": "所属商品大类", "type": "categorical", "values": ["电子", "家居", "服饰", "食品", "美妆"]},
                {"name": "Q1销量", "description": "第一季度销售数量", "type": "integer", "unit": "件", "aggregation": "sum"},
                {"name": "Q2销量", "description": "第二季度销售数量", "type": "integer", "unit": "件", "aggregation": "sum"},
                {"name": "Q3销量", "description": "第三季度销售数量", "type": "integer", "unit": "件", "aggregation": "sum"},
                {"name": "Q4销量", "description": "第四季度销售数量", "type": "integer", "unit": "件", "aggregation": "sum"},
                {"name": "单价", "description": "对外零售价", "type": "numeric", "unit": "元"},
                {"name": "成本", "description": "生产成本", "type": "numeric", "unit": "元"},
                {"name": "库存", "description": "当前可售库存", "type": "integer", "unit": "件"},
            ]
        }
    }
    save_meta(d, meta)
    register("table", slug, meta["title"], meta["description"])

    # ---- 2.3 客户满意度 ----
    slug = "customer_satisfaction"
    d = out / slug
    d.mkdir(exist_ok=True)
    df = pd.DataFrame({
        "客户ID": [f"CUST_{i:04d}" for i in range(1, 201)],
        "服务态度评分": [3 + i % 3 for i in range(200)],
        "产品质量评分": [3 + (i + 1) % 3 for i in range(200)],
        "物流速度评分": [3 + (i + 2) % 3 for i in range(200)],
        "售后支持评分": [3 + (i + 3) % 3 for i in range(200)],
        "整体满意度": [3 + (i + 4) % 3 for i in range(200)],
        "是否推荐": ["是" if i % 4 != 0 else "否" for i in range(200)],
        "会员等级": [["普通", "银牌", "金牌", "钻石"][i % 4] for i in range(200)],
        "注册时长": [1 + i % 36 for i in range(200)],
    })
    df.to_csv(d / "data.csv", index=False, encoding="utf-8-sig")
    meta = {
        "data_type": "table",
        "title": "客户满意度问卷",
        "description": "200名客户对5个服务维度的满意度评分及客户属性信息。",
        "schema": {
            "row_meaning": "每一位参与调研的客户",
            "column_meaning": "客户对各维度的满意度评分及属性",
            "columns": [
                {"name": "客户ID", "description": "客户唯一标识", "type": "string", "role": "primary_key"},
                {"name": "服务态度评分", "description": "对客服态度的满意程度", "type": "integer", "unit": "分(1-5)", "range": [1, 5]},
                {"name": "产品质量评分", "description": "对收到商品质量的满意程度", "type": "integer", "unit": "分(1-5)", "range": [1, 5]},
                {"name": "物流速度评分", "description": "对配送速度的满意程度", "type": "integer", "unit": "分(1-5)", "range": [1, 5]},
                {"name": "售后支持评分", "description": "对售后处理效率的满意程度", "type": "integer", "unit": "分(1-5)", "range": [1, 5]},
                {"name": "整体满意度", "description": "对本次购物的综合满意度", "type": "integer", "unit": "分(1-5)", "range": [1, 5]},
                {"name": "是否推荐", "description": "是否愿意向他人推荐", "type": "categorical", "values": ["是", "否"]},
                {"name": "会员等级", "description": "当前会员级别", "type": "categorical", "values": ["普通", "银牌", "金牌", "钻石"]},
                {"name": "注册时长", "description": "自注册以来的月数", "type": "integer", "unit": "月"},
            ]
        }
    }
    save_meta(d, meta)
    register("table", slug, meta["title"], meta["description"])

    # ---- 2.4 医院患者 ----
    slug = "hospital_patients"
    d = out / slug
    d.mkdir(exist_ok=True)
    df = pd.DataFrame({
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
        "医保类型": [["城镇职工", "城乡居民", "商业保险", "自费"][i % 4] for i in range(80)],
    })
    df.to_csv(d / "data.csv", index=False, encoding="utf-8-sig")
    meta = {
        "data_type": "table",
        "title": "肿瘤血液科住院患者信息",
        "description": "某医院肿瘤血液科80名住院患者的入院信息、诊断、治疗及费用数据。",
        "schema": {
            "row_meaning": "每位住院患者的一次住院记录",
            "column_meaning": "患者的入院信息、诊断、治疗与费用",
            "columns": [
                {"name": "病历号", "description": "院内唯一病历标识", "type": "string", "role": "primary_key"},
                {"name": "姓名", "description": "患者姓名", "type": "string"},
                {"name": "性别", "description": "生理性别", "type": "categorical", "values": ["男", "女"]},
                {"name": "年龄", "description": "入院时周岁", "type": "integer", "unit": "岁"},
                {"name": "科室", "description": "收治科室", "type": "categorical", "values": ["肿瘤血液科"]},
                {"name": "入院日期", "description": "正式入院日期", "type": "date", "format": "YYYY-MM-DD"},
                {"name": "主要诊断", "description": "出院主要诊断", "type": "categorical", "values": ["肺癌", "乳腺癌", "白血病", "淋巴瘤", "胃癌"]},
                {"name": "住院天数", "description": "本次住院总天数", "type": "integer", "unit": "天"},
                {"name": "总费用", "description": "住院期间全部医疗费用", "type": "numeric", "unit": "元", "aggregation": "sum"},
                {"name": "是否手术", "description": "住院期间是否接受手术治疗", "type": "categorical", "values": ["是", "否"]},
                {"name": "医保类型", "description": "费用结算的医保类别", "type": "categorical", "values": ["城镇职工", "城乡居民", "商业保险", "自费"]},
            ]
        }
    }
    save_meta(d, meta)
    register("table", slug, meta["title"], meta["description"])

    # ---- 2.5 电商订单 ----
    slug = "ecommerce_orders"
    d = out / slug
    d.mkdir(exist_ok=True)
    df = pd.DataFrame({
        "订单号": [f"ORD_{i:05d}" for i in range(1, 151)],
        "下单时间": [(datetime(2024, 6, 1) + timedelta(hours=i % 720)).strftime("%Y-%m-%d %H:%M") for i in range(150)],
        "用户ID": [f"USER_{i%50:04d}" for i in range(150)],
        "商品类别": [["数码", "服饰", "食品", "家居", "美妆"][i % 5] for i in range(150)],
        "订单金额": [50 + i * 10 for i in range(150)],
        "支付方式": [["支付宝", "微信支付", "信用卡", "花呗", "货到付款"][i % 5] for i in range(150)],
        "物流状态": [["已签收", "运输中", "待发货", "已取消", "退货中"][i % 5] for i in range(150)],
        "是否优惠券": ["是" if i % 4 == 0 else "否" for i in range(150)],
        "收货城市": [["北京", "上海", "广州", "深圳", "杭州"][i % 5] for i in range(150)],
    })
    df.to_csv(d / "data.csv", index=False, encoding="utf-8-sig")
    meta = {
        "data_type": "table",
        "title": "电商平台订单明细",
        "description": "某电商平台150个订单的交易信息、商品分类、支付与物流状态。",
        "schema": {
            "row_meaning": "每一个独立订单",
            "column_meaning": "订单的交易信息、商品与物流状态",
            "columns": [
                {"name": "订单号", "description": "平台唯一订单编号", "type": "string", "role": "primary_key"},
                {"name": "下单时间", "description": "用户提交订单的时间", "type": "datetime", "format": "YYYY-MM-DD HH:MM"},
                {"name": "用户ID", "description": "下单用户标识", "type": "string"},
                {"name": "商品类别", "description": "订单主商品的类目", "type": "categorical", "values": ["数码", "服饰", "食品", "家居", "美妆"]},
                {"name": "订单金额", "description": "实付金额（含优惠后）", "type": "numeric", "unit": "元", "aggregation": "sum"},
                {"name": "支付方式", "description": "用户选择的支付渠道", "type": "categorical", "values": ["支付宝", "微信支付", "信用卡", "花呗", "货到付款"]},
                {"name": "物流状态", "description": "当前订单物流进度", "type": "categorical", "values": ["已签收", "运输中", "待发货", "已取消", "退货中"]},
                {"name": "是否优惠券", "description": "是否使用了平台优惠券", "type": "categorical", "values": ["是", "否"]},
                {"name": "收货城市", "description": "订单配送目的地城市", "type": "categorical", "values": ["北京", "上海", "广州", "深圳", "杭州"]},
            ]
        }
    }
    save_meta(d, meta)
    register("table", slug, meta["title"], meta["description"])


# =============================================================================
# 3. JSON
# =============================================================================
def gen_json():
    out = BASE / "json"
    out.mkdir(parents=True, exist_ok=True)

    # ---- 3.1 用户行为日志 ----
    slug = "user_event_logs"
    d = out / slug
    d.mkdir(exist_ok=True)
    data = []
    for i in range(1, 51):
        data.append({
            "event_id": f"EVT_{i:05d}",
            "timestamp": (datetime(2024, 6, 1, 8, 0, 0) + timedelta(minutes=i * 15)).isoformat(),
            "user": {
                "user_id": f"USER_{i % 10:04d}",
                "device": {"type": ["mobile", "desktop", "tablet"][i % 3], "os": ["iOS", "Android", "Windows", "macOS"][i % 4], "browser": ["Chrome", "Safari", "Firefox"][i % 3]},
                "location": {"country": "中国", "province": ["北京", "上海", "广东", "浙江"][i % 4], "city": ["北京", "上海", "广州", "深圳", "杭州"][i % 5]},
            },
            "event": {
                "type": ["page_view", "click", "add_to_cart", "purchase", "search"][i % 5],
                "page": {"path": f"/product/{i % 20}", "referrer": ["google", "baidu", "direct", "wechat"][i % 4]},
                "properties": {"duration_sec": 10 + i % 120, "scroll_depth": 0.1 + (i % 10) * 0.1},
            },
        })
    with open(d / "data.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    meta = {
        "data_type": "json",
        "title": "用户行为事件日志",
        "description": "50条用户行为事件，记录用户在网站上的页面浏览、点击、加购、购买和搜索行为，包含用户设备、地理位置及事件属性。",
        "schema": {
            "root_type": "array",
            "item_meaning": "单次用户交互事件",
            "keys": {
                "event_id": {"type": "string", "description": "全局唯一事件ID", "role": "primary_key"},
                "timestamp": {"type": "datetime", "description": "事件发生的ISO8601时间戳", "format": "ISO8601"},
                "user": {
                    "type": "object",
                    "description": "触发事件的用户及设备信息",
                    "keys": {
                        "user_id": {"type": "string", "description": "用户唯一标识"},
                        "device": {
                            "type": "object",
                            "description": "用户使用的设备信息",
                            "keys": {
                                "type": {"type": "categorical", "description": "设备类型", "values": ["mobile", "desktop", "tablet"]},
                                "os": {"type": "categorical", "description": "操作系统", "values": ["iOS", "Android", "Windows", "macOS"]},
                                "browser": {"type": "categorical", "description": "浏览器", "values": ["Chrome", "Safari", "Firefox"]},
                            }
                        },
                        "location": {
                            "type": "object",
                            "description": "用户地理位置",
                            "keys": {
                                "country": {"type": "string", "description": "国家"},
                                "province": {"type": "categorical", "description": "省份", "values": ["北京", "上海", "广东", "浙江"]},
                                "city": {"type": "categorical", "description": "城市", "values": ["北京", "上海", "广州", "深圳", "杭州"]},
                            }
                        },
                    }
                },
                "event": {
                    "type": "object",
                    "description": "事件本身的详细信息",
                    "keys": {
                        "type": {"type": "categorical", "description": "事件类型", "values": ["page_view", "click", "add_to_cart", "purchase", "search"]},
                        "page": {
                            "type": "object",
                            "description": "页面信息",
                            "keys": {
                                "path": {"type": "string", "description": "页面路径"},
                                "referrer": {"type": "categorical", "description": "来源", "values": ["google", "baidu", "direct", "wechat"]},
                            }
                        },
                        "properties": {
                            "type": "object",
                            "description": "事件的量化属性",
                            "keys": {
                                "duration_sec": {"type": "numeric", "description": "页面停留时长", "unit": "秒"},
                                "scroll_depth": {"type": "numeric", "description": "页面滚动深度", "unit": "比例", "range": [0, 1]},
                            }
                        },
                    }
                },
            }
        }
    }
    save_meta(d, meta)
    register("json", slug, meta["title"], meta["description"])

    # ---- 3.2 商品目录（嵌套规格） ----
    slug = "product_catalog"
    d = out / slug
    d.mkdir(exist_ok=True)
    data = []
    for i in range(1, 31):
        data.append({
            "sku_id": f"SKU_{i:04d}",
            "name": f"商品_{i}",
            "category": {"level1": ["电子", "家居", "服饰"][i % 3], "level2": ["手机", "电脑", "家具", "服装"][i % 4]},
            "pricing": {"base_price": 100 + i * 50, "discount": {"type": ["percent", "fixed", "none"][i % 3], "value": [0.1, 20, 0][i % 3]}, "final_price": 100 + i * 50 - [10, 20, 0][i % 3]},
            "attributes": [{"key": "颜色", "value": ["红", "蓝", "黑"][i % 3]}, {"key": "尺寸", "value": ["S", "M", "L"][i % 3]}, {"key": "重量", "value": f"{i * 0.1:.1f}kg"}],
            "reviews": {"count": i * 2, "avg_rating": 3.5 + (i % 5) * 0.3, "tags": [["好评", "物流快"], ["一般"], ["差评", "质量差"], ["性价比高"], ["推荐"]][i % 5]},
            "seller": {"seller_id": f"SLR_{i % 5:03d}", "name": f"商家_{i % 5}", "rating": 4.0 + (i % 5) * 0.2},
        })
    with open(d / "data.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    meta = {
        "data_type": "json",
        "title": "电商平台商品目录",
        "description": "30个商品的详细信息，包含分类层级、定价折扣、属性规格、评价标签及商家信息。",
        "schema": {
            "root_type": "array",
            "item_meaning": "每一个独立商品SKU",
            "keys": {
                "sku_id": {"type": "string", "description": "SKU唯一编号", "role": "primary_key"},
                "name": {"type": "string", "description": "商品名称"},
                "category": {
                    "type": "object",
                    "description": "商品分类层级",
                    "keys": {
                        "level1": {"type": "categorical", "description": "一级类目", "values": ["电子", "家居", "服饰"]},
                        "level2": {"type": "categorical", "description": "二级类目", "values": ["手机", "电脑", "家具", "服装"]},
                    }
                },
                "pricing": {
                    "type": "object",
                    "description": "定价与折扣信息",
                    "keys": {
                        "base_price": {"type": "numeric", "description": "原价", "unit": "元"},
                        "discount": {
                            "type": "object",
                            "description": "折扣规则",
                            "keys": {
                                "type": {"type": "categorical", "description": "折扣类型", "values": ["percent", "fixed", "none"]},
                                "value": {"type": "numeric", "description": "折扣数值"},
                            }
                        },
                        "final_price": {"type": "numeric", "description": "最终售价", "unit": "元"},
                    }
                },
                "attributes": {
                    "type": "array",
                    "description": "商品属性规格列表",
                    "item_schema": {
                        "type": "object",
                        "keys": {
                            "key": {"type": "string", "description": "属性名"},
                            "value": {"type": "string", "description": "属性值"},
                        }
                    }
                },
                "reviews": {
                    "type": "object",
                    "description": "用户评价汇总",
                    "keys": {
                        "count": {"type": "integer", "description": "评价总数"},
                        "avg_rating": {"type": "numeric", "description": "平均评分", "unit": "分(1-5)", "range": [1, 5]},
                        "tags": {"type": "array", "description": "高频评价标签", "item_schema": {"type": "string"}},
                    }
                },
                "seller": {
                    "type": "object",
                    "description": "销售商家信息",
                    "keys": {
                        "seller_id": {"type": "string", "description": "商家ID"},
                        "name": {"type": "string", "description": "商家名称"},
                        "rating": {"type": "numeric", "description": "商家评分", "unit": "分(1-5)", "range": [1, 5]},
                    }
                },
            }
        }
    }
    save_meta(d, meta)
    register("json", slug, meta["title"], meta["description"])

    # ---- 3.3 API响应（嵌套分页） ----
    slug = "api_response"
    d = out / slug
    d.mkdir(exist_ok=True)
    data = {
        "status": "success",
        "pagination": {"page": 1, "page_size": 10, "total": 50, "total_pages": 5},
        "data": [{"id": i, "title": f"文章_{i}", "author": {"id": i % 5, "name": f"作者_{i % 5}", "level": ["初级", "中级", "高级"][i % 3]}, "tags": [f"标签_{i % 5}", f"标签_{(i + 1) % 5}"], "metrics": {"views": i * 100, "likes": i * 10, "comments": i * 2}} for i in range(1, 11)],
    }
    with open(d / "data.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    meta = {
        "data_type": "json",
        "title": "内容平台API分页响应",
        "description": "某内容平台的文章列表API响应，包含分页元数据及嵌套的文章、作者、标签和互动指标。",
        "schema": {
            "root_type": "object",
            "keys": {
                "status": {"type": "categorical", "description": "请求状态", "values": ["success", "error"]},
                "pagination": {
                    "type": "object",
                    "description": "分页元数据",
                    "keys": {
                        "page": {"type": "integer", "description": "当前页码"},
                        "page_size": {"type": "integer", "description": "每页条数"},
                        "total": {"type": "integer", "description": "总记录数"},
                        "total_pages": {"type": "integer", "description": "总页数"},
                    }
                },
                "data": {
                    "type": "array",
                    "description": "文章列表",
                    "item_schema": {
                        "type": "object",
                        "keys": {
                            "id": {"type": "integer", "description": "文章ID"},
                            "title": {"type": "string", "description": "文章标题"},
                            "author": {
                                "type": "object",
                                "description": "作者信息",
                                "keys": {
                                    "id": {"type": "integer", "description": "作者ID"},
                                    "name": {"type": "string", "description": "作者名"},
                                    "level": {"type": "categorical", "description": "作者等级", "values": ["初级", "中级", "高级"]},
                                }
                            },
                            "tags": {"type": "array", "description": "文章标签", "item_schema": {"type": "string"}},
                            "metrics": {
                                "type": "object",
                                "description": "互动指标",
                                "keys": {
                                    "views": {"type": "integer", "description": "浏览量"},
                                    "likes": {"type": "integer", "description": "点赞数"},
                                    "comments": {"type": "integer", "description": "评论数"},
                                }
                            },
                        }
                    }
                },
            }
        }
    }
    save_meta(d, meta)
    register("json", slug, meta["title"], meta["description"])

    # ---- 3.4 配置文件 ----
    slug = "app_config"
    d = out / slug
    d.mkdir(exist_ok=True)
    data = {
        "app_name": "智慧零售系统",
        "version": "2.1.0",
        "environment": "production",
        "database": {"host": "db.example.com", "port": 5432, "name": "retail_db", "pool": {"min": 5, "max": 50, "timeout_sec": 30}},
        "cache": {"provider": "redis", "host": "redis.example.com", "port": 6379, "ttl": {"session": 3600, "product": 300, "order": 60}},
        "features": {"recommendation": {"enabled": True, "algorithm": "collaborative_filtering", "params": {"k": 10, "similarity": "cosine"}}, "ab_test": {"enabled": False, "variants": ["control", "variant_a", "variant_b"]}},
        "logging": {"level": "INFO", "format": "json", "outputs": [{"type": "console"}, {"type": "file", "path": "/var/log/app.log", "rotation": "daily"}]},
    }
    with open(d / "data.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    meta = {
        "data_type": "json",
        "title": "应用系统配置文件",
        "description": "某零售SaaS系统的运行时配置，包含数据库连接池、缓存策略、功能开关及日志输出配置。",
        "schema": {
            "root_type": "object",
            "keys": {
                "app_name": {"type": "string", "description": "应用名称"},
                "version": {"type": "string", "description": "当前版本号"},
                "environment": {"type": "categorical", "description": "运行环境", "values": ["development", "staging", "production"]},
                "database": {
                    "type": "object",
                    "description": "数据库配置",
                    "keys": {
                        "host": {"type": "string", "description": "数据库主机"},
                        "port": {"type": "integer", "description": "端口"},
                        "name": {"type": "string", "description": "数据库名"},
                        "pool": {
                            "type": "object",
                            "description": "连接池参数",
                            "keys": {
                                "min": {"type": "integer", "description": "最小连接数"},
                                "max": {"type": "integer", "description": "最大连接数"},
                                "timeout_sec": {"type": "numeric", "description": "超时时间", "unit": "秒"},
                            }
                        },
                    }
                },
                "cache": {
                    "type": "object",
                    "description": "缓存配置",
                    "keys": {
                        "provider": {"type": "categorical", "description": "缓存提供商", "values": ["redis", "memcached"]},
                        "host": {"type": "string", "description": "缓存主机"},
                        "port": {"type": "integer", "description": "端口"},
                        "ttl": {
                            "type": "object",
                            "description": "各数据类型的TTL",
                            "keys": {
                                "session": {"type": "integer", "description": "会话缓存时长", "unit": "秒"},
                                "product": {"type": "integer", "description": "商品缓存时长", "unit": "秒"},
                                "order": {"type": "integer", "description": "订单缓存时长", "unit": "秒"},
                            }
                        },
                    }
                },
                "features": {
                    "type": "object",
                    "description": "功能模块开关",
                    "keys": {
                        "recommendation": {
                            "type": "object",
                            "description": "推荐系统配置",
                            "keys": {
                                "enabled": {"type": "boolean", "description": "是否启用"},
                                "algorithm": {"type": "categorical", "description": "推荐算法", "values": ["collaborative_filtering", "content_based"]},
                                "params": {
                                    "type": "object",
                                    "description": "算法参数",
                                    "keys": {
                                        "k": {"type": "integer", "description": "近邻数量"},
                                        "similarity": {"type": "categorical", "description": "相似度度量", "values": ["cosine", "pearson"]},
                                    }
                                },
                            }
                        },
                        "ab_test": {
                            "type": "object",
                            "description": "AB测试配置",
                            "keys": {
                                "enabled": {"type": "boolean", "description": "是否启用"},
                                "variants": {"type": "array", "description": "实验组列表", "item_schema": {"type": "string"}},
                            }
                        },
                    }
                },
                "logging": {
                    "type": "object",
                    "description": "日志配置",
                    "keys": {
                        "level": {"type": "categorical", "description": "日志级别", "values": ["DEBUG", "INFO", "WARN", "ERROR"]},
                        "format": {"type": "categorical", "description": "输出格式", "values": ["json", "text"]},
                        "outputs": {
                            "type": "array",
                            "description": "日志输出目标",
                            "item_schema": {
                                "type": "object",
                                "keys": {
                                    "type": {"type": "categorical", "description": "输出类型", "values": ["console", "file"]},
                                    "path": {"type": "string", "description": "文件路径（仅file类型）"},
                                    "rotation": {"type": "categorical", "description": "轮转策略", "values": ["daily", "hourly"]},
                                }
                            }
                        },
                    }
                },
            }
        }
    }
    save_meta(d, meta)
    register("json", slug, meta["title"], meta["description"])

    # ---- 3.5 物流轨迹（嵌套数组） ----
    slug = "logistics_tracking"
    d = out / slug
    d.mkdir(exist_ok=True)
    data = []
    for i in range(1, 21):
        nodes = []
        for j in range(1, 4 + i % 3):
            nodes.append({
                "node": f"节点_{j}",
                "time": (datetime(2024, 6, 10, 10, 0) + timedelta(hours=j * 8 + i)).isoformat(),
                "location": {"province": ["广东", "湖南", "湖北", "河南", "河北"][(i + j) % 5], "city": ["广州", "长沙", "武汉", "郑州", "石家庄"][(i + j) % 5], "lat": 23.0 + i * 0.1, "lng": 113.0 + i * 0.1},
                "status": ["已揽收", "运输中", "到达分拨", "派送中", "已签收"][j - 1],
            })
        data.append({
            "waybill_no": f"WB_{i:06d}",
            "carrier": ["顺丰", "中通", "圆通", "韵达", "申通"][i % 5],
            "sender": {"name": f"寄件人_{i}", "phone": f"138{i:08d}", "address": {"province": "广东", "city": "广州", "detail": f"天河区地址{i}"}},
            "receiver": {"name": f"收件人_{i}", "phone": f"139{i:08d}", "address": {"province": "北京", "city": "北京", "detail": f"朝阳区地址{i}"}},
            "items": [{"name": f"商品_{i}", "quantity": 1 + i % 5, "weight_kg": 0.5 + i * 0.1}],
            "tracking_nodes": nodes,
        })
    with open(d / "data.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    meta = {
        "data_type": "json",
        "title": "快递物流全程轨迹",
        "description": "20个快递运单的完整物流轨迹，包含寄收件人信息、商品明细及按时间排序的节点追踪记录。",
        "schema": {
            "root_type": "array",
            "item_meaning": "每一个快递运单",
            "keys": {
                "waybill_no": {"type": "string", "description": "运单号", "role": "primary_key"},
                "carrier": {"type": "categorical", "description": "承运快递公司", "values": ["顺丰", "中通", "圆通", "韵达", "申通"]},
                "sender": {
                    "type": "object",
                    "description": "寄件人信息",
                    "keys": {
                        "name": {"type": "string", "description": "姓名"},
                        "phone": {"type": "string", "description": "手机号"},
                        "address": {
                            "type": "object",
                            "description": "地址",
                            "keys": {
                                "province": {"type": "string", "description": "省"},
                                "city": {"type": "string", "description": "市"},
                                "detail": {"type": "string", "description": "详细地址"},
                            }
                        },
                    }
                },
                "receiver": {
                    "type": "object",
                    "description": "收件人信息",
                    "keys": {
                        "name": {"type": "string", "description": "姓名"},
                        "phone": {"type": "string", "description": "手机号"},
                        "address": {
                            "type": "object",
                            "description": "地址",
                            "keys": {
                                "province": {"type": "string", "description": "省"},
                                "city": {"type": "string", "description": "市"},
                                "detail": {"type": "string", "description": "详细地址"},
                            }
                        },
                    }
                },
                "items": {
                    "type": "array",
                    "description": "商品明细",
                    "item_schema": {
                        "type": "object",
                        "keys": {
                            "name": {"type": "string", "description": "商品名"},
                            "quantity": {"type": "integer", "description": "数量"},
                            "weight_kg": {"type": "numeric", "description": "重量", "unit": "kg"},
                        }
                    }
                },
                "tracking_nodes": {
                    "type": "array",
                    "description": "物流节点轨迹",
                    "item_schema": {
                        "type": "object",
                        "keys": {
                            "node": {"type": "string", "description": "节点名称"},
                            "time": {"type": "datetime", "description": "到达时间", "format": "ISO8601"},
                            "location": {
                                "type": "object",
                                "description": "节点地理位置",
                                "keys": {
                                    "province": {"type": "string", "description": "省"},
                                    "city": {"type": "string", "description": "市"},
                                    "lat": {"type": "numeric", "description": "纬度"},
                                    "lng": {"type": "numeric", "description": "经度"},
                                }
                            },
                            "status": {"type": "categorical", "description": "物流状态", "values": ["已揽收", "运输中", "到达分拨", "派送中", "已签收"]},
                        }
                    }
                },
            }
        }
    }
    save_meta(d, meta)
    register("json", slug, meta["title"], meta["description"])



# =============================================================================
# 4. Network
# =============================================================================
def gen_network():
    out = BASE / "network"
    out.mkdir(parents=True, exist_ok=True)

    # ---- 4.1 社交网络（多类型节点+多类型边） ----
    slug = "social_network"
    d = out / slug
    d.mkdir(exist_ok=True)
    nodes = []
    for i in range(1, 41):
        nodes.append({
            "id": f"U_{i}",
            "type": ["普通用户", "KOL", "商家"][i % 3],
            "label": f"用户_{i}",
            "attributes": {
                "age": 18 + i % 50,
                "gender": ["男", "女"][i % 2],
                "city": ["北京", "上海", "广州", "深圳"][i % 4],
                "followers": i * 10,
                "verified": i % 7 == 0,
            },
        })
    edges = []
    for i in range(1, 41):
        edges.append({"source": f"U_{i}", "target": f"U_{(i % 40) + 1}", "type": "关注", "properties": {"weight": 1, "since": "2024-01-01"}})
        if i % 3 == 0:
            edges.append({"source": f"U_{i}", "target": f"U_{(i + 5) % 40 + 1}", "type": "互动", "properties": {"weight": 5, "count": 20}})
        if i % 5 == 0:
            edges.append({"source": f"U_{i}", "target": f"U_{(i + 10) % 40 + 1}", "type": "推荐", "properties": {"weight": 2, "confidence": 0.85}})
    with open(d / "nodes.json", "w", encoding="utf-8") as f:
        json.dump(nodes, f, ensure_ascii=False, indent=2)
    with open(d / "edges.json", "w", encoding="utf-8") as f:
        json.dump(edges, f, ensure_ascii=False, indent=2)
    meta = {
        "data_type": "network",
        "title": "社交媒体关系网络",
        "description": "40个用户节点（含普通用户、KOL、商家三种类型）及关注/互动/推荐三种关系边。",
        "schema": {
            "node_types": {
                "普通用户": {
                    "description": "平台普通注册用户",
                    "attributes": {
                        "age": {"type": "integer", "description": "年龄", "unit": "岁", "range": [18, 67]},
                        "gender": {"type": "categorical", "description": "性别", "values": ["男", "女"]},
                        "city": {"type": "categorical", "description": "所在城市", "values": ["北京", "上海", "广州", "深圳"]},
                        "followers": {"type": "integer", "description": "粉丝数"},
                        "verified": {"type": "boolean", "description": "是否认证"},
                    }
                },
                "KOL": {
                    "description": "平台关键意见领袖",
                    "attributes": {
                        "age": {"type": "integer", "description": "年龄", "unit": "岁", "range": [18, 67]},
                        "gender": {"type": "categorical", "description": "性别", "values": ["男", "女"]},
                        "city": {"type": "categorical", "description": "所在城市", "values": ["北京", "上海", "广州", "深圳"]},
                        "followers": {"type": "integer", "description": "粉丝数"},
                        "verified": {"type": "boolean", "description": "是否认证", "constraint": "必须为True"},
                    }
                },
                "商家": {
                    "description": "平台入驻商家账号",
                    "attributes": {
                        "age": {"type": "integer", "description": "商家成立年限", "unit": "年"},
                        "gender": {"type": "categorical", "description": "法人性别", "values": ["男", "女"]},
                        "city": {"type": "categorical", "description": "注册城市", "values": ["北京", "上海", "广州", "深圳"]},
                        "followers": {"type": "integer", "description": "店铺关注数"},
                        "verified": {"type": "boolean", "description": "是否企业认证"},
                    }
                },
            },
            "edge_types": {
                "关注": {
                    "description": "用户A关注了用户B",
                    "directed": True,
                    "properties": {
                        "weight": {"type": "integer", "description": "关系强度权重", "default": 1},
                        "since": {"type": "date", "description": "关注开始日期", "format": "YYYY-MM-DD"},
                    }
                },
                "互动": {
                    "description": "用户A与用户B有内容互动（点赞/评论/转发）",
                    "directed": True,
                    "properties": {
                        "weight": {"type": "integer", "description": "互动频次权重"},
                        "count": {"type": "integer", "description": "近30天互动次数"},
                    }
                },
                "推荐": {
                    "description": "平台算法将B推荐给A",
                    "directed": True,
                    "properties": {
                        "weight": {"type": "integer", "description": "推荐优先级"},
                        "confidence": {"type": "numeric", "description": "推荐置信度", "range": [0, 1]},
                    }
                },
            }
        }
    }
    save_meta(d, meta)
    register("network", slug, meta["title"], meta["description"])

    # ---- 4.2 知识图谱（实体-关系-实体） ----
    slug = "knowledge_graph"
    d = out / slug
    d.mkdir(exist_ok=True)
    nodes = []
    for i in range(1, 21):
        nodes.append({
            "id": f"ENT_{i}",
            "type": ["人物", "公司", "产品", "行业"][i % 4],
            "label": f"实体_{i}",
            "attributes": {
                "name": f"名称_{i}",
                "description": f"这是实体{i}的描述",
                "source": ["维基百科", "企业年报", "新闻报道", "专利库"][i % 4],
            },
        })
    edges = []
    for i in range(1, 21):
        edges.append({"source": f"ENT_{i}", "target": f"ENT_{(i % 20) + 1}", "type": "关联", "properties": {"relation": ["创始人", "竞品", "供应链", "投资"][i % 4], "strength": 0.5 + (i % 5) * 0.1}})
        if i % 3 == 0:
            edges.append({"source": f"ENT_{i}", "target": f"ENT_{(i + 3) % 20 + 1}", "type": "从属", "properties": {"since": 2010 + i % 10}})
    with open(d / "nodes.json", "w", encoding="utf-8") as f:
        json.dump(nodes, f, ensure_ascii=False, indent=2)
    with open(d / "edges.json", "w", encoding="utf-8") as f:
        json.dump(edges, f, ensure_ascii=False, indent=2)
    meta = {
        "data_type": "network",
        "title": "企业知识图谱",
        "description": "20个实体（人物、公司、产品、行业）及关联/从属关系，用于企业情报分析。",
        "schema": {
            "node_types": {
                "人物": {
                    "description": "企业相关个人",
                    "attributes": {
                        "name": {"type": "string", "description": "姓名"},
                        "description": {"type": "string", "description": "人物简介"},
                        "source": {"type": "categorical", "description": "数据来源", "values": ["维基百科", "企业年报", "新闻报道", "专利库"]},
                    }
                },
                "公司": {
                    "description": "工商注册企业",
                    "attributes": {
                        "name": {"type": "string", "description": "公司名"},
                        "description": {"type": "string", "description": "企业简介"},
                        "source": {"type": "categorical", "description": "数据来源", "values": ["维基百科", "企业年报", "新闻报道", "专利库"]},
                    }
                },
                "产品": {
                    "description": "公司推出的产品",
                    "attributes": {
                        "name": {"type": "string", "description": "产品名"},
                        "description": {"type": "string", "description": "产品介绍"},
                        "source": {"type": "categorical", "description": "数据来源", "values": ["维基百科", "企业年报", "新闻报道", "专利库"]},
                    }
                },
                "行业": {
                    "description": "行业分类",
                    "attributes": {
                        "name": {"type": "string", "description": "行业名称"},
                        "description": {"type": "string", "description": "行业描述"},
                        "source": {"type": "categorical", "description": "数据来源", "values": ["维基百科", "企业年报", "新闻报道", "专利库"]},
                    }
                },
            },
            "edge_types": {
                "关联": {
                    "description": "两个实体存在语义关联",
                    "directed": True,
                    "properties": {
                        "relation": {"type": "categorical", "description": "具体关联类型", "values": ["创始人", "竞品", "供应链", "投资"]},
                        "strength": {"type": "numeric", "description": "关联强度", "range": [0, 1]},
                    }
                },
                "从属": {
                    "description": "实体A从属于实体B",
                    "directed": True,
                    "properties": {
                        "since": {"type": "integer", "description": "从属起始年份", "unit": "年"},
                    }
                },
            }
        }
    }
    save_meta(d, meta)
    register("network", slug, meta["title"], meta["description"])

    # ---- 4.3 供应链网络 ----
    slug = "supply_chain"
    d = out / slug
    d.mkdir(exist_ok=True)
    nodes = []
    roles = ["原材料供应商", "制造商", "分销商", "零售商", "消费者"]
    for i in range(1, 26):
        nodes.append({
            "id": f"SC_{i}",
            "type": roles[i % 5],
            "label": f"节点_{i}",
            "attributes": {
                "name": f"企业_{i}",
                "region": ["华东", "华南", "华北", "西南"][i % 4],
                "capacity": 1000 + i * 200,
                "risk_score": round(1 + (i % 10) * 0.5, 1),
            },
        })
    edges = []
    for i in range(1, 26):
        edges.append({"source": f"SC_{i}", "target": f"SC_{(i % 25) + 1}", "type": "供应", "properties": {"volume": 100 + i * 10, "lead_time_days": 3 + i % 7}})
        if i % 4 == 0:
            edges.append({"source": f"SC_{i}", "target": f"SC_{(i + 4) % 25 + 1}", "type": "合作", "properties": {"contract_value": 50000 + i * 1000, "duration_years": 1 + i % 3}})
    with open(d / "nodes.json", "w", encoding="utf-8") as f:
        json.dump(nodes, f, ensure_ascii=False, indent=2)
    with open(d / "edges.json", "w", encoding="utf-8") as f:
        json.dump(edges, f, ensure_ascii=False, indent=2)
    meta = {
        "data_type": "network",
        "title": "制造业供应链网络",
        "description": "25个供应链节点（原材料商到消费者）及供应/合作关系，含产能和风险评分。",
        "schema": {
            "node_types": {
                "原材料供应商": {
                    "description": "提供上游原材料的企业",
                    "attributes": {
                        "name": {"type": "string", "description": "企业名称"},
                        "region": {"type": "categorical", "description": "所在区域", "values": ["华东", "华南", "华北", "西南"]},
                        "capacity": {"type": "integer", "description": "年产能", "unit": "吨"},
                        "risk_score": {"type": "numeric", "description": "供应链风险评分", "range": [1, 5]},
                    }
                },
                "制造商": {
                    "description": "将原材料加工成成品的企业",
                    "attributes": {
                        "name": {"type": "string", "description": "企业名称"},
                        "region": {"type": "categorical", "description": "所在区域", "values": ["华东", "华南", "华北", "西南"]},
                        "capacity": {"type": "integer", "description": "年产能", "unit": "件"},
                        "risk_score": {"type": "numeric", "description": "供应链风险评分", "range": [1, 5]},
                    }
                },
                "分销商": {
                    "description": "负责区域分销的中间商",
                    "attributes": {
                        "name": {"type": "string", "description": "企业名称"},
                        "region": {"type": "categorical", "description": "所在区域", "values": ["华东", "华南", "华北", "西南"]},
                        "capacity": {"type": "integer", "description": "年分销能力", "unit": "件"},
                        "risk_score": {"type": "numeric", "description": "供应链风险评分", "range": [1, 5]},
                    }
                },
                "零售商": {
                    "description": "面向终端消费者的销售终端",
                    "attributes": {
                        "name": {"type": "string", "description": "企业名称"},
                        "region": {"type": "categorical", "description": "所在区域", "values": ["华东", "华南", "华北", "西南"]},
                        "capacity": {"type": "integer", "description": "年销售能力", "unit": "件"},
                        "risk_score": {"type": "numeric", "description": "供应链风险评分", "range": [1, 5]},
                    }
                },
                "消费者": {
                    "description": "最终购买产品的用户群体",
                    "attributes": {
                        "name": {"type": "string", "description": "消费者群体名称"},
                        "region": {"type": "categorical", "description": "所在区域", "values": ["华东", "华南", "华北", "西南"]},
                        "capacity": {"type": "integer", "description": "年消费需求量", "unit": "件"},
                        "risk_score": {"type": "numeric", "description": "消费风险评分", "range": [1, 5]},
                    }
                },
            },
            "edge_types": {
                "供应": {
                    "description": "上游向下游供货",
                    "directed": True,
                    "properties": {
                        "volume": {"type": "integer", "description": "年供货量", "unit": "件/吨"},
                        "lead_time_days": {"type": "integer", "description": "供货周期", "unit": "天"},
                    }
                },
                "合作": {
                    "description": "企业间的战略合作关系",
                    "directed": False,
                    "properties": {
                        "contract_value": {"type": "integer", "description": "合同金额", "unit": "元"},
                        "duration_years": {"type": "integer", "description": "合同期限", "unit": "年"},
                    }
                },
            }
        }
    }
    save_meta(d, meta)
    register("network", slug, meta["title"], meta["description"])

    # ---- 4.4 城市交通路网 ----
    slug = "city_transport"
    d = out / slug
    d.mkdir(exist_ok=True)
    nodes = []
    for i in range(1, 16):
        nodes.append({
            "id": f"ST_{i}",
            "type": ["地铁站", "公交站", "枢纽站"][i % 3],
            "label": f"站点_{i}",
            "attributes": {
                "name": f"站点名称_{i}",
                "lat": 39.9 + i * 0.01,
                "lng": 116.4 + i * 0.01,
                "daily_passengers": 10000 + i * 5000,
                "lines": [f"线路_{i % 5 + 1}", f"线路_{(i + 1) % 5 + 1}"],
            },
        })
    edges = []
    for i in range(1, 16):
        edges.append({"source": f"ST_{i}", "target": f"ST_{(i % 15) + 1}", "type": "轨道", "properties": {"distance_km": 1 + i % 5, "travel_time_min": 2 + i % 5}})
        if i % 3 == 0:
            edges.append({"source": f"ST_{i}", "target": f"ST_{(i + 3) % 15 + 1}", "type": "换乘", "properties": {"walk_time_min": 3 + i % 5}})
    with open(d / "nodes.json", "w", encoding="utf-8") as f:
        json.dump(nodes, f, ensure_ascii=False, indent=2)
    with open(d / "edges.json", "w", encoding="utf-8") as f:
        json.dump(edges, f, ensure_ascii=False, indent=2)
    meta = {
        "data_type": "network",
        "title": "城市公共交通网络",
        "description": "15个交通站点（地铁/公交/枢纽）及轨道连接和换乘关系。",
        "schema": {
            "node_types": {
                "地铁站": {
                    "description": "地铁线路上的站点",
                    "attributes": {
                        "name": {"type": "string", "description": "站点名称"},
                        "lat": {"type": "numeric", "description": "纬度"},
                        "lng": {"type": "numeric", "description": "经度"},
                        "daily_passengers": {"type": "integer", "description": "日均客流量"},
                        "lines": {"type": "array", "description": "经过的线路列表", "item_schema": {"type": "string"}},
                    }
                },
                "公交站": {
                    "description": "公交线路上的站点",
                    "attributes": {
                        "name": {"type": "string", "description": "站点名称"},
                        "lat": {"type": "numeric", "description": "纬度"},
                        "lng": {"type": "numeric", "description": "经度"},
                        "daily_passengers": {"type": "integer", "description": "日均客流量"},
                        "lines": {"type": "array", "description": "经过的线路列表", "item_schema": {"type": "string"}},
                    }
                },
                "枢纽站": {
                    "description": "多种交通方式交汇的枢纽",
                    "attributes": {
                        "name": {"type": "string", "description": "站点名称"},
                        "lat": {"type": "numeric", "description": "纬度"},
                        "lng": {"type": "numeric", "description": "经度"},
                        "daily_passengers": {"type": "integer", "description": "日均客流量"},
                        "lines": {"type": "array", "description": "经过的线路列表", "item_schema": {"type": "string"}},
                    }
                },
            },
            "edge_types": {
                "轨道": {
                    "description": "轨道线路上的直接连接",
                    "directed": False,
                    "properties": {
                        "distance_km": {"type": "numeric", "description": "站间距", "unit": "km"},
                        "travel_time_min": {"type": "integer", "description": "行驶时间", "unit": "分钟"},
                    }
                },
                "换乘": {
                    "description": "不同线路间的换乘通道",
                    "directed": False,
                    "properties": {
                        "walk_time_min": {"type": "integer", "description": "步行换乘时间", "unit": "分钟"},
                    }
                },
            }
        }
    }
    save_meta(d, meta)
    register("network", slug, meta["title"], meta["description"])

    # ---- 4.5 学术论文引用网络 ----
    slug = "citation_network"
    d = out / slug
    d.mkdir(exist_ok=True)
    nodes = []
    for i in range(1, 21):
        nodes.append({
            "id": f"PAPER_{i}",
            "type": ["期刊论文", "会议论文", "综述"][i % 3],
            "label": f"论文_{i}",
            "attributes": {
                "title": f"论文标题_{i}",
                "author": f"作者_{i}",
                "year": 2020 + i % 5,
                "citations": i * 3,
                "field": ["AI", "数据库", "网络安全", "图形学", "NLP"][i % 5],
                "impact_factor": round(2.0 + (i % 10) * 0.5, 1),
            },
        })
    edges = []
    for i in range(1, 21):
        edges.append({"source": f"PAPER_{i}", "target": f"PAPER_{(i % 20) + 1}", "type": "引用", "properties": {"citation_count": 1}})
        if i % 4 == 0:
            edges.append({"source": f"PAPER_{i}", "target": f"PAPER_{(i + 4) % 20 + 1}", "type": "合作", "properties": {"coauthor_count": 2 + i % 3}})
    with open(d / "nodes.json", "w", encoding="utf-8") as f:
        json.dump(nodes, f, ensure_ascii=False, indent=2)
    with open(d / "edges.json", "w", encoding="utf-8") as f:
        json.dump(edges, f, ensure_ascii=False, indent=2)
    meta = {
        "data_type": "network",
        "title": "学术论文引用与合作网络",
        "description": "20篇学术论文（期刊/会议/综述）及引用和合作关系。",
        "schema": {
            "node_types": {
                "期刊论文": {
                    "description": "发表在学术期刊上的研究论文",
                    "attributes": {
                        "title": {"type": "string", "description": "论文标题"},
                        "author": {"type": "string", "description": "第一作者"},
                        "year": {"type": "integer", "description": "发表年份"},
                        "citations": {"type": "integer", "description": "被引次数"},
                        "field": {"type": "categorical", "description": "研究领域", "values": ["AI", "数据库", "网络安全", "图形学", "NLP"]},
                        "impact_factor": {"type": "numeric", "description": "期刊影响因子"},
                    }
                },
                "会议论文": {
                    "description": "发表在学术会议上的研究论文",
                    "attributes": {
                        "title": {"type": "string", "description": "论文标题"},
                        "author": {"type": "string", "description": "第一作者"},
                        "year": {"type": "integer", "description": "发表年份"},
                        "citations": {"type": "integer", "description": "被引次数"},
                        "field": {"type": "categorical", "description": "研究领域", "values": ["AI", "数据库", "网络安全", "图形学", "NLP"]},
                        "impact_factor": {"type": "numeric", "description": "会议h5指数等替代指标"},
                    }
                },
                "综述": {
                    "description": "系统性综述文章",
                    "attributes": {
                        "title": {"type": "string", "description": "论文标题"},
                        "author": {"type": "string", "description": "第一作者"},
                        "year": {"type": "integer", "description": "发表年份"},
                        "citations": {"type": "integer", "description": "被引次数"},
                        "field": {"type": "categorical", "description": "研究领域", "values": ["AI", "数据库", "网络安全", "图形学", "NLP"]},
                        "impact_factor": {"type": "numeric", "description": "发表载体指标"},
                    }
                },
            },
            "edge_types": {
                "引用": {
                    "description": "论文A引用了论文B",
                    "directed": True,
                    "properties": {
                        "citation_count": {"type": "integer", "description": "引用次数（通常1次）"},
                    }
                },
                "合作": {
                    "description": "论文A与论文B有共同作者",
                    "directed": False,
                    "properties": {
                        "coauthor_count": {"type": "integer", "description": "共同作者数量"},
                    }
                },
            }
        }
    }
    save_meta(d, meta)
    register("network", slug, meta["title"], meta["description"])


# =============================================================================
# Main
# =============================================================================
if __name__ == "__main__":
    gen_timeseries()
    gen_table()
    gen_json()
    gen_network()
    with open(BASE / "index.json", "w", encoding="utf-8") as f:
        json.dump(INDEX, f, ensure_ascii=False, indent=2)
    print(f"Generated {len(INDEX)} sample datasets under {BASE}")
