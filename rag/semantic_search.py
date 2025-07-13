# rag/semantic_search.py
"""
🚨 ÂNCORA: RAG_SEARCH - Sistema de busca semântica para cartas
Contexto: Interface de alto nível para busca com ChromaDB
Cuidado: Manter compatibilidade com filtros estruturais existentes
Dependências: ChromaDBManager, GoogleSheetsClient
"""

from typing import List, Dict, Optional, Tuple
import sys
sys.path.append('..')

from rag.chromadb_setup import ChromaDBManager
from data.google_sheets_client import GoogleSheetsClient
from data.models import Card
from config.constants import FACTIONS


class SemanticCardSearch:
    """Interface de busca semântica para cartas do Eternal"""
    
    def __init__(self):
        """Inicializa o sistema de busca semântica"""
        self.chromadb_manager = ChromaDBManager()
        self.sheets_client = GoogleSheetsClient()
        
        # Cache de cartas para enriquecimento
        self._cards_cache = {}
        self._load_cards_cache()
    
    def _load_cards_cache(self):
        """Carrega cache de cartas para enriquecimento rápido"""
        all_cards = self.sheets_client.get_all_cards()
        
        for card in all_cards:
            # Usar múltiplas chaves para garantir match
            key1 = f"{card.set_number}_{card.eternal_id}_{card.name.replace(' ', '_')}"
            key2 = card.name
            
            self._cards_cache[key1] = card
            self._cards_cache[key2] = card
    
    def search_cards_for_strategy(self,
                                 strategy: str,
                                 allowed_factions: Optional[List[str]] = None,
                                 use_market: bool = False,
                                 required_cards: Optional[List[str]] = None,
                                 forbidden_cards: Optional[List[str]] = None,
                                 max_results: int = 80) -> List[Card]:
        """
        Busca cartas usando RAG para uma estratégia específica
        
        Args:
            strategy: Descrição da estratégia do deck
            allowed_factions: Facções permitidas (None = todas)
            use_market: Se deve incluir cartas de mercado
            required_cards: Cartas que DEVEM estar no resultado
            forbidden_cards: Cartas que NÃO DEVEM estar no resultado
            max_results: Número máximo de resultados
            
        Returns:
            Lista de objetos Card relevantes para a estratégia
        """
        # 🚨 ÂNCORA: HYBRID_SEARCH - Busca híbrida semântica + estrutural
        # Contexto: Combina relevância semântica com regras do jogo
        # Cuidado: Ordem importa - semântica primeiro, depois filtros
        # Dependências: ChromaDB para semântica, Google Sheets para dados
        
        # 1. Preparar query semântica enriquecida
        enriched_query = self._enrich_strategy_query(strategy, allowed_factions)
        
        # 2. Buscar semanticamente (com margem para filtros posteriores)
        search_results = self.chromadb_manager.search_similar_cards(
            strategy_text=enriched_query,
            n_results=max_results * 2,  # Buscar mais para ter margem após filtros
            filter_factions=allowed_factions,
            include_market=use_market
        )
        
        # 3. Converter resultados em objetos Card
        found_cards = []
        found_names = set()
        
        for result in search_results:
            # Tentar encontrar no cache
            card = None
            
            # Primeiro tentar pela ID completa
            if result['id'] in self._cards_cache:
                card = self._cards_cache[result['id']]
            # Depois tentar pelo nome
            elif result['name'] in self._cards_cache:
                card = self._cards_cache[result['name']]
            
            if card and card.name not in found_names:
                # Adicionar score de relevância
                card.semantic_score = result['similarity_score']
                found_cards.append(card)
                found_names.add(card.name)
        
        # 4. Aplicar filtros de cartas obrigatórias/proibidas
        filtered_cards = self._apply_card_filters(
            found_cards, 
            required_cards, 
            forbidden_cards
        )
        
        # 5. Adicionar cartas obrigatórias se não encontradas
        if required_cards:
            filtered_cards = self._ensure_required_cards(
                filtered_cards,
                required_cards,
                found_names
            )
        
        # 6. Ajustar para mercado se necessário
        if use_market:
            filtered_cards = self._ensure_market_cards(filtered_cards, allowed_factions)
        
        # 7. Limitar ao número solicitado
        final_cards = filtered_cards[:max_results]
        
        # 8. Ordenar por relevância mantendo diversidade
        final_cards = self._sort_by_relevance_and_diversity(final_cards)
        
        return final_cards
    
    def _enrich_strategy_query(self, strategy: str, factions: Optional[List[str]]) -> str:
        """
        Enriquece a query de estratégia com contexto adicional
        
        Args:
            strategy: Estratégia original
            factions: Facções escolhidas
            
        Returns:
            Query enriquecida para melhor busca semântica
        """
        # 🚨 ÂNCORA: QUERY_ENRICHMENT - Melhora queries para busca
        # Contexto: Adiciona contexto de TCG para melhorar resultados
        # Cuidado: Não sobrescrever intenção original do usuário
        # Dependências: Conhecimento de arquétipos e mecânicas
        
        enriched_parts = [strategy]
        
        # Adicionar contexto de facções
        if factions:
            faction_names = [FACTIONS.get(f, {}).get('name', f) for f in factions]
            faction_context = f"Using {', '.join(faction_names)} factions"
            enriched_parts.append(faction_context)
            
            # Adicionar características das facções
            faction_traits = {
                'FIRE': 'aggressive damage burn direct-damage weapons',
                'TIME': 'ramp big-creatures dinos sentinels',
                'JUSTICE': 'armor lifegain weapons removal',
                'PRIMAL': 'spells card-draw flying transform',
                'SHADOW': 'removal kill sacrifice void-recursion'
            }
            
            for faction in factions:
                if faction in faction_traits:
                    enriched_parts.append(faction_traits[faction])
        
        # Detectar e enriquecer arquétipos
        strategy_lower = strategy.lower()
        
        if any(word in strategy_lower for word in ['aggro', 'aggressive', 'fast', 'burn']):
            enriched_parts.append('charge overwhelm warcry low-cost efficient')
        
        elif any(word in strategy_lower for word in ['control', 'removal', 'slow']):
            enriched_parts.append('removal sweepers card-draw late-game answers')
        
        elif any(word in strategy_lower for word in ['midrange', 'value', 'balanced']):
            enriched_parts.append('efficient-units good-stats value-trades')
        
        elif any(word in strategy_lower for word in ['combo', 'synergy', 'engine']):
            enriched_parts.append('synergistic combo-pieces enablers payoffs')
        
        return ' '.join(enriched_parts)
    
    def _apply_card_filters(self, 
                          cards: List[Card], 
                          required: Optional[List[str]], 
                          forbidden: Optional[List[str]]) -> List[Card]:
        """Aplica filtros de cartas obrigatórias e proibidas"""
        if not required and not forbidden:
            return cards
        
        filtered = []
        
        for card in cards:
            # Verificar proibidas
            if forbidden and any(
                forbidden_name.lower() in card.name.lower() 
                for forbidden_name in forbidden
            ):
                continue
            
            filtered.append(card)
        
        return filtered
    
    def _ensure_required_cards(self, 
                             cards: List[Card], 
                             required: List[str],
                             found_names: set) -> List[Card]:
        """Garante que cartas obrigatórias estejam incluídas"""
        result = cards.copy()
        
        for required_name in required:
            # Verificar se já está na lista
            if any(required_name.lower() in name.lower() for name in found_names):
                continue
            
            # Buscar carta obrigatória
            search_results = self.sheets_client.search_cards(
                name=required_name,
                limit=1
            )
            
            if search_results:
                card = search_results[0]
                card.semantic_score = 1.0  # Alta prioridade por ser obrigatória
                result.insert(0, card)  # Adicionar no início
        
        return result
    
    def _ensure_market_cards(self, cards: List[Card], factions: Optional[List[str]]) -> List[Card]:
        """Garante que haja opções de acesso ao mercado"""
        # 🚨 ÂNCORA: MARKET_DETECTION - Detecção de cartas de mercado
        # Contexto: Merchants e smugglers dão acesso ao mercado
        # Cuidado: Diferentes tipos têm restrições de facção
        # Dependências: Card text deve conter palavras-chave corretas
        
        # Verificar se já tem merchant/smuggler
        has_market_access = any(
            card.card_text and any(
                term in card.card_text.lower() 
                for term in ['market', 'merchant', 'smuggler', 'etchings']
            )
            for card in cards
        )
        
        if has_market_access:
            return cards
        
        # Buscar merchants/smugglers apropriados
        market_cards = []
        
        # Termos de busca por tipo
        market_search_terms = [
            'merchant',
            'smuggler',
            'etchings',
            'marketeer'
        ]
        
        for term in market_search_terms:
            results = self.sheets_client.search_cards(
                card_text=term,
                factions=factions,
                limit=10
            )
            market_cards.extend(results)
        
        # Adicionar os mais relevantes
        if market_cards:
            # Ordenar por custo (merchants mais baratos primeiro)
            market_cards.sort(key=lambda x: x.cost)
            
            # Adicionar 2-3 opções
            for i, card in enumerate(market_cards[:3]):
                if card not in cards:
                    card.semantic_score = 0.8  # Boa prioridade
                    cards.insert(i * 5, card)  # Distribuir na lista
        
        return cards
    
    def _sort_by_relevance_and_diversity(self, cards: List[Card]) -> List[Card]:
        """
        Ordena cartas balanceando relevância e diversidade
        
        Args:
            cards: Lista de cartas com semantic_score
            
        Returns:
            Lista ordenada para máxima utilidade
        """
        # 🚨 ÂNCORA: DIVERSITY_SORT - Balanceia relevância com variedade
        # Contexto: Evita muitas cartas similares no topo
        # Cuidado: Não perder cartas muito relevantes
        # Dependências: semantic_score deve estar presente
        
        # Separar por categorias
        categories = {
            'units': [],
            'spells': [],
            'powers': [],
            'weapons': [],
            'relics': [],
            'others': []
        }
        
        for card in cards:
            score = getattr(card, 'semantic_score', 0.5)
            
            if card.is_unit:
                categories['units'].append((card, score))
            elif card.is_power:
                categories['powers'].append((card, score))
            elif 'Spell' in card.type:
                categories['spells'].append((card, score))
            elif 'Weapon' in card.type:
                categories['weapons'].append((card, score))
            elif 'Relic' in card.type:
                categories['relics'].append((card, score))
            else:
                categories['others'].append((card, score))
        
        # Ordenar cada categoria por score
        for category in categories.values():
            category.sort(key=lambda x: x[1], reverse=True)
        
        # Intercalar categorias para diversidade
        result = []
        
        # Primeiro, adicionar top cards de cada categoria
        for category in ['units', 'spells', 'powers', 'weapons', 'relics']:
            if categories[category]:
                card, score = categories[category].pop(0)
                result.append(card)
        
        # Depois, adicionar restante por relevância global
        remaining = []
        for category in categories.values():
            remaining.extend(category)
        
        remaining.sort(key=lambda x: x[1], reverse=True)
        
        for card, score in remaining:
            if card not in result:
                result.append(card)
        
        return result
    
    def get_search_statistics(self) -> Dict:
        """Retorna estatísticas sobre o sistema de busca"""
        info = self.chromadb_manager.get_collection_info()
        
        return {
            'chromadb_status': 'ready' if info['exists'] else 'not_initialized',
            'total_embeddings': info['count'],
            'cache_size': len(self._cards_cache),
            'metadata': info['metadata']
        }


