"""Validador de decks com parser flexível"""
import re
from typing import List, Tuple, Dict, Optional
from config.constants import DECK_RULES

class DeckValidator:
    def __init__(self):
        self.rules = DECK_RULES
        # Palavras que indicam linhas de metadata (não são cartas)
        self.metadata_keywords = [
            'DECK', 'MARKET', 'STRATEGY', 'ESTRATÉGIA', 'COMO JOGAR', 
            'UNITS', 'SPELLS', 'POWERS', 'WEAPONS', 'RELICS', 'MAIN',
            'SIDEBOARD', 'HOW TO PLAY', 'FORMAT'
        ]
    
    def is_metadata_line(self, line: str) -> bool:
        """Verifica se a linha é metadata e não uma carta"""
        line_upper = line.upper()
        
        # Linhas com separadores
        if any(sep in line for sep in ['===', '---', '***']):
            return True
        
        # Linhas que terminam com : ou contêm números entre parênteses
        if line.strip().endswith(':') or re.search(r'\(\d+\)', line):
            return True
        
        # Linhas que contêm palavras-chave de metadata
        for keyword in self.metadata_keywords:
            if keyword in line_upper:
                return True
        
        return False
    
    def parse_deck_line(self, line: str) -> Optional[Tuple[int, str]]:
        """
        Parser flexível que aceita vários formatos:
        - "4 Card Name"
        - "4x Card Name"
        - "Card Name x4"
        - "4 Card Name (Set1 #123)"
        
        Retorna None se não for uma linha de carta válida
        """
        line = line.strip()
        if not line:
            return None
        
        # Verificar se é linha de metadata
        if self.is_metadata_line(line):
            return None
        
        # Remover informações de set entre parênteses
        line_cleaned = re.sub(r'\([^)]*\)', '', line).strip()
        
        # Padrão 1: "4 Card Name" ou "4x Card Name"
        match = re.match(r'^(\d+)x?\s+(.+)$', line_cleaned)
        if match:
            return int(match.group(1)), match.group(2).strip()
        
        # Padrão 2: "Card Name x4"
        match = re.match(r'^(.+?)\s*x\s*(\d+)$', line_cleaned)
        if match:
            return int(match.group(2)), match.group(1).strip()
        
        # Se não encontrar quantidade mas parece ser uma carta
        # (não começa com caracteres especiais)
        if line_cleaned and line_cleaned[0].isalpha():
            return 1, line_cleaned
        
        return None
    
    def validate_text_deck(self, deck_text: str) -> Tuple[bool, List[str], Dict[str, any]]:
        """
        Valida um deck em formato texto
        Retorna: (válido, lista de erros, estatísticas)
        """
        errors = []
        stats = {
            'total_cards': 0,
            'power_cards': 0,
            'card_counts': {},
            'parsed_lines': 0,
            'failed_lines': [],
            'skipped_metadata': 0
        }
        
        lines = deck_text.strip().split('\n')
        
        for line_num, line in enumerate(lines, 1):
            # Pular linhas vazias
            if not line.strip():
                continue
            
            # Verificar se é metadata
            if self.is_metadata_line(line):
                stats['skipped_metadata'] += 1
                continue
            
            # Tentar parsear a linha
            parsed = self.parse_deck_line(line)
            
            if parsed:
                qty, card_name = parsed
                stats['parsed_lines'] += 1
                stats['total_cards'] += qty
                
                # Verificar se é power card (lista expandida)
                power_keywords = [
                    'Sigil', 'Power', 'Seat', 'Banner', 'Crest', 
                    'Waystone', 'Painting', 'Cylix', 'Standard',
                    'Insignia', 'Vow'
                ]
                if any(keyword in card_name for keyword in power_keywords):
                    stats['power_cards'] += qty
                
                # Contar cópias
                if card_name in stats['card_counts']:
                    stats['card_counts'][card_name] += qty
                else:
                    stats['card_counts'][card_name] = qty
            else:
                # Linha não parseada e não é metadata
                if line.strip():
                    stats['failed_lines'].append(f"Linha {line_num}: '{line.strip()}'")
        
        # Validações
        if stats['total_cards'] < self.rules['MIN_CARDS']:
            errors.append(f"Deck tem apenas {stats['total_cards']} cartas (mínimo {self.rules['MIN_CARDS']})")
        elif stats['total_cards'] > self.rules['MAX_CARDS']:
            errors.append(f"Deck tem {stats['total_cards']} cartas (máximo {self.rules['MAX_CARDS']})")
        
        if stats['total_cards'] > 0:
            power_ratio = stats['power_cards'] / stats['total_cards']
            min_ratio = self.rules['MIN_POWER_RATIO']
            
            if power_ratio < min_ratio:
                min_power = int(stats['total_cards'] * min_ratio)
                errors.append(f"Apenas {stats['power_cards']} cartas de poder ({power_ratio*100:.1f}%). Mínimo: {min_power} ({min_ratio*100:.0f}%)")
        
        # Verificar limite de cópias
        for card_name, count in stats['card_counts'].items():
            if count > self.rules['MAX_COPIES'] and 'Sigil' not in card_name:
                errors.append(f"'{card_name}' tem {count} cópias (máximo {self.rules['MAX_COPIES']})")
        
        # Avisar sobre linhas não parseadas (só se houver)
        if stats['failed_lines']:
            errors.append(f"Não foi possível interpretar {len(stats['failed_lines'])} linha(s): {', '.join(stats['failed_lines'][:3])}")
        
        return len(errors) == 0, errors, stats
    
    def validate_deck_rules(self, deck_list: str) -> str:
        """Método compatível com tools.py"""
        is_valid, errors, stats = self.validate_text_deck(deck_list)
        
        if is_valid:
            return f"DECK VÁLIDO: {stats['total_cards']} cartas, {stats['power_cards']} powers ({stats['power_cards']/stats['total_cards']*100:.1f}%)"
        else:
            return "DECK INVÁLIDO:\n" + "\n".join(errors)