"""Teste da busca de cartas"""
from data.google_sheets_client import GoogleSheetsClient

# Criar cliente
client = GoogleSheetsClient()

# Carregar todas as cartas
print("Carregando cartas...")
all_cards = client.get_all_cards()
print(f"Total de cartas: {len(all_cards)}")

# Testar busca simples
print("\n--- Teste 1: Primeiras 5 cartas ---")
for card in all_cards[:5]:
    print(f"- {card.name} ({card.cost} custo, {card.card_type}, Facções: {card.factions})")

# Testar busca por tipo
print("\n--- Teste 2: Units de custo baixo ---")
units = [c for c in all_cards if c.card_type == "Unit" and c.cost <= 2]
print(f"Units com custo <= 2: {len(units)}")
for card in units[:5]:
    print(f"- {card.name} ({card.cost} custo, {card.attack}/{card.health})")

# Testar busca por facção
print("\n--- Teste 3: Cartas Fire ---")
fire_cards = [c for c in all_cards if "FIRE" in c.factions]
print(f"Cartas Fire: {len(fire_cards)}")
for card in fire_cards[:5]:
    print(f"- {card.name} ({card.cost} custo, {card.card_type})")