"""Teste do exportador de deck"""
from utils.deck_exporter import DeckExporter

sample_deck = """
=== DECK FIRE AGGRO ===

4 Oni Ronin
4x Torch
3 Champion of Fury
25 Fire Sigil

MARKET:
1 Bore
1 Mindfire
"""

print("🧪 Testando exportação...\n")

exporter = DeckExporter()
exported = exporter.export_deck_text(sample_deck)

print("📤 Deck exportado:")
print("-" * 40)
print(exported)
print("-" * 40)