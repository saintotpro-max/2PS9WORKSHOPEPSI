FROM python:3.13-slim
RUN pip install --no-cache-dir \
      fastapi==0.148.0 uvicorn==0.54.0 httpx==0.28.1 prometheus-client==0.26.0 pyyaml==6.0.3
COPY app /app
# Volume de l'historique : créé ici pour appartenir à l'utilisateur non privilégié
RUN mkdir /data && chown 65534:65534 /data
WORKDIR /app
USER 65534:65534
EXPOSE 8000
HEALTHCHECK --interval=10s --timeout=3s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2)"
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log"]
