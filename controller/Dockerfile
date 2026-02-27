FROM python:3.11-slim


WORKDIR /app


COPY ryu_exporter.py /app/ryu_exporter.py



RUN pip install --no-cache-dir prometheus_client requests


EXPOSE 9100


CMD ["python", "ryu_exporter.py"]
