FROM node:20-alpine AS ui-builder

WORKDIR /build/ui-dashboard

COPY ui-dashboard/package.json ui-dashboard/package-lock.json ./
RUN npm ci

COPY ui-dashboard/mcp-app.html ui-dashboard/vite.config.js ./
COPY ui-dashboard/src ./src

RUN npm run build


FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080

WORKDIR /service

COPY pyproject.toml /service/pyproject.toml
COPY app /service/app
COPY --from=ui-builder /build/ui-dashboard/dist /service/ui-dashboard/dist

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir .

WORKDIR /service/app

EXPOSE 8080

CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8080}"]
