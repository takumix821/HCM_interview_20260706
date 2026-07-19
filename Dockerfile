FROM python:3.12-slim

ENV TZ=Asia/Taipei

RUN apt-get update \
    && apt-get install -y --no-install-recommends cron tzdata \
    && ln -snf /usr/share/zoneinfo/${TZ} /etc/localtime \
    && echo ${TZ} > /etc/timezone \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

RUN pip install --no-cache-dir uv

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project
ENV PATH="/app/.venv/bin:${PATH}"

COPY collect_articles.py ./
COPY certs/ ./certs/
COPY scheduler/ ./scheduler/

RUN chmod +x ./scheduler/entrypoint.sh ./scheduler/run_once.sh \
    && cp ./scheduler/crontab /etc/cron.d/collect-articles \
    && chmod 0644 /etc/cron.d/collect-articles

ENV PYTHONUNBUFFERED=1

ENTRYPOINT ["/app/scheduler/entrypoint.sh"]
