"""
示例数据生成器 — 生成测试用的多类型数据文件

运行方式:
    python examples/generate_sample_data.py

生成文件:
    - data/sales_data.csv    销售数据（含时间序列、类别、数值）
    - data/customer_data.csv 客户数据（含类别、数值、文本）
    - data/employee_data.xlsx 员工数据（Excel格式）
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json
from pathlib import Path

# 设置随机种子
np.random.seed(42)

# 项目数据目录
DATA_DIR = Path(__file__).parent.parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)


def generate_sales_data(n=500):
    """生成销售数据（CSV）— 适合趋势型、对比型叙事"""
    start_date = datetime(2024, 1, 1)
    dates = [start_date + timedelta(days=i) for i in range(n)]
    
    regions = ["华东", "华南", "华北", "西南", "西北"]
    categories = ["电子产品", "服装", "食品", "家居", "美妆"]
    
    data = {
        "日期": dates,
        "地区": np.random.choice(regions, n),
        "产品类别": np.random.choice(categories, n),
        "销售额": np.random.normal(5000, 2000, n).clip(100, 20000).round(2),
        "订单数": np.random.poisson(50, n),
        "客户评分": np.random.choice([1, 2, 3, 4, 5], n, p=[0.05, 0.1, 0.2, 0.35, 0.3]),
        "是否促销": np.random.choice([True, False], n, p=[0.3, 0.7]),
    }
    
    df = pd.DataFrame(data)
    # 人为制造一些缺失值
    missing_idx = np.random.choice(df.index, size=int(n * 0.02), replace=False)
    df.loc[missing_idx, "客户评分"] = np.nan
    
    return df


def generate_customer_data(n=300):
    """生成客户数据（CSV）— 适合分布型、关系型叙事"""
    age_groups = ["18-25", "26-35", "36-45", "46-55", "55+"]
    genders = ["男", "女"]
    cities = ["北京", "上海", "广州", "深圳", "杭州", "成都", "武汉", "西安"]
    channels = ["线上", "线下", "社交电商", "直播"]
    
    data = {
        "客户ID": [f"CUST_{i+1:05d}" for i in range(n)],
        "年龄组": np.random.choice(age_groups, n),
        "性别": np.random.choice(genders, n),
        "城市": np.random.choice(cities, n),
        "注册渠道": np.random.choice(channels, n),
        "消费金额": np.random.lognormal(8, 1.2, n).round(2),
        "购买次数": np.random.poisson(5, n),
        "最近一次购买距今天数": np.random.exponential(30, n).round(0).astype(int),
        "会员等级": np.random.choice(["普通", "银卡", "金卡", "钻石"], n, p=[0.5, 0.3, 0.15, 0.05]),
    }
    
    return pd.DataFrame(data)


def generate_employee_data(n=100):
    """生成员工数据（Excel）— 适合构成型、排名型叙事"""
    departments = ["技术部", "销售部", "市场部", "人事部", "财务部", "运营部"]
    positions = ["初级", "中级", "高级", "经理", "总监"]
    education = ["本科", "硕士", "博士", "大专"]
    
    data = {
        "员工编号": [f"EMP_{i+1:04d}" for i in range(n)],
        "姓名": [f"员工_{i+1}" for i in range(n)],
        "部门": np.random.choice(departments, n),
        "职位": np.random.choice(positions, n),
        "学历": np.random.choice(education, n, p=[0.5, 0.3, 0.05, 0.15]),
        "入职年份": np.random.randint(2018, 2025, n),
        "月薪": np.random.normal(15000, 5000, n).clip(5000, 50000).round(0).astype(int),
        "绩效评分": np.random.normal(75, 15, n).clip(0, 100).round(1),
        "是否在职": np.random.choice([True, False], n, p=[0.9, 0.1]),
    }
    
    return pd.DataFrame(data)


if __name__ == "__main__":
    import sys
    # 修复 Windows 控制台编码
    if sys.platform == "win32":
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    
    print("生成示例数据...")
    
    # 1. 销售数据
    sales_df = generate_sales_data(500)
    sales_path = DATA_DIR / "sales_data.csv"
    sales_df.to_csv(sales_path, index=False, encoding="utf-8-sig")
    print(f"   [OK] sales_data.csv ({len(sales_df)} 行 x {len(sales_df.columns)} 列)")
    
    # 2. 客户数据
    customer_df = generate_customer_data(300)
    customer_path = DATA_DIR / "customer_data.csv"
    customer_df.to_csv(customer_path, index=False, encoding="utf-8-sig")
    print(f"   [OK] customer_data.csv ({len(customer_df)} 行 x {len(customer_df.columns)} 列)")
    
    # 3. 员工数据 (Excel)
    employee_df = generate_employee_data(100)
    employee_path = DATA_DIR / "employee_data.xlsx"
    employee_df.to_excel(employee_path, index=False, sheet_name="员工信息")
    print(f"   [OK] employee_data.xlsx ({len(employee_df)} 行 x {len(employee_df.columns)} 列)")
    
    print(f"\n数据已保存到: {DATA_DIR}")
    print("\n接下来可以运行:")
    print(f'   python run.py data/sales_data.csv')
    print(f'   python run.py data/customer_data.csv')
    print(f'   python run.py data/employee_data.xlsx')
