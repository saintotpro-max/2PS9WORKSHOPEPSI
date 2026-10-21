FROM debian:trixie-slim
RUN apt-get update \
 && apt-get install -y --no-install-recommends argus-server \
 && rm -rf /var/lib/apt/lists/*
COPY argus.conf /etc/argus.conf
CMD ["argus", "-F", "/etc/argus.conf"]
