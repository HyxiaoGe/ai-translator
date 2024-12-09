# 使用Python 3.10作为基础镜像
FROM python:3.10.14

# 设置工作目录
WORKDIR /ai-translator

# 设置环境变量
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# 创建自定义目录
RUN mkdir -p /ai-translator/env

# 复制打包的环境
COPY ai-translator_env.tar.gz /ai-translator/env

# 解压到指定目录
RUN cd /ai-translator/env && \
    tar xf ai-translator_env.tar.gz && \
    rm ai-translator_env.tar.gz && \
    /ai-translator/env/bin/conda-unpack

# 设置环境变量到自定义路径
ENV PATH="/ai-translator/env/bin:$PATH"

# 复制项目文件
COPY . .

# 创建临时文件目录
RUN mkdir -p temp

# 暴露端口
EXPOSE 8000

# 启动应用
CMD ["python", "main.py"]
