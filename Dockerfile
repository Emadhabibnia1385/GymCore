FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /srv/gymcore

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

# Non-root runtime user; uploads volume is mounted here.
RUN useradd --create-home gymcore \
    && mkdir -p /srv/gymcore/uploads \
    && chown -R gymcore:gymcore /srv/gymcore
USER gymcore

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
