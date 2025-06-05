from dotenv import load_dotenv
import os
import logging
import time
from typing import Optional
import tweepy
from kafka import KafkaProducer

# 環境變數
load_dotenv()

# 配置日誌
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 配置常數
KAFKA_SERVERS = 'localhost:9092'
KAFKA_TOPIC = 'streams-plaintext-input'

# X API 配置
BEARER_TOKEN = os.getenv('TWITTER_BEARER_TOKEN')
SEARCH_QUERY = "#AI OR #Tech -is:retweet" # 關鍵字先搜尋 AI Tech 相關 tag
MAX_TWEETS = 10  # 每次抓 10 則推文，避免免費 API 額度沒了


def handle_rate_limit(client: tweepy.Client, query: str, max_results: int = 10, 
                     retry_count: int = 3, retry_delay: int = 15,
                     tweet_fields: Optional[list] = None) -> Optional[tweepy.Response]:
    """
    處理API速率限制的搜索函數
    
    Args:
        client: Tweepy客戶端
        query: 搜索查詢
        max_results: 返回的最大結果數
        retry_count: 重試次數
        retry_delay: 重試延遲(秒)
        tweet_fields: 要獲取的推文欄位
    
    Returns:
        搜索結果或None
    """
    if tweet_fields is None:
        tweet_fields = ["created_at", "author_id", "public_metrics"]
        
    attempt = 0
    
    while attempt < retry_count:
        try:
            logger.info(f"執行搜索查詢: {query}，嘗試 #{attempt+1}")
            
            # 執行API呼叫
            results = client.search_recent_tweets(
                query=query,
                max_results=max_results,
                tweet_fields=tweet_fields
            )
            
            logger.info("API呼叫成功")
            return results
            
        except tweepy.TooManyRequests as e:
            # 獲取響應頭中的剩餘時間
            reset_time = int(e.response.headers.get('x-rate-limit-reset', 0)) - int(time.time())
            wait_time = max(reset_time, retry_delay)
            
            logger.warning(f"達到速率限制! 等待 {wait_time} 秒後重試...")
            time.sleep(wait_time)
            attempt += 1
            
        except tweepy.TwitterServerError as e:
            logger.error(f"Twitter伺服器錯誤: {e}")
            time.sleep(retry_delay)
            attempt += 1
            
        except Exception as e:
            logger.error(f"搜索過程中發生錯誤: {e}")
            return None
            
    logger.error(f"達到最大重試次數 ({retry_count})，放棄搜索")
    return None


def fetch_real_tweets():
    """從 X API 獲取真實推文"""
    try:
        if not BEARER_TOKEN:
          logger.error("缺少 TWITTER_BEARER_TOKEN 環境變數")
          exit(1)

        client = tweepy.Client(bearer_token=BEARER_TOKEN)
        
        search_results = handle_rate_limit(
            client=client,
            query=SEARCH_QUERY,
            max_results=MAX_TWEETS
        )
        
        if not search_results or not search_results.data:
            logger.warning("未找到符合條件的推文")
            return []
        
        # 轉換為需要的格式
        tweets = []
        for tweet in search_results.data:
            tweets.append({
                "id": str(tweet.id),
                "text": tweet.text,
                "author_id": str(tweet.author_id)
            })
        
        logger.info(f"成功獲取 {len(tweets)} 條推文")
        return tweets
        
    except Exception as e:
        logger.error(f"獲取推文時發生錯誤: {e}")
        return []


def create_kafka_producer():
    """建立 Kafka Producer"""
    producer = KafkaProducer(
        bootstrap_servers=KAFKA_SERVERS,
        value_serializer=lambda x: x.encode('utf-8')
    )
    logger.info("Kafka Producer 已連接")
    return producer


def main():
    logger.info("開始從 X API 獲取推文並發送到 Kafka...")
    
    # 獲取推文
    tweets = fetch_real_tweets()
    
    if not tweets:
        logger.error("沒有獲取到推文數據，程序結束")
        return
    
    # 發送到 Kafka
    producer = create_kafka_producer()
    try:
        logger.info("開始發送推文到 Kafka...")
        
        for i, tweet_data in enumerate(tweets):
            tweet_text = tweet_data["text"]
            producer.send(KAFKA_TOPIC, value=tweet_text)
            logger.info(f"已發送推文 {i+1}/{len(tweets)}: {tweet_text}")
        
        producer.flush()
        logger.info("✅ 所有推文發送完成")
        
    except Exception as e:
        logger.error(f"發送到 Kafka 時發生錯誤: {e}")
    finally:
        producer.close()
        logger.info("Kafka Producer 已關閉")


if __name__ == "__main__":
    main()