# Função auxiliar para integração rápida
def create_semantic_search() -> SemanticCardSearch:
    """Cria e retorna uma instância configurada do SemanticCardSearch"""
    return SemanticCardSearch()


# Script de teste se executado diretamente
if __name__ == "__main__":
    print("🔍 Testando sistema de busca semântica...")
    
    searcher = SemanticCardSearch()
    
    # Verificar status
    stats = searcher.get_search_statistics()
    print(f"\n📊 Status do sistema:")
    print(f"   ChromaDB: {stats['chromadb_status']}")
    print(f"   Total embeddings: {stats['total_embeddings']}")
    print(f"   Cache size: {stats['cache_size']}")
    
    if stats['chromadb_status'] != 'ready':
        print("\n❌ ChromaDB não está inicializado! Execute chromadb_setup.py primeiro.")
        exit(1)
    
    # Testar buscas
    test_cases = [
        {
            'strategy': 'Quero um deck agressivo de Fire com muitas unidades pequenas e dano direto',
            'factions': ['FIRE'],
            'use_market': False
        },
        {
            'strategy': 'Deck de controle com remoção e card draw',
            'factions': ['JUSTICE', 'PRIMAL'],
            'use_market': True
        },
        {
            'strategy': 'Deck midrange com unidades voadoras eficientes',
            'factions': ['TIME', 'PRIMAL'],
            'required_cards': ['Sandstorm Titan']
        }
    ]
    
    for i, test in enumerate(test_cases):
        print(f"\n\n{'='*60}")
        print(f"Teste {i+1}: {test['strategy']}")
        print(f"Facções: {test.get('factions', 'Todas')}")
        print(f"Mercado: {'Sim' if test.get('use_market') else 'Não'}")
        
        results = searcher.search_cards_for_strategy(
            strategy=test['strategy'],
            allowed_factions=test.get('factions'),
            use_market=test.get('use_market', False),
            required_cards=test.get('required_cards'),
            max_results=20
        )
        
        print(f"\nTop 10 resultados:")
        for j, card in enumerate(results[:10]):
            score = getattr(card, 'semantic_score', 0)
            print(f"{j+1:2d}. {card.name:30s} | {card.cost}{card.influence_string or ''} | Score: {score:.3f}")