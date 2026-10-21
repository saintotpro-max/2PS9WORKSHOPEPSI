FROM debian:trixie-slim
RUN apt-get update \
 && apt-get install -y --no-install-recommends nftables python3 \
 && rm -rf /var/lib/apt/lists/*
COPY app.py /app/app.py
# nft exige CAP_NET_ADMIN : accordé par compose, sans mode privilégié
CMD ["python3", "-u", "/app/app.py"]
