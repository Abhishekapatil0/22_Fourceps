import asyncio
import aiohttp
from transformers import AutoTokenizer, AutoModelForSequenceClassification, AutoModelForSeq2SeqLM
import torch
from pymongo import MongoClient
from extractor import Extractor
import torch.nn.functional as F

# Move models to GPU if available
device = "cuda" if torch.cuda.is_available() else "cpu"

# MongoDB Connection (Replace with your MongoDB Atlas or Compass URI)
MONGO_URI = "mongodb+srv://Adhesh_R:DeadlyIdli@cluster0.hbo0p.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
client = MongoClient(MONGO_URI)

db = client["news_db"]   # Database
collection = db["articles"]  # Collection

# Load models
classify_tokenizer = AutoTokenizer.from_pretrained("Yueh-Huan/news-category-classification-distilbert")
classify_model = AutoModelForSequenceClassification.from_pretrained(
    "Yueh-Huan/news-category-classification-distilbert", from_tf=True
).to(device).half().eval()

sentiment_tokenizer = AutoTokenizer.from_pretrained("nlptown/bert-base-multilingual-uncased-sentiment")
sentiment_model = AutoModelForSequenceClassification.from_pretrained(
    "nlptown/bert-base-multilingual-uncased-sentiment"
).to(device).half().eval()

summarize_tokenizer = AutoTokenizer.from_pretrained("Yooniii/Article_summarizer")
summarize_model = AutoModelForSeq2SeqLM.from_pretrained("Yooniii/Article_summarizer").to(device).half().eval()

# Compile model for performance if PyTorch 2.0+
if hasattr(torch, 'compile'):
    summarize_model = torch.compile(summarize_model)

# Fetch and Extract Content
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

# Parse Articles
async def parse_articles(urls):
    async with aiohttp.ClientSession() as session:
        tasks = [fetch_and_extract(session, url) for url in urls]
        return await asyncio.gather(*tasks)

# Classify Articles
def classify_texts(texts):
    inputs = classify_tokenizer(texts, return_tensors="pt", truncation=True, padding=True).to(device)
    with torch.no_grad():
        logits = classify_model(**inputs).logits
    predicted_classes = torch.argmax(logits, dim=1).tolist()
    return [classify_model.config.id2label.get(pred, "Unknown") for pred in predicted_classes]

# Classify Sentiment
def classify_sentiments(texts):
    inputs = sentiment_tokenizer(texts, return_tensors="pt", truncation=True, padding=True).to(device)
    with torch.no_grad():
        logits = sentiment_model(**inputs).logits
    probabilities = F.softmax(logits, dim=-1)
    predicted_classes = torch.argmax(probabilities, dim=-1) + 1
    sentiment_labels = ["Very Negative", "Negative", "Neutral", "Positive", "Very Positive"]
    return [sentiment_labels[pred.item() - 1] for pred in predicted_classes]

# Summarize Articles
def summarize_articles(articles):
    inputs = summarize_tokenizer(articles, return_tensors="pt", truncation=True, padding=True, max_length=1024).to(device)
    summary_ids = summarize_model.generate(
        inputs.input_ids, max_length=120, min_length=60, length_penalty=1.5, num_beams=6, early_stopping=True
    )
    return summarize_tokenizer.batch_decode(summary_ids, skip_special_tokens=True)

# Store Data in MongoDB
def store_in_mongodb(title, url, content, category, sentiment, summary):
    article_data = {
        "title": title,
        "url": url,
        "content": content,
        "category": category,
        "sentiment": sentiment,
        "summary": summary
    }
    collection.insert_one(article_data)
    print(f"✅ Stored in MongoDB: {title}")

# Main Function
async def main(urls):
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
        store_in_mongodb(title, url, content, category, sentiment, summary)

if __name__ == "__main__":
    urls = [
        "https://www.bbc.com/sport/formula1/articles/c4g7j0j8357o",
        "https://www.bbc.com/news/articles/cg5ydgeqrvqo",
        "https://www.bbc.com/sport/formula1/articles/cm21e8pj24lo",
        "https://www.bbc.com/news/articles/c78x4ngjyy9o",
        "https://www.bbc.com/sport/formula1/articles/c4g7j0j8357o",
        "https://www.bbc.com/news/articles/c9vm1m8wpr9o",
        "https://www.bbc.com/travel/article/20250124-tia-carreres-family-guide-to-visiting-hawaii",
        "https://www.bbc.com/news/articles/cn9370dny5xo",
        "https://www.bbc.com/sport/rugby-union/articles/c334p3z1mneo",
        "https://www.bbc.com/news/live/cy7kxx74yxlt"
    ]
    asyncio.run(main(urls))
