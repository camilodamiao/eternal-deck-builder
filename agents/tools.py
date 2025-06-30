"""Ferramentas para o agente de deck building"""
from typing import List, Dict, Optional
from langchain.tools import tool
from data.google_sheets_client import GoogleSheetsClient
from data.models import Card, Deck, DeckCard

# Cache global de cartas
_cards_cache = None

def get_all_cards_cached():
    """Carregar cartas com cache"""
    global _cards_cache
    if _cards_cache is None:
        client = GoogleSheetsClient()
        _cards_cache = client.get_all_cards()
        print(f"✅ {len(_cards_cache)} cartas carregadas em cache")
    return _cards_cache

@tool
def search_cards(
    query: Optional[str] = None,
    faction: Optional[str] = None,
    max_cost: Optional[int] = None,
    card_type: Optional[str] = None,
    text_contains: Optional[str] = None
) -> str:
    """
    Busca cartas no banco de dados.
    
    Args:
        query: Nome parcial da carta
        faction: Facção (Fire, Time, Justice, Primal, Shadow)
        max_cost: Custo máximo
        card_type: Tipo (Unit, Spell, Power, Weapon, Relic)
        text_contains: Texto que a carta deve conter
    
    Retorna lista de cartas encontradas.
    """
    # Carregar cartas
    all_cards = get_all_cards_cached()
    results = all_cards
    
    # Debug
    print(f"[DEBUG] Busca iniciada - Total cartas: {len(results)}")
    print(f"[DEBUG] Parâmetros: query={query}, faction={faction}, max_cost={max_cost}, card_type={card_type}")
    
    # Aplicar filtros
    if query:
        query_lower = query.lower()
        results = [c for c in results if query_lower in c.name.lower()]
        print(f"[DEBUG] Após filtro nome: {len(results)} cartas")
    
    if faction:
        # Normalizar nome da facção
        faction_upper = faction.upper()
        results = [c for c in results if faction_upper in c.factions]
        print(f"[DEBUG] Após filtro facção {faction}: {len(results)} cartas")
    
    if card_type:
        # Normalizar tipo
        type_normalized = card_type.capitalize()
        results = [c for c in results if c.card_type == type_normalized]
        print(f"[DEBUG] Após filtro tipo {type_normalized}: {len(results)} cartas")
    
    if max_cost is not None:
        results = [c for c in results if c.cost <= max_cost]
        print(f"[DEBUG] Após filtro custo <= {max_cost}: {len(results)} cartas")
    
    if text_contains:
        text_lower = text_contains.lower()
        results = [c for c in results if text_lower in c.text.lower()]
        print(f"[DEBUG] Após filtro texto: {len(results)} cartas")
    
    # Formatar resposta
    if not results:
        return "Nenhuma carta encontrada com esses critérios."
    
    # Limitar resultados
    output = f"Encontradas {len(results)} cartas:\n\n"
    
    for card in results[:30]:  # Mostrar até 30 cartas
        output += f"{card.name} - {card.cost} custo"
        
        if card.card_type == "Unit":
            output += f" - {card.attack}/{card.health} Unit"
        else:
            output += f" - {card.card_type}"
        
        if card.factions:
            output += f" - {'/'.join(card.factions)}"
        
        if card.text:
            output += f" - {card.text[:40]}..."
        
        output += "\n"
    
    if len(results) > 30:
        output += f"\n... e mais {len(results) - 30} cartas."
    
    return output

@tool 
def get_basic_aggro_package() -> str:
    """Retorna um pacote básico de cartas para deck aggro."""
    
    all_cards = get_all_cards_cached()
    
    # Buscar cartas aggro básicas
    aggro_cards = []
    
    # Units de 1 custo
    one_drops = [c for c in all_cards if c.card_type == "Unit" and c.cost == 1][:5]
    
    # Units de 2 custo
    two_drops = [c for c in all_cards if c.card_type == "Unit" and c.cost == 2][:5]
    
    # Spells de dano direto
    burn_spells = [c for c in all_cards if c.card_type == "Spell" and c.cost <= 3 
                   and any(word in c.text.lower() for word in ["damage", "deal"])][:5]
    
    output = "PACOTE AGGRO BÁSICO:\n\n"
    
    output += "Units de 1 custo:\n"
    for card in one_drops:
        output += f"- {card.name} ({card.attack}/{card.health})\n"
    
    output += "\nUnits de 2 custo:\n"
    for card in two_drops:
        output += f"- {card.name} ({card.attack}/{card.health})\n"
    
    output += "\nSpells de dano:\n"
    for card in burn_spells:
        output += f"- {card.name} ({card.cost} custo)\n"
    
    return output

@tool
def validate_deck_rules(deck_list: str) -> str:
    """Valida se um deck segue as regras do Eternal."""
    lines = deck_list.strip().split('\n')
    
    total_cards = 0
    power_cards = 0
    card_counts = {}
    
    for line in lines:
        try:
            # Parsear formato "4 Card Name"
            parts = line.strip().split(' ', 1)
            if len(parts) == 2 and parts[0].isdigit():
                qty = int(parts[0])
                name = parts[1]
                total_cards += qty
                
                # Verificar se é power
                if 'Sigil' in name or 'Power' in name:
                    power_cards += qty
                
                # Contar cópias
                card_counts[name] = card_counts.get(name, 0) + qty
        except:
            continue
    
    # Validar regras
    errors = []
    
    if total_cards < 75:
        errors.append(f"Deck tem apenas {total_cards} cartas (mínimo 75)")
    
    power_ratio = power_cards / total_cards if total_cards > 0 else 0
    if power_ratio < 0.33:
        errors.append(f"Apenas {power_ratio*100:.1f}% de power cards (mínimo 33%)")
    
    for card, count in card_counts.items():
        if count > 4 and 'Sigil' not in card:
            errors.append(f"{card} tem {count} cópias (máximo 4)")
    
    if errors:
        return "DECK INVÁLIDO:\n" + "\n".join(errors)
    else:
        return f"DECK VÁLIDO: {total_cards} cartas, {power_ratio*100:.1f}% power"

@tool
def get_faction_powers(faction: str, quantity: int = 25) -> str:
    """Retorna power cards para uma facção específica."""
    
    all_cards = get_all_cards_cached()
    
    # Normalizar facção
    faction_upper = faction.upper()
    
    # Buscar sigils
    sigil_name = f"{faction.capitalize()} Sigil"
    sigils = [c for c in all_cards if sigil_name in c.name and c.card_type == "Power"]
    
    if not sigils:
        return f"Não encontrei Sigils para {faction}"
    
    sigil = sigils[0]
    
    output = f"POWER BASE PARA {faction_upper}:\n"
    output += f"{quantity} {sigil.name}\n"
    
    # Buscar outros powers da facção
    other_powers = [c for c in all_cards 
                    if c.card_type == "Power" 
                    and faction_upper in c.factions 
                    and "Sigil" not in c.name][:5]
    
    if other_powers:
        output += "\nOutros powers disponíveis:\n"
        for power in other_powers:
            output += f"- {power.name}\n"
    
    return output