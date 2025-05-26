import time
import docker
import smtplib
import logging
import os
from dotenv import load_dotenv
from email.mime.text import MIMEText

load_dotenv()

# 設定參數
CONTAINER_NAME = "kafka-worldcount-demo"
CHECK_INTERVAL = 15  # N 秒 check 一次容器狀態
FAIL_ALERT_INTERVAL = 5  # 每 N 次失敗再發信

# Email 設定
SMTP_SERVER = os.getenv('SMTP_SERVER')
SMTP_PORT = os.getenv('SMTP_PORT')
SMTP_USER = os.getenv('SMTP_USER')
SMTP_PASSWORD = os.getenv('SMTP_PASSWORD') # 寄件者密碼（建議用 Gmail 應用程式專用密碼，不要用一般登入密碼）
ALERT_TO = os.getenv('ALERT_TO')

# Logging 設定
LOG_FILE = "monitor.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler()
    ]
)

def send_alert(subject, message):
    msg = MIMEText(message)
    msg['Subject'] = subject
    msg['From'] = SMTP_USER
    msg['To'] = ALERT_TO

    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(SMTP_USER, [ALERT_TO], msg.as_string())
        logging.info(f"Sent alert email: {subject}")
    except Exception as e:
        logging.error(f"Failed to send alert email: {e}")

def is_container_running(container_name):
    client = docker.from_env()
    try:
        container = client.containers.get(container_name)
        return container.attrs["State"]["Status"] == "running"
    except docker.errors.NotFound:
        return False
    except Exception as e:
        logging.error(f"Docker error: {e}")
        return False

if __name__ == "__main__":
    last_status = True  # 假設一開始是正常
    fail_count = 0

    while True:
        running = is_container_running(CONTAINER_NAME)
        now = time.ctime()

        if running:
            if not last_status:
                # 容器恢復時發信
                subject = f"RECOVERY: Kafka container '{CONTAINER_NAME}' is running again"
                message = f"The container '{CONTAINER_NAME}' recovered at {now}."
                send_alert(subject, message)
                logging.info(f"Container '{CONTAINER_NAME}' recovered at {now}")
                fail_count = 0  # 重置失敗計數
            else:
                logging.info(f"Container '{CONTAINER_NAME}' is running at {now}")
            last_status = True
        else:
            fail_count += 1
            if last_status or fail_count % FAIL_ALERT_INTERVAL == 0:
                # 第一次失敗 或 每 N 次失敗發信
                subject = f"ALERT: Kafka container '{CONTAINER_NAME}' is not running!"
                message = f"The container '{CONTAINER_NAME}' was found stopped or missing at {now}. (fail count: {fail_count})"
                send_alert(subject, message)
                logging.error(f"Container '{CONTAINER_NAME}' is not running at {now} (fail count: {fail_count})")
            else:
                logging.error(f"Container '{CONTAINER_NAME}' is still not running at {now} (fail count: {fail_count})")
            last_status = False

        time.sleep(CHECK_INTERVAL)
