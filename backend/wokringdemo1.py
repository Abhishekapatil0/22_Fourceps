import asyncio
import aiomysql
import aiohttp
from transformers import AutoTokenizer, AutoModelForSequenceClassification, AutoModelForSeq2SeqLM
import torch
from extractor import Extractor

# GPU Configuration
device = "cuda" if torch.cuda.is_available() else "cpu"
torch.cuda.set_per_process_memory_fraction(0.8)  # Strict 80% memory limit
print(f"Using device: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU'}")

# Batch sizes for 4GB VRAM
BATCH_SIZES = {
    "classify": 2,
    "sentiment": 2,
    "summarize": 1
}

# Model Configuration
MODEL_CONFIG = {
    "classify": {
        "name": "Yueh-Huan/news-category-classification-distilbert",
        "max_length": 256
    },
    "sentiment": {
        "name": "nlptown/bert-base-multilingual-uncased-sentiment",
        "max_length": 256
    },
    "summarize": {
        "name": "Yooniii/Article_summarizer",
        "max_length": 512,
        "gen_max_length": 100
    }
}

# MySQL Configuration
DB_CONFIG = {
    "host": "127.0.0.1",
    "user": "root",
    "password": "BeqFUzW8",
    "db": "news_db",
    "autocommit": True
}

# Load models with memory optimization
classify_tokenizer = AutoTokenizer.from_pretrained(MODEL_CONFIG["classify"]["name"])
classify_model = AutoModelForSequenceClassification.from_pretrained(
    MODEL_CONFIG["classify"]["name"],
    from_tf=True  # Critical fix for TensorFlow weights
).to(device).half().eval()

sentiment_tokenizer = AutoTokenizer.from_pretrained(MODEL_CONFIG["sentiment"]["name"])
sentiment_model = AutoModelForSequenceClassification.from_pretrained(
    MODEL_CONFIG["sentiment"]["name"]
).to(device).half().eval()

summarize_tokenizer = AutoTokenizer.from_pretrained(MODEL_CONFIG["summarize"]["name"])
summarize_model = AutoModelForSeq2SeqLM.from_pretrained(
    MODEL_CONFIG["summarize"]["name"]
).to(device).half().eval()



async def fetch_and_extract(session, url):
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as response:
            html = await response.text()
        # Add required parameters for Extractor
        ext = Extractor(
            url=url, 
            html=html,
            threshold=0.5,  # Add threshold
            output="html"   # Add output format
        )
        title, content = ext.parse()
        return title, content
    except Exception as e:
        print(f"Error processing {url}: {str(e)[:100]}")
        return None, None
async def parse_articles(urls):
    async with aiohttp.ClientSession() as session:
        return await asyncio.gather(*[fetch_and_extract(session, url) for url in urls])

async def process_batch(model_type, texts):
    results = []
    for i in range(0, len(texts), BATCH_SIZES[model_type]):
        torch.cuda.empty_cache()
        batch = texts[i:i+BATCH_SIZES[model_type]]
        
        if model_type == "classify":
            inputs = classify_tokenizer(
                batch, 
                padding=True, 
                truncation=True, 
                max_length=MODEL_CONFIG["classify"]["max_length"],
                return_tensors="pt"
            ).to(device)
            with torch.no_grad():
                outputs = classify_model(**inputs).logits
            results.extend(outputs.argmax(dim=1).cpu().tolist())
        
        elif model_type == "sentiment":
            inputs = sentiment_tokenizer(
                batch,
                padding=True,
                truncation=True,
                max_length=MODEL_CONFIG["sentiment"]["max_length"],
                return_tensors="pt"
            ).to(device)
            with torch.no_grad():
                outputs = sentiment_model(**inputs).logits
            results.extend((outputs.softmax(dim=-1).argmax(dim=-1) + 1).cpu().tolist())
        
        elif model_type == "summarize":
            inputs = summarize_tokenizer(
                batch,
                padding=True,
                truncation=True,
                max_length=MODEL_CONFIG["summarize"]["max_length"],
                return_tensors="pt"
            ).to(device)
            with torch.no_grad():
                outputs = summarize_model.generate(
                    inputs.input_ids,
                    max_length=MODEL_CONFIG["summarize"]["gen_max_length"],
                    min_length=50,
                    num_beams=2,
                    early_stopping=True
                )
            results.extend(summarize_tokenizer.batch_decode(outputs, skip_special_tokens=True))
        
        del inputs, outputs
        torch.cuda.empty_cache()
    
    return results

async def create_table():
    try:
        conn = await aiomysql.connect(**DB_CONFIG)
        print("Successfully connected to MySQL database")
        async with conn.cursor() as cursor:
            await cursor.execute("""
                CREATE TABLE IF NOT EXISTS news_articles (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    title VARCHAR(255),
                    url VARCHAR(255) UNIQUE,
                    summary TEXT,
                    classification VARCHAR(100),
                    sentiment VARCHAR(50),
                    source_name VARCHAR(50),
                    priority INT
                )
            """)
            print("Table 'news_articles' created/verified successfully")
            await conn.commit()
    except Exception as e:
        print(f"Database error: {e}")
    finally:
        if conn:
            await conn.ensure_closed()

