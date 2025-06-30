"""Teste dos modelos de dados"""
from data.models import Card, DeckCard, Deck

def test_models():
    print("🧪 Testando modelos de dados...\n")
    
    # Criar algumas cartas de exemplo
    torch = Card(
        name="Torch",
        cost=1,
        influence={"FIRE": 1},
        card_type="Spell",
        factions=["FIRE"],
        text="Deal 3 damage.",
        rarity="Common"
    )
    
    fire_sigil = Card(
        name="Fire Sigil",
        cost=0,
        card_type="Power",
        factions=["FIRE"],
        text="Gain 1 Fire influence.",
        rarity="Common"
    )
    
    oni_ronin = Card(
        name="Oni Ronin",
        cost=1,
        influence={"FIRE": 1},
        card_type="Unit",
        factions=["FIRE"],
        attack=2,
        health=1,
        text="Warcry",
        rarity="Common"
    )
    
    # Mostrar informações das cartas
    print("📍 Cartas criadas:")
    for card in [torch, fire_sigil, oni_ronin]:
        print(f"  - {card.name} ({card.cost} custo, {card.card_type})")
        if card.is_unit:
            print(f"    {card.attack}/{card.health} - {card.text}")
    
    # Criar um deck de exemplo
    deck = Deck(
        name="Fire Aggro Teste",
        main_deck=[
            DeckCard(card=torch, quantity=4),
            DeckCard(card=oni_ronin, quantity=4),
            DeckCard(card=fire_sigil, quantity=25)
        ]
    )
    
    # Mostrar informações do deck
    print(f"\n📚 Deck: {deck.name}")
    print(f"  - Total de cartas: {deck.total_cards}")
    print(f"  - Cartas de poder: {deck.power_count}")
    print(f"  - Proporção de poder: {deck.power_count/deck.total_cards*100:.1f}%")
    
    # Verificar se os modelos funcionam corretamente
    print("\n✅ Teste dos modelos concluído com sucesso!")
    
    return True

if __name__ == "__main__":
    test_models()