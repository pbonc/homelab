FROM python@sha256:0aecac02dc3d4c5dbb024b753af084cafe41f5416e02193f1ce345d671ec966e

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app
COPY decoy ./decoy

RUN useradd --create-home --uid 10009 decoy
USER decoy

EXPOSE 8080
CMD ["python", "-m", "decoy"]
