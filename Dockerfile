FROM python:3.13-slim AS base
WORKDIR /app

FROM node:22-slim AS frontend-build
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ .
RUN npm run build

FROM base AS backend
COPY pyproject.toml uv.lock ./
COPY src ./src
COPY golden_dataset ./golden_dataset
COPY prompts ./prompts
COPY runs ./runs
COPY main.py .
RUN pip install uv
RUN uv sync --no-dev
RUN --mount=type=cache,target=/root/.cache/uv \
  uv pip install --system -e .
COPY --from=frontend-build /app/frontend/dist ./frontend/dist
EXPOSE 8000
CMD ["uv", "run", "uvicorn", "src.api:app", "--host", "0.0.0.0", "--port", "8000"]
