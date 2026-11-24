FROM python:3.12-slim

WORKDir /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

COPY pyproject.toml uv.lock ./

RUN uv sync --locked --no-dev --no-install-project

ENV PATH="/app/.venv/bin:$PATH"

COPY ..

EXPOSE 8000

CMD ["uvicorn","app:app","--host","0.0.0.0","--port","8000"]


