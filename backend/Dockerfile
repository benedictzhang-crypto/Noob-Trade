FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY . /app

ENV HOST=0.0.0.0
ENV PORT=5010
ENV FLASK_DEBUG=false
ENV FLASK_USE_RELOADER=false

EXPOSE 5010

CMD ["sh", "-c", "gunicorn -b 0.0.0.0:${PORT:-5010} app:app"]
