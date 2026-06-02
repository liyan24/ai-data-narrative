# 基于 Python 3.11 的轻量级镜像
FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .

# 安装 Python 依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制项目代码
COPY src/ ./src/
COPY run.py .
COPY examples/ ./examples/
COPY templates/ ./templates/

# 创建数据目录
RUN mkdir -p data output logs

# 设置环境变量
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# 暴露端口（Web 界面）
EXPOSE 7860

# 默认命令：运行帮助
CMD ["python", "run.py", "--help"]
