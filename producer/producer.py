import tweepy, json, time, os
from kafka import KafkaProducer
from dotenv import load_dotenv
from datetime import datetime, timedelta, timezone

# 載入 .env 中的環境變數
load_dotenv()

# BEARER_TOKEN = os.getenv("BEARER_TOKEN")
# if not BEARER_TOKEN:
#     raise ValueError("BEARER_TOKEN not found in environment variables!")

producer = KafkaProducer(
    bootstrap_servers=[
        'kafka1:9092',
        'kafka2:9092',
        'kafka3:9092'
        ],
    value_serializer=lambda x: json.dumps(x).encode('utf-8')
)

# client = tweepy.Client(bearer_token=BEARER_TOKEN)
# query = "(AI OR Ai OR ai) lang:en -is:retweet" #抓含有 "AI" 關鍵字的文章（英文推文），排除轉推內容，只抓原創推文


# 載入 tweets.json 資料
json_path = os.path.join("twitter_raw_data", "tweets.json")
if not os.path.exists(json_path):
    raise FileNotFoundError(f"{json_path} not found!")

with open(json_path, "r", encoding="utf-8") as f:
    tweets = json.load(f)

# 建立當天 00:00 的 UTC 時間基準
base_time = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)

# 傳送資料到 Kafka topic
for i, msg in enumerate(tweets):
    
    fake_time = base_time + timedelta(minutes=i)
    msg["timestamp"] = fake_time.isoformat()

    try:
        producer.send("tweets_raw", msg)
        time.sleep(1)
        print(f"Sent tweet [{i+1}]: {msg['timestamp']} | {msg['text'][:50]}...")
    except Exception as e:
        print("Kafka send error:", e)

producer.flush()
print("All tweets from file sent!")

# # 傳送資料到 Kafka topic
# for msg in tweets:
#     try:
#         producer.send("tweets_raw", msg)
#         time.sleep(3)  # 模擬間隔
#         print(f"Sent tweet: {msg['text'][:50]}...")
#     except Exception as e:
#         print("Kafka send error:", e)

# producer.flush()
# print("All tweets from file sent!")


