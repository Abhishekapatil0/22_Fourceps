from kafka import KafkaConsumer
import json
import asyncio
import aiohttp
from transformers import AutoTokenizer, AutoModelForSequenceClassification, AutoModelForSeq2SeqLM
import torch
import aiomysql
import torch.nn.functional as F
from extractor import Extractor
import torch._dynamo
torch._dynamo.config.suppress_errors = True

# Kafka Configuration
KAFKA_TOPIC = "news_articles"
KAFKA_SERVER = "127.0.0.1:9092"

# MySQL Database Configuration
DB_CONFIG = {
    "host": "127.0.0.1",
    "user": "root",
    "password": "adhesh",
    "db": "news_db"
}

# Initialize Kafka Consumer
consumer = KafkaConsumer(KAFKA_TOPIC,
                         bootstrap_servers=KAFKA_SERVER,
                         value_deserializer=lambda v: json.loads(v.decode("utf-8")))

# Move models to GPU if available
device = "cuda" if torch.cuda.is_available() else "cpu"

# Load category classification model
category_model_path = r"C:/Users/Adhesh Rajath/OneDrive/Desktop/NewsPulse/news_category_classifier"
category_tokenizer = AutoTokenizer.from_pretrained(category_model_path)
category_model = AutoModelForSequenceClassification.from_pretrained(category_model_path).to(device).eval()

# Category mapping
category_mapping = {
    24: "POLITICS", 38: "WELLNESS", 10: "ENTERTAINMENT", 34: "TRAVEL", 3: "BUSINESS",
    28: "SPORTS", 33: "THE WORLDPOST", 6: "CRIME", 18: "IMPACT", 40: "WORLD NEWS",
    20: "MEDIA", 26: "RELIGION", 27: "SCIENCE", 32: "TECH"
}

# GoEmotions sentiment analysis setup
goemotions_tokenizer = AutoTokenizer.from_pretrained("SamLowe/roberta-base-go_emotions")
goemotions_model = AutoModelForSequenceClassification.from_pretrained(
    "SamLowe/roberta-base-go_emotions"
).to(device).eval()

goemotions_labels = [
    "admiration", "amusement", "anger", "annoyance", "approval", "caring", "confusion", "curiosity", "desire",
    "disappointment", "disapproval", "disgust", "embarrassment", "excitement", "fear", "gratitude", "grief", "joy",
    "love", "nervousness", "optimism", "pride", "realization", "relief", "remorse", "sadness", "surprise", "neutral"
]

positive_emotions = {"admiration", "amusement", "approval", "caring", "curiosity", "desire", "excitement",
                     "gratitude", "joy", "love", "optimism", "pride", "realization", "relief"}
negative_emotions = set(goemotions_labels) - positive_emotions - {"neutral"}

# Load summarization model
summarize_tokenizer = AutoTokenizer.from_pretrained("Yooniii/Article_summarizer")
summarize_model = AutoModelForSeq2SeqLM.from_pretrained("Yooniii/Article_summarizer").to(device).eval()

async def fetch_and_extract(session, url):
    try:
        async with session.get(url, timeout=10) as response:
            html = await response.text()
        ext = Extractor(url=url, html=html, output="html", threshold=0.5)
        title, content = ext.parse()
        return title, content
    except Exception as e:
        print(f"Error processing {url}: {e}")
        return None, None

async def parse_articles(urls):
    async with aiohttp.ClientSession() as session:
        tasks = [fetch_and_extract(session, url) for url in urls]
        return await asyncio.gather(*tasks)

def classify_texts(texts):
    inputs = category_tokenizer(texts, return_tensors="pt", truncation=True, padding=True).to(device)
    with torch.no_grad():
        logits = category_model(**inputs).logits
    predicted_labels = torch.argmax(logits, dim=-1).tolist()
    return [category_mapping.get(label, "UNKNOWN") for label in predicted_labels]

