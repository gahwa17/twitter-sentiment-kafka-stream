# 🐦 Twitter Sentiment Analysis with Kafka, Faust, and InfluxDB

本專案實作一個以 Kafka 為核心的串流處理系統，用於分析 Twitter 貼文的情緒，並將分析結果存入 InfluxDB，最後透過 Grafana 可視化。

---

## 📦 專案架構

producer.py → Kafka topic (tweets_raw) → stream.py (Faust + twitter-roberta-base-sentiment model)
↓
InfluxDB
↓
Grafana

- **Kafka**：建置三個 broker，實現高可用與高吞吐
- **Faust**：Python 串流框架，作為 Kafka consumer 與處理邏輯
- **Transformers**：使用 `cardiffnlp/twitter-roberta-base-sentiment` 進行情緒分析
- **InfluxDB**：存放分析結果
- **Grafana**：展示情緒分析資料

## 🚀 啟動流程

1. 環境變數（.env）
   請建立 .env 並填入以下內容：
   INFLUXDB_URL=http://influxdb:8086
   INFLUXDB_TOKEN=(your_token) （若第一次啟用，請填'mytoken'）
   INFLUXDB_ORG=myorg
   INFLUXDB_BUCKET=tweets

2. 啟動 Kafka containers (Kafka1, Kafka2, Kafka3)

3. 初始化 Kafka topic:
   (在 Kafka 三個 broker 啟動後執行，確保 topic tweets_raw 被正確建立且具備多分區與複本數設定。)
   chmod +x ./init-topics.sh
   ./init-topics.sh

4. 啟動所有其他容器服務（InfluxDB、Grafana、Producer、Faust Stream 等）

5. 開啟 InfluxDB 確認有成功寫入資料：
   前往瀏覽器開啟： http://localhost:8086 （預設帳密 admin / admin123）

6. 開啟 Grafana:
   前往瀏覽器開啟： http://localhost:3000（預設帳密 admin / admin）
   設定 InfluxDB 作為資料來源
   建立 Dashboard，可視化不同情緒類別的 tweet 數量、趨勢等

## 專案架構

.
├── docker-compose.yml
├── .env
├── producer/
│ └── producer.py
│ └── Dockerfile
│ └── requirements.txt
├── stream/
│ └── stream.py
│ └── Dockerfile
│ └── requirements.txt
├── twitter_raw_data/
│ └── tweets.json
├── init-topics.sh

## 備註:

1. 請先確認 Kafka 三個 brokers 都已啟動，否則 init-topics.sh 無法成功執行
2. 可調整 BATCH_SIZE 與 FLUSH_TIMEOUT 控制分析頻率與即時程度
