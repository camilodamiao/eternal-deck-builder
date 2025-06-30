"""Modelos de dados para cartas e decks"""
from typing import List, Optional, Dict
from pydantic import BaseModel, Field, validator

class Card(BaseModel):
    """Modelo simplificado de uma carta do Eternal"""
    name: str
    cost: int = 0
    influence: Dict[str, int] = Field(default_factory=dict)  # Ex: {"FIRE": 1, "TIME": 2}
    card_type: str  # Unit, Spell, Power, etc.
    factions: List[str] = Field(default_factory=list)  # Ex: ["FIRE", "TIME"]
    attack: Optional[int] = None
    health: Optional[int] = None
    text: str = ""
    rarity: str = "Common"
    deck_buildable: bool = True
    image_url: Optional[str] = None  # NOVO CAMPO
    set_number: Optional[str] = None  # NOVO
    eternal_id: Optional[str] = None  # NOVO
    
    @property
    def is_unit(self) -> bool:
        return self.card_type == "Unit"
    
    @property
    def is_power(self) -> bool:
        return self.card_type == "Power"
    
    @property
    def is_sigil(self) -> bool:
        """Verifica se é um Sigil básico"""
        return self.card_type == "Power" and "Sigil" in self.name

class DeckCard(BaseModel):
    """Carta em um deck com quantidade"""
    card: Card
    quantity: int = Field(ge=1)  # Mínimo 1 cópia
    
    @validator('quantity')
    def validate_quantity(cls, v, values):
        """Valida quantidade - Sigils podem ter mais de 4 cópias"""
        if 'card' in values:
            card = values['card']
            if not card.is_sigil and v > 4:
                raise ValueError(f"Cartas não-Sigil podem ter no máximo 4 cópias (tentou {v})")
        return v

class Deck(BaseModel):
    """Modelo simplificado de um deck"""
    name: str = "Novo Deck"
    main_deck: List[DeckCard] = Field(default_factory=list)
    market: List[DeckCard] = Field(default_factory=list)
    
    @property
    def total_cards(self) -> int:
        return sum(dc.quantity for dc in self.main_deck)
    
    @property
    def power_count(self) -> int:
        return sum(dc.quantity for dc in self.main_deck if dc.card.is_power)
    
    @property
    def average_cost(self) -> float:
        """Calcula o custo médio das cartas não-power"""
        total_cost = 0
        total_non_power = 0
        
        for dc in self.main_deck:
            if not dc.card.is_power:
                total_cost += dc.card.cost * dc.quantity
                total_non_power += dc.quantity
        
        return total_cost / total_non_power if total_non_power > 0 else 0