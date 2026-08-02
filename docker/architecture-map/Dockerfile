FROM python@sha256:0aecac02dc3d4c5dbb024b753af084cafe41f5416e02193f1ce345d671ec966e

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY architecture_map ./architecture_map
COPY model ./model
COPY static ./static
RUN useradd --create-home --uid 10005 architecture-map
USER architecture-map
EXPOSE 8040
CMD ["python", "-m", "architecture_map"]
