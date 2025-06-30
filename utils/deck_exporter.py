"""Exportador de decks para o formato do Eternal"""
from typing import List, Dict, Optional, Tuple
from data.google_sheets_client import GoogleSheetsClient
import re

class DeckExporter:
    def __init__(self):
        self.client = GoogleSheetsClient()
        self._card_info_cache = {}
        self._all_cards = None
    
    def _load_cards_once(self):
        """Carrega todas as cartas apenas uma vez"""
        if self._all_cards is None:
            self._all_cards = self.client.get_all_cards()
    
    def get_card_info(self, card_name: str) -> Dict[str, str]:
        """Busca informações de set e ID da carta"""
        if card_name in self._card_info_cache:
            return self._card_info_cache[card_name]
        
        # Garantir que as cartas foram carregadas
        self._load_cards_once()
        
        # Buscar carta (case insensitive)
        card_name_lower = card_name.lower().strip()
        
        for card in self._all_cards:
            if card.name.lower() == card_name_lower:
                info = {
                    'set': f"Set{getattr(card, 'set_number', '1')}",
                    'number': getattr(card, 'eternal_id', '1')
                }
                
                self._card_info_cache[card_name] = info
                return info
        
        # Se não encontrar, retornar valores padrão
        default_info = {'set': 'Set1', 'number': '1'}
        self._card_info_cache[card_name] = default_info
        return default_info
    
    def export_deck_text(self, deck_text: str, format_type: str = "Throne") -> str:
        """Converte deck em texto para o formato do jogo"""
        lines = deck_text.strip().split('\n')
        main_deck = []
        market = []
        in_market = False
        
        for line in lines:
            # Detectar seção de mercado
            if 'MARKET' in line.upper():
                in_market = True
                continue
            
            # Pular linhas vazias e metadata
            if not line.strip() or self._is_metadata_line(line):
                continue
            
            # Parsear linha
            parsed = self.parse_deck_line(line)
            if parsed:
                qty, card_name = parsed
                card_info = self.get_card_info(card_name)
                formatted_line = f"{qty} {card_name} ({card_info['set']} #{card_info['number']})"
                
                if in_market:
                    market.append(formatted_line)
                else:
                    main_deck.append(formatted_line)
        
        # Montar deck final
        output = f"FORMAT:{format_type}\n"
        output += '\n'.join(main_deck)
        
        if market:
            output += "\n--------------MARKET---------------\n"
            output += '\n'.join(market)
        
        return output
    
    def _is_metadata_line(self, line: str) -> bool:
        """Verifica se é linha de metadata"""
        metadata_indicators = ['===', '---', 'UNITS', 'SPELLS', 'POWERS', 
                             'WEAPONS', 'RELICS', ':', 'DECK', 'STRATEGY']
        return any(indicator in line.upper() for indicator in metadata_indicators)
    
    def parse_deck_line(self, line: str) -> Optional[Tuple[int, str]]:
        """Parser para linha de deck - agora suporta formato com pipes"""
        line = line.strip()
        if not line:
            return None
        
        # Se tem pipe, é o novo formato - pegar apenas a primeira parte
        if '|' in line:
            line = line.split('|')[0].strip()
        
        # Remover informações de set se já existirem (para formato antigo)
        line = re.sub(r'\([^)]*\)', '', line).strip()
        
        # Tentar diferentes padrões
        patterns = [
            r'^(\d+)x?\s+(.+)$',     # "4 Card" ou "4x Card"
            r'^(.+?)\s*x\s*(\d+)$'   # "Card x4"
        ]
        
        for pattern in patterns:
            match = re.match(pattern, line)
            if match:
                if pattern == patterns[0]:
                    return int(match.group(1)), match.group(2).strip()
                else:
                    return int(match.group(2)), match.group(1).strip()
        
        return None