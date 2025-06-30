"""Teste do cliente Google Sheets"""
from data.google_sheets_client import GoogleSheetsClient
import json

def test_sheets_client():
    print("🧪 Testando cliente Google Sheets...\n")
    
    # Criar cliente
    client = GoogleSheetsClient()
    
    # Buscar algumas cartas
    print("\n📊 Buscando cartas de exemplo...")
    sample_cards = client.get_sample_cards(limit=5)
    
    if sample_cards:
        print(f"\n✅ {len(sample_cards)} cartas encontradas!")
        
        # Mostrar primeira carta raw
        print("\n📄 Primeira carta (dados brutos):")
        first_card = sample_cards[0]
        # Mostrar apenas alguns campos para não poluir
        for key in list(first_card.keys())[:10]:
            print(f"  {key}: {first_card[key]}")
        
        # Tentar parsear
        print("\n🔄 Tentando converter para modelo Card...")
        parsed_cards = []
        for card_data in sample_cards:
            parsed = client.parse_card(card_data)
            if parsed:
                parsed_cards.append(parsed)
                print(f"  ✅ {parsed.name} ({parsed.cost} custo, {parsed.card_type})")
        
        print(f"\n📊 {len(parsed_cards)} de {len(sample_cards)} cartas parseadas com sucesso!")
        
    else:
        print("❌ Nenhuma carta encontrada")
    
    return True

if __name__ == "__main__":
    test_sheets_client()