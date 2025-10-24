FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl wget gnupg libpq-dev build-essential \
    && rm -rf /var/lib/apt/lists/*

ADD requirements.txt requirements.txt
RUN pip install --upgrade pip && pip install -r requirements.txt

ADD . .

RUN playwright install --with-deps chromium

CMD ["python", "pipeline.py"]
