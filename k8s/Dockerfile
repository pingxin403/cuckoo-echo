FROM python:3.12-slim AS builder
RUN pip install --no-cache-dir uv -i https://pypi.tuna.tsinghua.edu.cn/simple
RUN apt-get update && apt-get install -y --no-install-recommends gcc libc6-dev zlib1g-dev && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv pip install --system --no-cache -r pyproject.toml -i https://pypi.tuna.tsinghua.edu.cn/simple
COPY . .

FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    libgl1 \
    libglib2.0-0 \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*
RUN useradd -m -s /bin/bash app
WORKDIR /app
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY --from=builder /app /app
COPY scripts/docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh && chown -R app:app /app
USER app
ENTRYPOINT ["/docker-entrypoint.sh"]

# ============================================================
# 备用方案: 从主机拷贝依赖 (取消下方注释并注释上方 builder 阶段)
# ============================================================
# FROM python:3.12-slim
# RUN apt-get update && apt-get install -y --no-install-recommends \
#     curl \
#     libgl1 \
#     libglib2.0-0 \
#     poppler-utils \
#     && rm -rf /var/lib/apt/lists/*
# RUN useradd -m -s /bin/bash app
# WORKDIR /app
# # 将本地的 .venv 依赖复制进来 (需要先在主机运行: cp -r .venv/lib/python3.12/site-packages ./docker-deps/)
# COPY docker-deps/site-packages /usr/local/lib/python3.12/site-packages
# COPY --from=builder /usr/local/bin /usr/local/bin
# COPY . /app
# COPY scripts/docker-entrypoint.sh /docker-entrypoint.sh
# RUN chmod +x /docker-entrypoint.sh && chown -R app:app /app
# USER app
# ENTRYPOINT ["/docker-entrypoint.sh"]