def classify_sentiments(texts, batch_size=8):
    predictions = []
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i+batch_size]
        inputs = goemotions_tokenizer(batch, return_tensors="pt", truncation=True, padding=True).to(device)
        
        with torch.no_grad():
            logits = goemotions_model(**inputs).logits
        probabilities = F.softmax(logits, dim=-1).cpu().numpy()
        
        for probs in probabilities:
            positive_score = sum(probs[i] for i, label in enumerate(goemotions_labels) if label in positive_emotions)
            negative_score = sum(probs[i] for i, label in enumerate(goemotions_labels) if label in negative_emotions)
            neutral_score = probs[goemotions_labels.index("neutral")]
            
            total = positive_score + negative_score + neutral_score
            if total > 0:
                positive_score /= total
                negative_score /= total
                neutral_score /= total
            
            if neutral_score > 0.5:
                predictions.append("positive" if positive_score >= negative_score else "negative")
            else:
                predictions.append("positive" if positive_score > negative_score else "negative")
    
    return predictions

def summarize_articles(articles):
    inputs = summarize_tokenizer(articles, return_tensors="pt", truncation=True, padding=True, max_length=1024).to(device)
    summary_ids = summarize_model.generate(
        inputs.input_ids,
        max_length=120,
        min_length=60,
        length_penalty=1.5,
        num_beams=6,
        early_stopping=True
    )
    return summarize_tokenizer.batch_decode(summary_ids, skip_special_tokens=True)

async def create_table_if_not_exists():
    try:
        conn = await aiomysql.connect(**DB_CONFIG)
        async with conn.cursor() as cursor:
            query = """
            CREATE TABLE IF NOT EXISTS news_analytics_results (
                id INT AUTO_INCREMENT PRIMARY KEY,
                title VARCHAR(255),
                url VARCHAR(255),
                summary TEXT,
                classification VARCHAR(100),
                sentiment VARCHAR(50),
                source VARCHAR(50)
            )
            """
            await cursor.execute(query)
            await conn.commit()
        await conn.ensure_closed()
        print("✅ Table created or already exists.")
    except Exception as e:
        print(f"❌ Error creating table: {e}")

def extract_source(url):
    if "bbc.com" in url:
        return "BBC"
    elif "timesofindia.indiatimes.com" in url:
        return "Times of India"
    elif "theguardian.com" in url:
        return "The Guardian"
    return "Unknown"

async def store_in_mysql(title, url, summary, classification, sentiment):
    source = extract_source(url)
    try:
        conn = await aiomysql.connect(**DB_CONFIG)
        async with conn.cursor() as cursor:
            query = """
            INSERT INTO news_analytics_results (title, url, summary, classification, sentiment, source) 
            VALUES (%s, %s, %s, %s, %s, %s)
            """
            await cursor.execute(query, (title, url, summary, classification, sentiment, source))
            await conn.commit()
        await conn.ensure_closed()
        print(f"✅ Stored in MySQL: {title} (Source: {source})")
    except Exception as e:
        print(f"❌ Error storing in MySQL: {e}")

async def main(urls):
    await create_table_if_not_exists()
    extracted_data = await parse_articles(urls)
    valid_data = [(url, title, content) for url, (title, content) in zip(urls, extracted_data) if content]
    if not valid_data:
        print("No valid content extracted.")
        return
    urls, titles, contents = zip(*valid_data)
    categories = classify_texts(contents)
    sentiments = classify_sentiments(contents)
    summaries = summarize_articles(contents)
    for url, title, content, category, sentiment, summary in zip(urls, titles, contents, categories, sentiments, summaries):
        await store_in_mysql(title, url, summary, category, sentiment)

async def process_batch(batch):
    await main(batch)

urls = []
BATCH_SIZE = 5

print("Waiting for news articles...")

for message in consumer:
    news = message.value
    url = news['url']
    urls.append(url)
    print(f"Received: {url}")
    if len(urls) >= BATCH_SIZE:
        asyncio.run(process_batch(urls))
        urls = []