# Optional container for running the app without installing Python.
#   docker compose up --build        then open http://localhost:8501
FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:0.13.6 /uv /usr/local/bin/uv
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy PYTHONUNBUFFERED=1
WORKDIR /app

# Dependencies first so code changes don't reinstall them.
COPY pyproject.toml uv.lock .python-version README.md ./
RUN uv sync --frozen --no-dev --no-install-project

COPY config.yaml ./
COPY src ./src
COPY app ./app
COPY data/policy ./data/policy
COPY data/listings ./data/listings
COPY data/cases ./data/cases
COPY data/eval ./data/eval
COPY data/labels ./data/labels
COPY reports ./reports
RUN uv sync --frozen --no-dev

# Download the embedding model and build the policy index at build time.
RUN uv run python -c "from dispute_agent.rag.store import get_store; get_store()"

EXPOSE 8501
CMD ["uv", "run", "streamlit", "run", "app/streamlit_app.py", "--server.address=0.0.0.0", "--server.port=8501"]
