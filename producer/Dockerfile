FROM python:3.10-slim

WORKDIR /app

COPY producer/ .   
RUN pip install --no-cache-dir -r ./requirements.txt


CMD ["python", "producer.py"]
