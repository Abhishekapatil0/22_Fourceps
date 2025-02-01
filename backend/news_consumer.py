from kafka import KafkaConsumer
import json
import requests
from urllib.parse import urlparse

KAFKA_TOPIC = "news_articles"
KAFKA_SERVER = "localhost:9092"

consumer = KafkaConsumer(KAFKA_TOPIC,
                         bootstrap_servers=KAFKA_SERVER,
                         value_deserializer=lambda v: json.loads(v.decode("utf-8")))

def can_scrape(url):
    """Check if a website allows scraping based on robots.txt"""
    domain = urlparse(url).netloc
    robots_url = f"https://{domain}/robots.txt"

    try:
        response = requests.get(robots_url, timeout=5)
        
        if response.status_code == 200:
            robots_txt = response.text.lower()
            if "disallow: /" in robots_txt:
                return False, f"Scraping NOT allowed (robots.txt restriction)"
            return True, f"Scraping allowed"
        
        elif response.status_code == 404:
            return None, f"No robots.txt found (Check ToS manually)"
        
        else:
            return None, f"Robots.txt unavailable (HTTP {response.status_code})"
    
    except requests.RequestException:
        return None, f"Could not retrieve robots.txt (Possible network issue)"

print("Waiting for news articles...")

for message in consumer:
    news = message.value
    url = news['url']

    can_scrape_status, reason = can_scrape(url)

    print(f"Received: {url} → {reason}")