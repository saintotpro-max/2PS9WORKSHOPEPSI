FROM debian:trixie-slim
RUN apt-get update \
 && apt-get install -y --no-install-recommends argus-client nftables python3 python3-prometheus-client \
 && rm -rf /var/lib/apt/lists/*
COPY extractor.py /app/extractor.py
# nft exige CAP_NET_ADMIN : accordé par compose, sans mode privilégié
CMD ["python3", "-u", "/app/extractor.py"]
