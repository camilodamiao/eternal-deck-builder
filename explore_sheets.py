"""Explorar estrutura da planilha"""
from data.google_sheets_client import GoogleSheetsClient
import json

def explore_sheets():
    print("🔍 Explorando estrutura da planilha...\n")
    
    # Conectar
    client = GoogleSheetsClient()
    
    # Buscar uma carta
    sample_cards = client.get_sample_cards(limit=1)
    
    if sample_cards:
        first_card = sample_cards[0]
        
        print("📋 Colunas encontradas:")
        print("-" * 50)
        
        # Listar todas as colunas e valores
        for i, (key, value) in enumerate(first_card.items()):
            # Truncar valores muito longos
            value_str = str(value)[:100] + "..." if len(str(value)) > 100 else str(value)
            print(f"{i+1:3d}. {key}: {value_str}")
        
        print("\n" + "-" * 50)
        print(f"Total de colunas: {len(first_card)}")
        
        # Procurar por colunas que possam ter imagens
        print("\n🖼️ Possíveis colunas de imagem:")
        image_keywords = ['image', 'img', 'url', 'link', 'picture', 'card', 'art']
        
        for key in first_card.keys():
            if any(keyword in key.lower() for keyword in image_keywords):
                print(f"  - {key}: {first_card[key][:50]}...")
    
    else:
        print("❌ Nenhuma carta encontrada")

if __name__ == "__main__":
    explore_sheets()