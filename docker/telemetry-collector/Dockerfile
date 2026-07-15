FROM python@sha256:0aecac02dc3d4c5dbb024b753af084cafe41f5416e02193f1ce345d671ec966e

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir --requirement requirements.txt

COPY telemetry_collector ./telemetry_collector

RUN useradd --create-home --uid 10001 collector
USER collector

EXPOSE 8000

CMD ["uvicorn", "telemetry_collector.main:app", "--host", "0.0.0.0", "--port", "8000"]
