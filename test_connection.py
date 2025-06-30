import gspread
from google.oauth2.service_account import Credentials
import os
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv()

def test_google_sheets_connection():
    try:
        # Configurar credenciais
        creds = Credentials.from_service_account_file(
            os.getenv('GOOGLE_SHEETS_CREDENTIALS_PATH'),
            scopes=[
                'https://www.googleapis.com/auth/spreadsheets',
                'https://www.googleapis.com/auth/drive'
            ]
        )
        
        # Conectar ao Google Sheets
        client = gspread.authorize(creds)
        
        # Abrir a planilha
        sheet = client.open_by_key(os.getenv('GOOGLE_SHEETS_ID'))
        
        # Listar todas as abas
        worksheets = sheet.worksheets()
        print(f"✅ Conexão bem sucedida!")
        print(f"📊 Planilha: {sheet.title}")
        print(f"📑 Abas encontradas: {[ws.title for ws in worksheets]}")
        
        # Tentar ler a primeira linha da primeira aba
        first_sheet = sheet.get_worksheet(0)
        headers = first_sheet.row_values(1)
        print(f"📋 Colunas na primeira aba: {headers[:5]}...")  # Primeiras 5 colunas
        
        return True
        
    except Exception as e:
        print(f"❌ Erro na conexão: {str(e)}")
        return False

if __name__ == "__main__":
    test_google_sheets_connection()