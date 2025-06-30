"""Configurações gerais da aplicação"""
import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    # API Keys
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
    OPENAI_MODEL = "gpt-4-turbo-preview"  # ou "gpt-3.5-turbo" para testes
    
    # Google Sheets
    GOOGLE_SHEETS_CREDENTIALS = os.getenv('GOOGLE_SHEETS_CREDENTIALS_PATH')
    GOOGLE_SHEETS_ID = os.getenv('GOOGLE_SHEETS_ID')
    
    # App Settings
    APP_NAME = "Eternal Deck Builder AI"
    APP_VERSION = "1.0.0"
    
    # LangChain Settings
    TEMPERATURE = 0.3
    MAX_TOKENS = 2000

settings = Settings()