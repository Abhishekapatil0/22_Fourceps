import requests
import json
import time
from kafka import KafkaProducer
import feedparser

# Set the BBC RSS feed URL for India (Asia section)
BBC_RSS_URL = "https://feeds.bbci.co.uk/news/world/asia/india/rss.xml"

# Set your Guardian API Key
GUARDIAN_API_KEY = "62dc29f7-5423-4f0e-b0ae-710b9fbc395a"  # Replace with your Guardian API key
GUARDIAN_API_URL = f"https://content.guardianapis.com/search?api-key={GUARDIAN_API_KEY}&section=world"

KAFKA_TOPIC = "news_articles"
KAFKA_SERVER = "localhost:9092"

# Initialize the Kafka producer
producer = KafkaProducer(bootstrap_servers=KAFKA_SERVER,
                         value_serializer=lambda v: json.dumps(v).encode("utf-8"))

def fetch_bbc_news():
    # Fetch the BBC RSS feed
    feed = feedparser.parse(BBC_RSS_URL)

    # Check if the feed contains entries
    if feed.entries:
        for entry in feed.entries:
            # Filter out entries that have '/videos' in the URL
            if '/videos' not in entry.link:
                # Prepare the news data (title and URL)
                news_data = {"title": entry.title, "url": entry.link}
                producer.send(KAFKA_TOPIC, news_data)  # Send to Kafka topic
                print(f"Sent from BBC: {news_data['url']}")

def fetch_guardian_news():
    # Fetch news from the Guardian API (international news)
    response = requests.get(GUARDIAN_API_URL)
    data = response.json()

    # Check if the response contains results
    if "response" in data and "results" in data["response"]:
        for article in data["response"]["results"]:
            # Prepare the news data (title and URL)
            news_data = {"title": article["webTitle"], "url": article["webUrl"]}
            producer.send(KAFKA_TOPIC, news_data)  # Send to Kafka topic
            print(f"Sent from Guardian: {news_data['url']}")

while True:
    fetch_bbc_news()        # Fetch BBC news
    fetch_guardian_news()   # Fetch Guardian international news
    time.sleep(30)  # Fetch news every 30 seconds