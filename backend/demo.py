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