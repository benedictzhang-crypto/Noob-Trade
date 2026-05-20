FROM node:22-bookworm-slim AS frontend-builder

WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm install
COPY frontend/ ./
RUN npm run build

FROM node:22-bookworm-slim AS ampli-lab-builder

RUN apt-get update && \
    apt-get install -y --no-install-recommends ca-certificates git && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app/ampli-lab
RUN git clone --depth 1 https://github.com/benedictzhang-crypto/ampli-lab.git .
RUN npm ci
RUN npm run build -- --base=/amplialpha/

FROM python:3.12-slim

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV FLASK_DEBUG=false
ENV HOST=0.0.0.0
ENV PORT=5000

COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r /app/backend/requirements.txt && \
    pip install --no-cache-dir gunicorn==23.0.0

COPY backend/ /app/backend/
COPY --from=frontend-builder /app/frontend/dist /app/frontend/dist
COPY --from=ampli-lab-builder /app/ampli-lab/dist /app/backend/ampli_lab_site

WORKDIR /app/backend
CMD ["sh", "-c", "gunicorn --bind 0.0.0.0:${PORT:-5000} --worker-class gthread --workers 1 --threads 8 --timeout 30 --graceful-timeout 10 --keep-alive 5 --max-requests 100 --max-requests-jitter 20 --access-logfile - --error-logfile - app:app"]
