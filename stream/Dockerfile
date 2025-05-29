FROM python:3.9-slim

WORKDIR /app

COPY stream/ .
RUN pip install --no-cache-dir -r ./requirements.txt


# 啟動 faust worker
CMD ["faust", "-A", "stream", "worker", "-l", "info"]
