import faust
import torch
import asyncio
from transformers import AutoModelForSequenceClassification, AutoTokenizer
from influxdb_client import InfluxDBClient, Point, WriteOptions
from dotenv import load_dotenv
import os
import time
from faust import Record
import json


class Tweet(Record, serializer='json'):
    text: str
    timestamp: str

load_dotenv()

# Faust App 設定
app = faust.App(
    'tweet-sentiment',
    broker=[
        'kafka://kafka1:9092',
        'kafka://kafka2:9092',
        'kafka://kafka3:9092'
    ],
    consumer_auto_offset_reset='earliest'
)
topic = app.topic('tweets_raw')  # 不指定 Tweet 型別

# 模型與 tokenizer 載入
MODEL = "cardiffnlp/twitter-roberta-base-sentiment"
print("Loading model and tokenizer...")

tokenizer = AutoTokenizer.from_pretrained(MODEL)
model = AutoModelForSequenceClassification.from_pretrained(MODEL)
model.eval()
print("Model loaded successfully.")
labels = ['negative', 'neutral', 'positive']

# InfluxDB 設定
influx = InfluxDBClient(
    url="http://influxdb:8086",
    token=os.getenv("INFLUXDB_TOKEN", "mytoken"),
    org=os.getenv("INFLUXDB_ORG", "myorg")
)
write_api = influx.write_api(write_options=WriteOptions(batch_size=1))
bucket = os.getenv("INFLUXDB_BUCKET", "tweets")

for i in range(5):
    try:
        influx.ping()
        break
    except Exception as e:
        print(f"[{i+1}/5] Waiting for InfluxDB... {e}")
        time.sleep(3)
else:
    print("Could not connect to InfluxDB after 5 attempts. Exiting.")
    exit(1)


# 批次邏輯設定
BATCH_SIZE = 5
FLUSH_TIMEOUT = 5  # 秒

buffer = []
# last_flush_time = asyncio.get_event_loop().time()
last_flush_time = time.monotonic()

@app.agent(topic)
async def process(tweets):
    global buffer, last_flush_time

    async for msg in tweets:
        try:
            data = msg
            text = data["text"]
            timestamp = data["timestamp"]
            app.logger.info(f"Received: {text} at {timestamp}")

            buffer.append((text, timestamp))

        except Exception as e:
            app.logger.error(f"Parse failed: {msg} | {e}")
            continue

        now = time.monotonic()
        if len(buffer) >= BATCH_SIZE or now - last_flush_time >= FLUSH_TIMEOUT:
            await flush_buffer()
            last_flush_time = now

# Flush function：包含寫入與錯誤處理
async def flush_buffer():
    global buffer

    if not buffer:
        return
    
    app.logger.info(f"Flushing buffer with {len(buffer)} tweets...")

    try:
        texts, timestamps = zip(*buffer)
        inputs = tokenizer(list(texts), return_tensors="pt", truncation=True, padding=True)

        with torch.no_grad():
            outputs = model(**inputs)
            probs = torch.nn.functional.softmax(outputs.logits, dim=1)
            preds = torch.argmax(probs, dim=1)

        points = []
        for text, timestamp, pred_idx, prob in zip(texts, timestamps, preds, probs):
            sentiment = labels[pred_idx.item()]
            confidence = prob[pred_idx].item()
            point = (
                Point("tweet_sentiment")
                .tag("sentiment", sentiment)
                .field("confidence", confidence)
                .field("text", text)
                .time(timestamp)
            )
            points.append(point)
            app.logger.info(f"{text[:60]}... | {sentiment} ({confidence:.2f})")

        # 寫入
        write_api.write(bucket=bucket, record=points)
        app.logger.info(f"Wrote {len(points)} points to InfluxDB.")


    except Exception as e:
        app.logger.error(f"Error during batch write: {e}")

        # fallback: 每筆嘗試單獨寫入
        for text, timestamp in buffer:
            try:
                inputs = tokenizer(text, return_tensors="pt", truncation=True, padding=True)
                with torch.no_grad():
                    output = model(**inputs)
                    scores = torch.nn.functional.softmax(output.logits[0], dim=0)
                pred_idx = torch.argmax(scores).item()
                confidence = scores[pred_idx].item()
                sentiment = labels[pred_idx]

                point = (
                    Point("tweet_sentiment")
                    .tag("sentiment", sentiment)
                    .field("confidence", confidence)
                    .field("text", text)
                    .time(timestamp)
                )
                write_api.write(bucket=bucket, record=point)
                app.logger.info(f"Fallback OK: {text[:40]}... | {sentiment}")
            except Exception as inner_e:
                app.logger.error(f"Fallback failed for 1 point: {inner_e}")

    finally:
        buffer.clear()
