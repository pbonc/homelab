FROM python@sha256:0aecac02dc3d4c5dbb024b753af084cafe41f5416e02193f1ce345d671ec966e

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir --requirement requirements.txt

COPY security_status ./security_status

RUN useradd --create-home --uid 10002 security-status
USER security-status

EXPOSE 8010

CMD ["uvicorn", "security_status.main:app", "--host", "0.0.0.0", "--port", "8010"]

