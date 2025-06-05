1. 設置環境變數 : `.env` 文件
  
    `TWITTER_BEARER_TOKEN=`
  
2. 啟動 Kafka
  
    `docker-compose up -d`

3. 安裝 Python 相關套件

    `pip install kafka-python tweepy python-dotenv wordcloud matplotlib`

4. 啟動 WordCount 處理器 : 進入 Kafka 容器並啟動 WordCount Demo
    ```
    docker exec -it kafka-worldcount-demo bash
    cd opt/kafka
    bin/kafka-run-class.sh org.apache.kafka.streams.examples.wordcount.WordCountDemo
    ```

5. 呼叫 X API，取得推文並發送到 Kafka
    
    `python twitter_producer.py`

6. 生成文字雲 : 從 Kafka 讀取詞頻統計結果並生成文字雲

    `python wordcloud_generator.py`