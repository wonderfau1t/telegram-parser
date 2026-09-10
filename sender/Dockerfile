FROM ghcr.io/astral-sh/uv:0.11.32 AS uv
FROM python:3.12-slim

COPY --from=uv /uv /uvx /bin/
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    PATH="/app/.venv/bin:$PATH"
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project
RUN useradd --uid 10001 --create-home app && mkdir /data && chown app:app /data
COPY *.py ./
USER app
CMD ["python", "main.py"]
