from kafka import KafkaConsumer
from wordcloud import WordCloud
import matplotlib.pyplot as plt
import json
from collections import defaultdict
import time

KAFKA_SERVER = 'localhost:9092'
TOPIC = 'streams-wordcount-output'

consumer = KafkaConsumer(
    TOPIC,
    bootstrap_servers=[KAFKA_SERVER],
    auto_offset_reset='earliest',
    enable_auto_commit=True,
    consumer_timeout_ms=10000,
    key_deserializer=lambda m: m.decode('utf-8') if m else None,  # String
    value_deserializer=lambda m: int.from_bytes(m, byteorder='big', signed=False) if m else 0  # Long (unsigned)
)

# 收集詞頻數據
word_freq = {}
message_count = 0

try:
    start_time = time.time()
    
    for message in consumer:
        word = message.key
        count = message.value
        
        if word:
            word_freq[word] = count
            print(f"讀取: {word} = {count}")
            
        message_count += 1
        
        if message_count >= 50:
            print("達到最大讀取數量，停止...")
            break
            
except Exception as e:
    print(f"讀取過程中出現異常: {e}")
    
finally:
    consumer.close()
    
print(f"\n總共讀取了 {message_count} 條消息")
print(f"找到 {len(word_freq)} 個不同的單字")

if not word_freq:
    print("❌ 沒有讀取到任何數據！")
    exit()

# 顯示所有讀取到的數據
print("\n所有單字統計:")
for word, count in sorted(word_freq.items(), key=lambda x: x[1], reverse=True):
    print(f"  {word}: {count}")

# 過濾數據
filtered_freq = {
    word: count 
    for word, count in word_freq.items() 
    if count >= 1 and len(word) > 1
}

print(f"\n過濾後剩餘 {len(filtered_freq)} 個單字")

# 創建文字雲
if filtered_freq:
    try:
        wordcloud = WordCloud(
            width=800, 
            height=400, 
            background_color='white',
            max_words=100,
            colormap='viridis',
            min_font_size=10
        ).generate_from_frequencies(filtered_freq)
        
        # 顯示文字雲
        plt.figure(figsize=(12, 6))
        plt.imshow(wordcloud, interpolation='bilinear')
        plt.axis('off')
        plt.title('X WordCloud', fontsize=16)
        plt.tight_layout()
        
        # 保存文字雲
        plt.savefig('kafka_wordcloud.png', dpi=300, bbox_inches='tight')
        print(f"✅ 文字雲已保存為 kafka_wordcloud.png")
        
    except Exception as e:
        print(f"生成文字雲時出錯: {e}")
        
else:
    print("❌ 沒有足夠的數據生成文字雲")