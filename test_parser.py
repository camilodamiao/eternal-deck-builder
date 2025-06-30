"""Teste do parser flexível"""
from core.deck_validator import DeckValidator

# Criar validador
validator = DeckValidator()

# Testar diferentes formatos
test_cases = [
    "4 Torch",
    "4x Torch",
    "Torch x4",
    "4 Seek Power (Set1 #408)",
    "3x Sandstorm Titan (Set1 #99)",
    "Harsh Rule x2",
    "1 Svetya, Merciful Orene",
    "25 Fire Sigil",
    "=== DECK ===",  # Deve ser ignorado
    "MARKET:",       # Deve ser ignorado
    "UNITS (28):",   # Deve ser ignorado
    "",              # Linha vazia
]

print("🧪 Testando parser flexível...\n")

for test in test_cases:
    result = validator.parse_deck_line(test)
    if result:
        qty, name = result
        print(f"✅ '{test}' → {qty}x {name}")
    else:
        print(f"⏭️  '{test}' → Ignorado")

# Testar deck completo
print("\n🎴 Testando deck completo...\n")

sample_deck = """
=== DECK FIRE AGGRO (75 cartas) ===

UNITS (32):
4x Oni Ronin
4 Torch Bearer
Pyroknight x4
3x Champion of Fury
3 Vadius, Clan Father (Set5 #123)
4 Rakano Outlaw
4x Crimson Firemaw
4 Varret, Hero-in-Training

SPELLS (12):
4 Torch
4x Char
Obliterate x4

POWERS (31):
25 Fire Sigil
3x Granite Waystone
3 Diplomatic Seal
"""

is_valid, errors, stats = validator.validate_text_deck(sample_deck)

print(f"Válido: {is_valid}")
print(f"Total de cartas: {stats['total_cards']}")
print(f"Cartas de poder: {stats['power_cards']}")
print(f"Linhas parseadas: {stats['parsed_lines']}")
print(f"Linhas de metadata ignoradas: {stats['skipped_metadata']}")

if stats['card_counts']:
    print(f"\nPrimeiras 5 cartas:")
    for i, (card, qty) in enumerate(list(stats['card_counts'].items())[:5]):
        print(f"  - {qty}x {card}")

if errors:
    print("\nErros encontrados:")
    for error in errors:
        print(f"  ❌ {error}")
else:
    print("\n✅ Deck válido!")