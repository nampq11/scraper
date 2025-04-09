FROM python:3.10-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

ENV PYTHONUNBUFFERED=1

# RUN apt-get update && apt-get install -y \
#     curl \
#     build-essential \
#     # libpq-dev is needed for psycopg2
#     libpq-dev \
#     && apt-get clean \
#     && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY uv.lock pyproject.toml ./
RUN uv sync --no-dev --frozen --no-cache
COPY . .

EXPOSE 8000

CMD ["/app/.venv/bin/fastapi", "run", "src/main.py", "--port", "8000", "--host", "0.0.0.0"]