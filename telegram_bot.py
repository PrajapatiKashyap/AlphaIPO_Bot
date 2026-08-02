import requests
import urllib.parse
from config import BOT_TOKEN, CHAT_ID

def send_message(message: str) -> bool:
    """
    Sends a message to the configured Telegram chat using the Telegram Bot API.
    Returns True if successful, False otherwise.
    """
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }
    
    # Retry once on failure
    for attempt in range(2):
        try:
            print(f"Sending Telegram Alert (attempt {attempt + 1})...")
            response = requests.post(url, json=payload, timeout=10)
            if response.status_code == 200:
                print("Telegram message sent successfully.")
                return True
            else:
                print(f"Telegram API error: HTTP {response.status_code} - {response.text}")
        except Exception as e:
            print(f"Telegram connection error on attempt {attempt + 1}: {e}")
            
    return False
