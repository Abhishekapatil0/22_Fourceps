import asyncio
import aiomysql
import aiohttp
from transformers import AutoTokenizer, AutoModelForSequenceClassification, AutoModelForSeq2SeqLM
import torch
import torch.nn.functional as F

# Move models to GPU if available
device = "cuda" if torch.cuda.is_available() else "cpu"
print(torch.cuda.get_device_name(0) if torch.cuda.is_available() else "No GPU found")

# MySQL Database Configuration
DB_CONFIG = {
    "host": "127.0.0.1",
    "user": "root",
    "password": "BeqFUzW8",
    "db": "news_db"
}

# Load models
classify_tokenizer = AutoTokenizer.from_pretrained("Yueh-Huan/news-category-classification-distilbert")
classify_model = AutoModelForSequenceClassification.from_pretrained(
    "Yueh-Huan/news-category-classification-distilbert", from_tf=True
).to(device).half().eval()

sentiment_tokenizer = AutoTokenizer.from_pretrained("cardiffnlp/twitter-xlm-roberta-base-sentiment")
sentiment_model = AutoModelForSequenceClassification.from_pretrained(
    "cardiffnlp/twitter-xlm-roberta-base-sentiment"
).to(device).half().eval()

summarize_tokenizer = AutoTokenizer.from_pretrained("Yooniii/Article_summarizer")
summarize_model = AutoModelForSeq2SeqLM.from_pretrained("Yooniii/Article_summarizer").to(device).half().eval()

if hasattr(torch, 'compile'):
    summarize_model = torch.compile(summarize_model)

# Sample Content for Debugging
sample_contents = [
    "Breaking news: Stock markets crash amid economic downturn. Investors are concerned about rising interest rates and global recession fears, leading to a sharp selloff across major indices.",
    "Scientists discover new exoplanet with potential for life. The planet, located in a habitable zone, shows promising signs of having liquid water, raising hopes for extraterrestrial life.",
]

# Ensure table exists
async def ensure_table_exists():
    try:
        conn = await aiomysql.connect(**DB_CONFIG)
        async with conn.cursor() as cursor:
            create_table_query = """
            CREATE TABLE IF NOT EXISTS news_articles (
                id INT AUTO_INCREMENT PRIMARY KEY,
                title VARCHAR(255) NOT NULL,
                content TEXT NOT NULL,
                category VARCHAR(255) NOT NULL,
                sentiment VARCHAR(255) NOT NULL,
                summary TEXT NOT NULL
            )
            """
            await cursor.execute(create_table_query)
            await conn.commit()
        await conn.ensure_closed()
        print("✅ Table check complete.")
    except Exception as e:
        print(f"❌ Error ensuring table exists: {e}")

# Classify Articles
def classify_texts(texts):
    inputs = classify_tokenizer(texts, return_tensors="pt", truncation=True, padding=True).to(device)
    with torch.no_grad():
        logits = classify_model(**inputs).logits
    predicted_classes = torch.argmax(logits, dim=1).tolist()
    return [classify_model.config.id2label.get(pred, "Unknown") for pred in predicted_classes]

# Classify Sentiment
def classify_sentiments(texts):
    if not texts:
        return []
    inputs = sentiment_tokenizer(texts, return_tensors="pt", truncation=True, padding=True, max_length=512).to(device)
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

# Store Data in MySQL
async def store_in_mysql(title, content, category, sentiment, summary):
    try:
        conn = await aiomysql.connect(**DB_CONFIG)
        async with conn.cursor() as cursor:
            query = """
            INSERT INTO news_articles (title, content, category, sentiment, summary) 
            VALUES (%s, %s, %s, %s, %s)
            """
            await cursor.execute(query, (title, content, category, sentiment, summary))
            await conn.commit()
        await conn.ensure_closed()
        print(f"✅ Stored in MySQL: {title}")
    except Exception as e:
        print(f"❌ Error storing in MySQL: {e}")

# Process Sample Content
async def process_articles():
    await ensure_table_exists()
    categories = classify_texts(sample_contents)
    sentiments = classify_sentiments(sample_contents)
    summaries = summarize_articles(sample_contents)

    for i, content in enumerate(sample_contents):
        title = f"Article {i+1}"
        await store_in_mysql(title, content, categories[i], sentiments[i], summaries[i])

asyncio.run(process_articles())