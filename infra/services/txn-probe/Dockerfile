FROM python:3.13-slim
RUN pip install --no-cache-dir prometheus-client==0.26.0
COPY probe.py /app/probe.py
USER 65534:65534
EXPOSE 9102
CMD ["python", "-u", "/app/probe.py"]
