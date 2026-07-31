FROM python@sha256:0aecac02dc3d4c5dbb024b753af084cafe41f5416e02193f1ce345d671ec966e

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update \
    && apt-get install --yes --no-install-recommends nmap \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --requirement requirements.txt

COPY network_inventory ./network_inventory
COPY config ./config

RUN useradd --create-home --uid 10004 network-inventory \
    && install -d -o network-inventory -g network-inventory /data
USER network-inventory

EXPOSE 8030

CMD ["python", "-m", "network_inventory.service"]
