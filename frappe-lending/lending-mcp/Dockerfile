FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /service

COPY pyproject.toml /service/pyproject.toml
COPY app /service/app

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir .

WORKDIR /service/app

EXPOSE 8080

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
