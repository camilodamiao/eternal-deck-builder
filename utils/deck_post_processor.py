"""Pós-processador para validar e corrigir decks gerados pela IA"""
from typing import List, Tuple, Dict
from data.models import Card
import re

class DeckPostProcessor:
    def __init__(self, cards_database: List[Card]):
        """
        Inicializa o pós-processador com a base de dados de cartas
        
        Args:
            cards_database: Lista de todas as cartas do jogo
        """
        # Criar dicionário para busca rápida (case-insensitive)
        self.cards_dict = {card.name.lower(): card for card in cards_database}
        self.influence_map = {'FIRE': 'F', 'TIME': 'T', 'JUSTICE': 'J', 'PRIMAL': 'P', 'SHADOW': 'S'}
    
    def format_influence(self, card: Card) -> str:
        """Formata influência no estilo {F}{T}{J}"""
        if not card.influence:
            return str(card.cost)
        
        influence_str = str(card.cost)
        
        for faction, count in sorted(card.influence.items()):
            symbol = self.influence_map.get(faction, '?')
            influence_str += '{' + symbol + '}' * count
            
        return influence_str
    
    def validate_and_fix_deck(self, deck_text: str) -> Tuple[str, List[str], Dict[str, int]]:
        """
        Valida o deck gerado e corrige informações incorretas
        
        Args:
            deck_text: Texto do deck gerado pela IA
            
        Returns:
            Tuple de (deck_corrigido, lista_de_correções, estatísticas)
        """
        corrections = []
        fixed_lines = []
        stats = {
            'total_corrections': 0,
            'cards_not_found': 0,
            'rarity_fixes': 0,
            'influence_fixes': 0,
            'stats_fixes': 0
        }
        
        lines = deck_text.strip().split('\n')
        
        for line_num, line in enumerate(lines, 1):
            # Pular linhas vazias
            if not line.strip():
                fixed_lines.append(line)
                continue
            
            # Se é metadata, manter como está
            if self._is_metadata_line(line):
                fixed_lines.append(line)
                continue
            
            # Tentar processar linha de carta
            processed = self._process_card_line(line)
            
            if processed:
                fixed_line, correction_msg = processed
                fixed_lines.append(fixed_line)
                
                if correction_msg:
                    corrections.append(f"Linha {line_num}: {correction_msg}")
                    stats['total_corrections'] += 1
                    
                    # Categorizar correção
                    if 'não encontrada' in correction_msg:
                        stats['cards_not_found'] += 1
                    elif 'raridade' in correction_msg.lower():
                        stats['rarity_fixes'] += 1
                    elif 'influência' in correction_msg.lower():
                        stats['influence_fixes'] += 1
                    elif 'stats' in correction_msg.lower():
                        stats['stats_fixes'] += 1
            else:
                # Linha não processável, manter como está
                fixed_lines.append(line)
        
        return '\n'.join(fixed_lines), corrections, stats
    
    def _is_metadata_line(self, line: str) -> bool:
        """Verifica se é uma linha de metadata"""
        metadata_indicators = [
            '===', '---', '***',
            'DECK', 'ESTRATÉGIA', 'COMO JOGAR',
            'STRATEGY', 'HOW TO PLAY', 'MARKET',
            'UNITS', 'SPELLS', 'POWERS', 'WEAPONS'
        ]
        
        line_upper = line.upper()
        
        # Linhas com separadores ou que terminam com :
        if any(sep in line for sep in ['===', '---', '***']) or line.strip().endswith(':'):
            return True
        
        # Linhas com palavras-chave (mas sem pipes, para evitar falsos positivos)
        if '|' not in line:
            for indicator in metadata_indicators:
                if indicator in line_upper:
                    return True
        
        return False
    
    def _process_card_line(self, line: str) -> Tuple[str, str]:
        """
        Processa uma linha de carta e retorna a versão corrigida
        
        Returns:
            Tuple de (linha_corrigida, mensagem_de_correção)
            ou None se não for uma linha de carta
        """
        # Verificar se parece uma linha de carta no novo formato
        if '|' in line and re.match(r'^\d+x?\s+', line):
            parts = line.split('|')
            
            if len(parts) >= 2:  # Mínimo: quantidade/nome e alguma outra info
                qty_name = parts[0].strip()
                
                # Extrair quantidade e nome
                match = re.match(r'^(\d+)x?\s+(.+)$', qty_name)
                if not match:
                    return None
                
                qty = match.group(1)
                card_name = match.group(2).strip()
                
                # Buscar carta real na base de dados
                card = self.cards_dict.get(card_name.lower())
                
                if not card:
                    # Carta não encontrada
                    msg = f"'{card_name}' não encontrada na base de dados"
                    return line, msg
                
                # Construir linha correta
                correct_line = self._build_correct_line(qty, card)
                
                # Comparar com linha original
                if line.strip() != correct_line:
                    # Identificar o que foi corrigido
                    corrections = []
                    
                    # Verificar cada parte
                    if len(parts) >= 4:
                        original_cost = parts[1].strip() if len(parts) > 1 else ""
                        original_stats = parts[2].strip() if len(parts) > 2 else ""
                        original_rarity = parts[3].strip() if len(parts) > 3 else ""
                        
                        correct_influence = self.format_influence(card)
                        correct_stats = self._get_card_stats(card)
                        
                        if original_cost != correct_influence:
                            corrections.append("influência")
                        if original_stats != correct_stats:
                            corrections.append("stats")
                        if original_rarity != card.rarity:
                            corrections.append("raridade")
                    
                    msg = f"{card.name} - corrigido: {', '.join(corrections)}"
                    return correct_line, msg
                else:
                    # Linha já está correta
                    return line, None
        
        # Não é uma linha de carta no formato esperado
        return None
    
    def _build_correct_line(self, qty: str, card: Card) -> str:
        """Constrói a linha correta para uma carta"""
        influence = self.format_influence(card)
        stats = self._get_card_stats(card)
        
        return f"{qty}x {card.name} | {influence} | {stats} | {card.rarity}"
    
    def _get_card_stats(self, card: Card) -> str:
        """Obtém os stats corretos para uma carta"""
        if card.card_type == "Unit":
            return f"{card.attack}/{card.health}"
        elif card.card_type == "Weapon" and card.attack is not None:
            health_bonus = card.health if card.health else 0
            return f"+{card.attack}/+{health_bonus}"
        elif card.card_type == "Power":
            return "N/A"
        elif card.card_type == "Spell":
            return "Spell"
        elif card.card_type == "Relic":
            return "Relic"
        else:
            return "N/A"
    
    def generate_correction_report(self, corrections: List[str], stats: Dict[str, int]) -> str:
        """Gera um relatório das correções aplicadas"""
        if not corrections:
            return "✅ Nenhuma correção necessária - deck gerado corretamente!"
        
        report = f"📊 **Relatório de Correções**\n\n"
        report += f"Total de correções: {stats['total_corrections']}\n"
        
        if stats['cards_not_found'] > 0:
            report += f"⚠️ Cartas não encontradas: {stats['cards_not_found']}\n"
        if stats['rarity_fixes'] > 0:
            report += f"🏷️ Raridades corrigidas: {stats['rarity_fixes']}\n"
        if stats['influence_fixes'] > 0:
            report += f"💎 Influências corrigidas: {stats['influence_fixes']}\n"
        if stats['stats_fixes'] > 0:
            report += f"⚔️ Stats corrigidos: {stats['stats_fixes']}\n"
        
        report += "\n**Detalhes das correções:**\n"
        for i, correction in enumerate(corrections[:10], 1):  # Mostrar até 10
            report += f"{i}. {correction}\n"
        
        if len(corrections) > 10:
            report += f"\n... e mais {len(corrections) - 10} correções\n"
        
        return report