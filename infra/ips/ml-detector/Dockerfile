# Versions identiques à celles de l'entraînement (scikit-learn 1.7.2) : un pickle
# scikit-learn n'est garanti qu'avec la version qui l'a produit.
FROM python:3.13-slim
RUN pip install --no-cache-dir \
      scikit-learn==1.7.2 numpy==2.5.4 scipy==1.18.1 joblib==1.6.0 threadpoolctl==3.7.0
COPY app.py /app/app.py
USER 65534:65534
EXPOSE 8000
HEALTHCHECK --interval=10s --timeout=3s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2)"
CMD ["python", "-u", "/app/app.py"]
