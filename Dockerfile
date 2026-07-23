FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    fonts-liberation \
    fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY bot/ ./bot/
COPY schema.sql .

CMD ["python", "-m", "bot.main"]
