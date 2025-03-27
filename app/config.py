import os
from dotenv import load_dotenv
from typing import List, Optional

load_dotenv()

class Settings:
    # MongoDB Configuration
    MONGO_URI = os.getenv('MONGO_URI', 'mongodb://mongodb:27017')
    DATABASE_NAME = os.getenv('DATABASE_NAME', 'chat_summarization_db')

    # Gemini Configuration
    GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
    
    # Application Settings
    DEBUG = os.getenv('DEBUG', 'False') == 'True'
    
    # Pagination & Limits
    DEFAULT_PAGE_SIZE = 10
    MAX_PAGE_SIZE = 100
    MAX_SUMMARY_MESSAGES = 500  # Maximum messages to summarize

settings = Settings()