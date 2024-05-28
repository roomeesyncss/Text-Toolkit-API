from fastapi import FastAPI, File, UploadFile, HTTPException, Request, Depends
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from bs4 import BeautifulSoup
from pydantic import BaseModel, Field, validator
from collections import Counter
import re
import string
import secrets
import requests
from langdetect import detect, LangDetectException
from translate import Translator

app = FastAPI(
    title="Text toolkit  API",
    description="An API for various text manipulation tasks including language detection,password generation, and more.",
    version="1.0.1",
)

# Middleware for CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class LanguageDetectionRequest(BaseModel):
    text: str

    @validator('text')
    def text_must_not_be_empty(cls, value):
        if not value.strip():
            raise ValueError("Text must not be empty.")
        return value


class LanguageDetectionResponse(BaseModel):
    language: str


class PasswordGeneratorRequest(BaseModel):
    length: int = Field(default=12, ge=8, le=128, description="Password length should be between 8 and 128 characters.")


class PasswordGeneratorResponse(BaseModel):
    generated_password: str


class AcronymRequest(BaseModel):
    words: list[str]

    @validator('words')
    def words_must_not_be_empty(cls, value):
        if not value:
            raise ValueError("At least one word is required for acronym generation.")
        return value


class AcronymResponse(BaseModel):
    acronym: str


class RemoveLineBreaksRequest(BaseModel):
    text: str = Field(..., title="Text Content", description="Enter text with line breaks to remove.")


class RemoveLineBreaksResponse(BaseModel):
    text_without_line_breaks: str


class CharacterCounterRequest(BaseModel):
    text: str = Field(..., title="Text Content", description="Enter text to count characters.")


class CharacterCounterResponse(BaseModel):
    character_count: dict


class HTMLLinkExtractorRequest(BaseModel):
    html: str = Field(..., title="HTML Content", description="Enter HTML content to extract links.")


class HTMLLinkExtractorResponse(BaseModel):
    links: list


class WordCountRequest(BaseModel):
    text: str = Field(..., title="Text Content", description="Text content to count word occurrences.")


class WordCountResponse(BaseModel):
    word_frequencies: dict


class RemoveTagsRequest(BaseModel):
    html: str = Field(..., title="HTML Content", description="HTML content to remove tags.")


class RemoveTagsResponse(BaseModel):
    cleaned_text: str


class ExtractEmailsUrlsRequest(BaseModel):
    text: str = Field(..., title="Text Content", description="Text content to extract emails and URLs.")


class ExtractEmailsUrlsResponse(BaseModel):
    emails: list
    urls: list


class RandomQuoteResponse(BaseModel):
    quote: str
    author: str


