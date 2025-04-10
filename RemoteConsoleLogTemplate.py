import psutil
import requests
import json
import time

# Replace with your actual webhook URL
SLACK_WEBHOOK_URL = 'https://hooks.slack.com/services/your/webhook/url'
PROCESS_NAME = 'your_process_name'  # e.g., 'javac' for Java, 'gcc' for C/C++

def send_slack_notification(message):
    payload = {
        "text": message
    }
    requests.post(SLACK_WEBHOOK_URL, data=json.dumps(payload), headers={'Content-Type': 'application/json'})

def check_process():
    for proc in psutil.process_iter(['name']):
        if proc.info['name'] == PROCESS_NAME:
            return True
    return False

if __name__ == "__main__":
    while True:
        if check_process():
            send_slack_notification(f"{PROCESS_NAME} is currently running.")
        else:
            send_slack_notification(f"{PROCESS_NAME} is not running.")
        
        time.sleep(10)  # Check every 10 seconds
