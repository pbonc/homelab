FROM python@sha256:0aecac02dc3d4c5dbb024b753af084cafe41f5416e02193f1ce345d671ec966e

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir --requirement requirements.txt

COPY study_deck ./study_deck
COPY content ./content
COPY static ./static

RUN useradd --create-home --uid 10003 study-deck \
    && install -d -o study-deck -g study-deck /data
USER study-deck

EXPOSE 8020

CMD ["uvicorn", "study_deck.main:app", "--host", "0.0.0.0", "--port", "8020"]
