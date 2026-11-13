FROM python:3.13-slim

ARG HTTP_PROXY
ARG HTTPS_PROXY
ARG NO_PROXY

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=8000


WORKDIR /app

COPY requirements.txt .

RUN pip install \
    --no-cache-dir \
    --requirement requirements.txt

COPY app ./app
COPY static ./static
COPY templates ./templates

RUN addgroup --system autobook \
    && adduser --system \
        --ingroup autobook \
        --home /app \
        autobook \
    && chown -R autobook:autobook /app

USER autobook

EXPOSE 8000

HEALTHCHECK \
    --interval=30s \
    --timeout=5s \
    --start-period=10s \
    --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3)"

CMD ["sh", "-c", "uvicorn app.webapp:app --host 0.0.0.0 --port ${PORT}"]