async def store_article(data):
    try:
        conn = await aiomysql.connect(**DB_CONFIG)
        async with conn.cursor() as cursor:
            await cursor.execute("""
                INSERT INTO news_articles 
                (title, url, summary, classification, sentiment, source_name, priority)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE 
                    title=VALUES(title),
                    summary=VALUES(summary),
                    classification=VALUES(classification),
                    sentiment=VALUES(sentiment),
                    priority=VALUES(priority)
            """, data)
            await conn.commit()
            print(f"Stored article: {data[0][:50]}...")  # Truncate long titles
    except Exception as e:
        print(f"Error storing article: {e}")
    finally:
        if conn:
            await conn.ensure_closed()

def get_source_and_priority(url):
    if "bbc.com" in url: return ("BBC News", 2)
    if "theguardian.com" in url: return ("The Guardian", 3)
    if "timesofindia" in url: return ("Times of India", 1)
    return ("Other", 4)

async def main():
    await create_table()
    
    urls = [
        "https://timesofindia.indiatimes.com/india/assam-reports-1st-guillain-barre-syndrome-death-maharashtra-tally-climbs-to-5/articleshow/117841253.cms",
        "https://timesofindia.indiatimes.com/city/raipur/8-maoists-killed-in-clash-with-security-forces-in-bijapur/articleshow/117836450.cms",
        "https://timesofindia.indiatimes.com/science/with-big-ticket-space-missions-lined-up-isro-gets-a-budget-boost/articleshow/117837166.cms",
        "https://www.bbc.com/sport/formula1/articles/c4g7j0j8357o",
        "https://www.bbc.com/news/articles/cg5ydgeqrvqo",
        "https://www.bbc.com/sport/formula1/articles/cm21e8pj24lo",
        "https://www.bbc.com/news/articles/c78x4ngjyy9o",
        "https://www.bbc.com/sport/formula1/articles/c4g7j0j8357o",
        "https://www.bbc.com/news/articles/c9vm1m8wpr9o",
        "https://www.theguardian.com/world/2022/mar/17/ukraine-war-russia-putin-peace-talks",
        "https://www.theguardian.com/world/live/2025/feb/01/middle-east-crisis-live-hamas-hostages-release-israel-gaza",
        "https://www.theguardian.com/world/2025/feb/01/no-one-but-jews-lost-their-apartments-how-homes-taken-by-nazis-in-wartime-paris-were-never-given-back",
        "https://www.theguardian.com/world/2025/jan/31/woman-freed-by-hamas-tells-starmer-she-was-held-in-premises-owned-by-unrwa-her-mother-says",
        "https://www.theguardian.com/world/2025/jan/31/hunger-fear-goma-m23-takeover-democratic-republic-of-the-congo",
        "https://www.theguardian.com/world/2025/jan/31/german-parliament-rejects-immigration-bill-backed-far-right-afd",
        "https://www.theguardian.com/world/live/2025/jan/31/middle-east-crisis-live-israeli-hamas-gaza-lebanon-hebollah-latest-news-hostages-ceasefire",
        "https://www.theguardian.com/world/2025/jan/31/beethoven-marie-curie-compete-birds-appear-new-euro-notes",
        "https://www.theguardian.com/world/2025/jan/31/anger-romania-theft-dacian-artefacts-netherlands-drents-museum"
    ]

    extracted = await parse_articles(urls)
    valid_data = [(url, title, content) for url, (title, content) in zip(urls, extracted) if content]
    
    if not valid_data:
        print("No valid content extracted")
        return

    urls, titles, contents = zip(*valid_data)

    # Process batches sequentially to manage memory
    classifications = await process_batch("classify", contents)
    sentiments = await process_batch("sentiment", contents)
    summaries = await process_batch("summarize", contents)

    # Convert numerical outputs to labels
    sentiment_labels = ["Very Negative", "Negative", "Neutral", "Positive", "Very Positive"]
    sentiments = [sentiment_labels[s-1] for s in sentiments]
    classifications = [classify_model.config.id2label.get(c, "Unknown") for c in classifications]

    # Store results
    storage_tasks = []
    for data in zip(titles, urls, summaries, classifications, sentiments):
        title, url, summary, category, sentiment = data
        source, priority = get_source_and_priority(url)
        storage_tasks.append(store_article((
            title[:255], 
            url, 
            summary[:2000],
            category[:100], 
            sentiment[:50],
            source[:50], 
            priority
        )))
    await asyncio.gather(*storage_tasks)
    print(f"Processed {len(urls)} articles successfully")

if __name__ == "__main__":
    asyncio.run(main())