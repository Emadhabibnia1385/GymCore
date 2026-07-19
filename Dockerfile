FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Default command; docker-compose overrides it per service (api / telegram /
# bale / worker). Long polling means no port needs to be exposed for the bots.
CMD ["python", "-m", "app.bots.telegram.main"]
