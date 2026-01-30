import re
from bs4 import BeautifulSoup

def preprocess_text(text: str) -> str:
    if not text:
        return ""
    # remove HTML tags
    text = BeautifulSoup(text, "html.parser").get_text()
    # lowercase
    text = text.lower()
    # remove URLs
    text = re.sub(r"http\S+|www\S+", "", text)
    # remove special characters/numbers
    text = re.sub(r"[^a-z\s]", " ", text)
    # remove extra spaces
    text = re.sub(r"\s+", " ", text).strip()
    return text
