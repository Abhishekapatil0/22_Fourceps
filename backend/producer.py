import requests
import json
import time
from kafka import KafkaProducer
import feedparser
from datetime import datetime

# Set the RSS feed URLs
BBC_RSS_URL = "https://feeds.bbci.co.uk/news/world/asia/india/rss.xml"
TOI_RSS_URL = "https://timesofindia.indiatimes.com/rssfeeds/-2128936835.cms"  # Times of India - India News

# Set your Guardian API Key
GUARDIAN_API_KEY = "62dc29f7-5423-4f0e-b0ae-710b9fbc395a"  # Replace with your Guardian API key
GUARDIAN_API_URL = f"https://content.guardianapis.com/search?api-key={GUARDIAN_API_KEY}&section=world"

KAFKA_TOPIC = "news_articles"
KAFKA_SERVER = "127.0.0.1:9092"

# Initialize the Kafka producer
producer = KafkaProducer(bootstrap_servers=KAFKA_SERVER,
                         value_serializer=lambda v: json.dumps(v).encode("utf-8"))

# Start page for Guardian API
guardian_page = 1

# Store the timestamp of the last fetched article for both RSS feeds
last_bbc_timestamp = None
last_toi_timestamp = None

def fetch_bbc_news():
    """Fetch news from BBC RSS feed."""
    global last_bbc_timestamp
    feed = feedparser.parse(BBC_RSS_URL)

    if feed.entries:
        for entry in feed.entries:
            # Parse the published date of the article
            published_date = datetime(*entry.published_parsed[:6])

            # Only process the article if it was published after the last fetched article
            if last_bbc_timestamp is None or published_date > last_bbc_timestamp:
                news_data = {"title": entry.title, "url": entry.link}
                producer.send(KAFKA_TOPIC, news_data)
                print(f"Sent from BBC: {news_data['url']}")

                # Update the last fetched timestamp
                if last_bbc_timestamp is None or published_date > last_bbc_timestamp:
                    last_bbc_timestamp = published_date

def fetch_toi_news():
    """Fetch news from Times of India RSS feed."""
    global last_toi_timestamp
    feed = feedparser.parse(TOI_RSS_URL)

    if feed.entries:
        for entry in feed.entries:
            # Parse the published date of the article
            published_date = datetime(*entry.published_parsed[:6])

            # Only process the article if it was published after the last fetched article
            if last_toi_timestamp is None or published_date > last_toi_timestamp:
                news_data = {"title": entry.title, "url": entry.link}
                producer.send(KAFKA_TOPIC, news_data)
                print(f"Sent from TOI: {news_data['url']}")

                # Update the last fetched timestamp
                if last_toi_timestamp is None or published_date > last_toi_timestamp:
                    last_toi_timestamp = published_date


def fetch_guardian_news():
    """Fetch news from Guardian API with pagination."""
    global guardian_page  # Make page variable accessible

    # Add the page number to the request
    url_with_page = f"{GUARDIAN_API_URL}&page={guardian_page}"
    response = requests.get(url_with_page)
    data = response.json()

    if "response" in data and "results" in data["response"]:
        for article in data["response"]["results"]:
            news_data = {"title": article["webTitle"], "url": article["webUrl"]}
            producer.send(KAFKA_TOPIC, news_data)
            print(f"Sent from Guardian: {news_data['url']}")

        # Increment the page number for the next API call
        guardian_page += 1
    else:
        print("Error fetching Guardian news or no results.")


while True:
    fetch_bbc_news()      # Fetch BBC News
    fetch_toi_news()      # Fetch Times of India News
    fetch_guardian_news()  # Fetch Guardian News
    time.sleep(30)  # Fetch news every 20 minutes