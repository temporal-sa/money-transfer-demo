FROM python:3.12-slim

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv
COPY pyproject.toml ./
RUN uv pip install --system -r pyproject.toml

COPY worker.py ./

CMD ["python", "worker.py"]