# Utility Functions
def remove_tags(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    clean_text = soup.get_text(separator=' ')
    return clean_text


def extract_email_addresses(text):
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    emails = re.findall(email_pattern, text)
    return emails


def extract_html_links(input_html):
    soup = BeautifulSoup(input_html, 'html.parser')
    links = [a.get('href') for a in soup.find_all('a') if a.get('href')]
    return links


def extract_urls(text):
    url_ptrn = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
    urls = re.findall(url_ptrn, text)
    return urls


def process_text(input_text):
    cleaned_text = remove_tags(input_text)
    emails = extract_email_addresses(cleaned_text)
    urls = extract_urls(cleaned_text)
    return {"emails": emails, "urls": urls}


def count_word_occurrences(text):
    words = re.findall(r'\b\w+\b', text)
    word_frequencies = Counter(words)
    return word_frequencies


def remove_line_breaks(text):
    return text.replace('\n', '').replace('\r', '')


def count_characters(input_text):
    return dict(Counter(input_text))


# Dependency for Translator
def get_translator(target_language: str):
    return Translator(to_lang=target_language)


# Endpoints
@app.post("/text-manipulation/remove-tags/json", response_model=RemoveTagsResponse, tags=["Remove Tags"])
async def remove_tags_json_api(data: RemoveTagsRequest):
    try:
        input_html = data.html
        cleaned_text = remove_tags(input_html)
        return {"cleaned_text": cleaned_text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/text-manipulation/remove-tags/file", response_model=RemoveTagsResponse, tags=["Remove Tags"])
async def remove_tags_file_api(html_file: UploadFile = File(...)):
    try:
        input_html = await html_file.read()
        cleaned_text = remove_tags(input_html.decode())
        return {"cleaned_text": cleaned_text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/text-manipulation/extract-emails-urls", response_model=ExtractEmailsUrlsResponse, tags=["Emails and URLs"])
async def extract_emails_urls_api(data: ExtractEmailsUrlsRequest):
    try:
        input_text = data.text
        result = process_text(input_text)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/text-manipulation/word-count", response_model=WordCountResponse, tags=["Word Count"])
async def word_count_api(data: WordCountRequest):
    try:
        input_text = data.text
        word_frequencies = count_word_occurrences(input_text)
        return {"word_frequencies": word_frequencies}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/text-manipulation/remove-line-breaks", response_model=RemoveLineBreaksResponse, tags=["Remove Line Breaks"])
async def remove_line_breaks_api(data: RemoveLineBreaksRequest):
    try:
        input_text = data.text
        text_without_line_breaks = remove_line_breaks(input_text)
        return {"text_without_line_breaks": text_without_line_breaks}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/text-manipulation/character-counter", response_model=CharacterCounterResponse, tags=["Character Counter"])
async def character_counter_api(data: CharacterCounterRequest):
    try:
        input_text = data.text
        character_count = count_characters(input_text)
        return {"character_count": character_count}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/html-manipulation/html-link-extractor", response_model=HTMLLinkExtractorResponse,
          tags=["HTML Link Extractor"])
async def html_link_extractor_api(data: HTMLLinkExtractorRequest):
    try:
        input_html = data.html
        links = extract_html_links(input_html)
        return {"links": links}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/password-generator", response_model=PasswordGeneratorResponse, tags=["Password Generator"])
async def generate_password(request: PasswordGeneratorRequest):
    try:
        password_length = request.length
        uppercase_chars = string.ascii_uppercase
        lowercase_chars = string.ascii_lowercase
        digit_chars = string.digits
        special_chars = string.punctuation
        required_chars = (
                secrets.choice(uppercase_chars) +
                secrets.choice(lowercase_chars) +
                secrets.choice(digit_chars) +
                secrets.choice(special_chars)
        )
        remaining_length = max(0, password_length - len(required_chars))
        all_chars = uppercase_chars + lowercase_chars + digit_chars + special_chars
        remaining_chars = ''.join(secrets.choice(all_chars) for _ in range(remaining_length))
        password = list(required_chars + remaining_chars)
        secrets.SystemRandom().shuffle(password)
        return {"generated_password": ''.join(password)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/random-quote", response_model=RandomQuoteResponse, tags=["Random Quote Generator"])
async def get_random_quote():
    try:
        response = requests.get("https://api.quotable.io/random")
        if response.status_code == 200:
            data = response.json()
            return {"quote": data["content"], "author": data["author"]}
        else:
            raise HTTPException(status_code=response.status_code, detail="Failed to fetch quote")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/text-manipulation/detect-language", response_model=LanguageDetectionResponse, tags=["Language Detection"])
async def detect_language(request: LanguageDetectionRequest):
    try:
        lang = detect(request.text)
        return {"language": lang}
    except LangDetectException:
        raise HTTPException(status_code=400, detail="Could not detect language of the input text.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/acronym-generator", response_model=AcronymResponse, tags=["Acronym Generator"])
async def generate_acronym(request: AcronymRequest):
    try:
        words = request.words
        acronym = "".join(word[0].upper() for word in words)
        return {"acronym": acronym}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
