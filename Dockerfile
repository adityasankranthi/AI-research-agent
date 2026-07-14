# Multi-stage build: compile the SPA, then run it from a single FastAPI/uvicorn
# process that serves both the built static files and /api/* -- one image, one
# port, no separate static host to coordinate for a small public demo.

FROM node:20-slim AS web-build
WORKDIR /web
COPY web/package.json web/package-lock.json ./
RUN npm ci
COPY web/ .
RUN npm run build

FROM python:3.12-slim AS runtime
WORKDIR /app
RUN pip install --no-cache-dir uv

COPY pyproject.toml uv.lock ./
COPY research_agent/ ./research_agent/
COPY api/ ./api/
# eval/ is intentionally omitted -- it's not needed to serve the demo and keeps
# the runtime image smaller, but [tool.setuptools] packages still lists it, so
# uv sync needs the package importable to build research-agent itself.
COPY eval/ ./eval/
RUN uv sync --frozen --no-dev

COPY --from=web-build /web/dist ./web/dist

EXPOSE 8000
CMD ["uv", "run", "uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
