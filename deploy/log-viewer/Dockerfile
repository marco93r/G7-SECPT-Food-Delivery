FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt ./
RUN apt-get update \
    && apt-get install -y --no-install-recommends coreutils \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir -r requirements.txt

COPY app.py ./

ENV LOG_DIR=/logs \
    LOG_USER=admin \
    LOG_PASSWORD=admin \
    PORT=8080

EXPOSE 8080

CMD ["python", "app.py"]
