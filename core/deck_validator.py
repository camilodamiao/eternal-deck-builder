"""Validador de decks com parser flexível para múltiplos formatos"""
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
        
        # Linhas que terminam com : ou contêm números entre parênteses (mas não info de set)
        if line.strip().endswith(':'):
            return True
        
        # Linhas que parecem seções (ex: "UNITS (28):")
        if re.search(r'^[A-Z\s]+\s*\(\d+\)\s*:?\s*$', line.strip()):
            return True
        
        # Linhas que contêm palavras-chave de metadata
        for keyword in self.metadata_keywords:
            if keyword in line_upper and '|' not in line:  # Evitar falsos positivos com cartas
                return True
        
        return False
    
    def parse_deck_line(self, line: str) -> Optional[Tuple[int, str]]:
        """
        Parser flexível que aceita vários formatos:
        - "4 Card Name"
        - "4x Card Name"
        - "Card Name x4"
        - "4 Card Name (Set1 #123)"
        - "4x Card Name | 2{F} | 3/2 | Rare" (NOVO FORMATO)
        
        Retorna None se não for uma linha de carta válida
        """
        line = line.strip()
        if not line:
            return None
        
        # Verificar se é linha de metadata
        if self.is_metadata_line(line):
            return None
        
        # NOVO: Lidar com formato com pipes primeiro
        if '|' in line:
            # Formato: "4x Card Name | Cost | Stats | Rarity"
            parts = line.split('|')
            if len(parts) >= 2:  # Pelo menos quantidade/nome e mais alguma info
                first_part = parts[0].strip()
                
                # Tentar extrair quantidade e nome
                # Padrão: "4x Card Name" ou "4 Card Name"
                match = re.match(r'^(\d+)x?\s+(.+)$', first_part)
                if match:
                    return int(match.group(1)), match.group(2).strip()
                
                # Padrão alternativo: "Card Name x4"
                match = re.match(r'^(.+?)\s*x\s*(\d+)$', first_part)
                if match:
                    return int(match.group(2)), match.group(1).strip()
        
        # Formato antigo sem pipes
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
            'skipped_metadata': 0,
            'format_detected': 'unknown'
        }
        
        lines = deck_text.strip().split('\n')
        
        # Detectar formato
        for line in lines[:20]:  # Verificar primeiras 20 linhas
            if '|' in line and any(char in line for char in ['{', '}']):
                stats['format_detected'] = 'new_pipe_format'
                break
            elif re.search(r'\(Set\d+\s*#\d+\)', line):
                stats['format_detected'] = 'export_format'
                break
            elif re.match(r'^\d+x?\s+\w+', line):
                stats['format_detected'] = 'simple_format'
                break
        
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
                    'Insignia', 'Vow', 'Etchings'
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
                if line.strip() and not line.strip().startswith('#'):  # Ignorar comentários
                    stats['failed_lines'].append(f"Linha {line_num}: '{line.strip()[:50]}...'")
        
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
        
        # Avisar sobre linhas não parseadas (só se houver muitas)
        if len(stats['failed_lines']) > 3:
            errors.append(f"Não foi possível interpretar {len(stats['failed_lines'])} linhas")
        elif stats['failed_lines']:
            for failed in stats['failed_lines'][:3]:
                errors.append(f"Linha não parseada: {failed}")
        
        return len(errors) == 0, errors, stats
    
    def validate_deck_rules(self, deck_list: str) -> str:
        """Método compatível com tools.py"""
        is_valid, errors, stats = self.validate_text_deck(deck_list)
        
        info = f"Formato detectado: {stats['format_detected']}\n"
        
        if is_valid:
            return info + f"DECK VÁLIDO: {stats['total_cards']} cartas, {stats['power_cards']} powers ({stats['power_cards']/stats['total_cards']*100:.1f}%)"
        else:
            return info + "DECK INVÁLIDO:\n" + "\n".join(errors)
    
    def extract_deck_for_export(self, deck_text: str) -> List[Tuple[int, str]]:
        """
        Extrai apenas as linhas de cartas do deck para exportação,
        ignorando metadata e formato específico
        """
        deck_cards = []
        lines = deck_text.strip().split('\n')
        
        for line in lines:
            if not line.strip():
                continue
                
            if self.is_metadata_line(line):
                continue
            
            parsed = self.parse_deck_line(line)
            if parsed:
                deck_cards.append(parsed)
        
        return deck_cards