# rag/chromadb_setup.py
"""
🚨 ÂNCORA: RAG_SETUP - Configuração inicial ChromaDB
Contexto: Embeddings locais para busca semântica de cartas
Cuidado: Manter consistência entre metadata e dados originais
Dependências: Google Sheets como fonte única
"""

import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
import json
import os
from typing import List, Dict, Optional
from datetime import datetime
import sys
sys.path.append('..')

from data.google_sheets_client import GoogleSheetsClient
from data.models import Card
from config.settings import Settings as AppSettings


class ChromaDBManager:
    """Gerenciador de embeddings de cartas usando ChromaDB"""
    
    def __init__(self, persist_directory: str = "./data/embeddings"):
        """
        Inicializa o ChromaDB com persistência local
        
        Args:
            persist_directory: Diretório para armazenar os embeddings
        """
        # 🚨 ÂNCORA: CHROMADB_CONFIG - Configuração local sem dependência externa
        # Contexto: ChromaDB rodando localmente com persistência em disco
        # Cuidado: Não alterar para client/server sem necessidade
        # Dependências: Nenhuma dependência de rede necessária
        
        self.persist_directory = persist_directory
        os.makedirs(persist_directory, exist_ok=True)
        
        # Configurar ChromaDB com persistência local
        self.chroma_client = chromadb.PersistentClient(
            path=persist_directory,
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
        
        # Modelo de embeddings - usando sentence-transformers
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        
        # Nome da coleção principal
        self.collection_name = "eternal_cards"
        
        # Cliente Google Sheets
        self.sheets_client = GoogleSheetsClient()
    
    def setup_card_embeddings(self, force_recreate: bool = False) -> Dict[str, int]:
        """
        Configura embeddings iniciais das cartas
        
        Args:
            force_recreate: Se True, recria a coleção do zero
            
        Returns:
            Dict com estatísticas: {'total_cards': X, 'embedded_cards': Y, 'time_taken': Z}
        """
        start_time = datetime.now()
        
        # 🚨 ÂNCORA: COLLECTION_RESET - Reset controlado da coleção
        # Contexto: Permite recriar embeddings sem perder dados acidentalmente
        # Cuidado: force_recreate=True apaga todos os embeddings existentes
        # Dependências: Necessário recarregar todas as cartas do Google Sheets
        
        if force_recreate:
            try:
                self.chroma_client.delete_collection(self.collection_name)
                print(f"Coleção '{self.collection_name}' deletada para recriação")
            except:
                print(f"Coleção '{self.collection_name}' não existia, criando nova")
        
        # Criar ou obter coleção
        collection = self.chroma_client.get_or_create_collection(
            name=self.collection_name,
            metadata={"description": "Eternal Card Game cards with semantic embeddings"}
        )
        
        # Verificar se já tem dados
        existing_count = collection.count()
        if existing_count > 0 and not force_recreate:
            print(f"Coleção já contém {existing_count} cartas")
            return {
                'total_cards': existing_count,
                'embedded_cards': 0,
                'time_taken': 0,
                'status': 'already_exists'
            }
        
        # Carregar todas as cartas do Google Sheets
        print("Carregando cartas do Google Sheets...")
        all_cards = self.sheets_client.get_all_cards()
        
        # Filtrar apenas cartas jogáveis
        playable_cards = [card for card in all_cards if card.deck_buildable]
        print(f"Total de cartas jogáveis: {len(playable_cards)}")
        
        # Preparar dados para embedding
        documents = []
        metadatas = []
        ids = []
        
        for card in playable_cards:
            # 🚨 ÂNCORA: EMBEDDING_TEXT - Texto usado para criar embeddings
            # Contexto: Combina nome + texto + tipo para busca semântica rica
            # Cuidado: Mudanças aqui requerem recriar todos embeddings
            # Dependências: Busca semântica depende desta estrutura
            
            # Criar texto rico para embedding
            embedding_text = self._create_embedding_text(card)
            
            # Metadata estruturada para filtros
            metadata = {
                'name': card.name,
                'cost': card.cost,
                'influence': card.influence_string or '',
                'attack': card.attack or 0,
                'health': card.health or 0,
                'rarity': card.rarity or 'Common',
                'type': card.type,
                'factions': ','.join(card.factions) if card.factions else '',
                'set_number': card.set_number or 0,
                'eternal_id': card.eternal_id or 0,
                'is_unit': card.is_unit,
                'is_spell': 'Spell' in card.type,
                'is_power': card.is_power,
                'is_relic': 'Relic' in card.type,
                'is_weapon': 'Weapon' in card.type,
                'is_market': self._is_market_card(card)
            }
            
            documents.append(embedding_text)
            metadatas.append(metadata)
            ids.append(f"{card.set_number}_{card.eternal_id}_{card.name.replace(' ', '_')}")
        
        # Adicionar em batches para performance
        batch_size = 100
        total_added = 0
        
        print(f"Criando embeddings para {len(documents)} cartas...")
        
        for i in range(0, len(documents), batch_size):
            batch_docs = documents[i:i+batch_size]
            batch_meta = metadatas[i:i+batch_size]
            batch_ids = ids[i:i+batch_size]
            
            # ChromaDB cria embeddings automaticamente
            collection.add(
                documents=batch_docs,
                metadatas=batch_meta,
                ids=batch_ids
            )
            
            total_added += len(batch_docs)
            print(f"Progresso: {total_added}/{len(documents)} cartas processadas")
        
        # Salvar estatísticas
        time_taken = (datetime.now() - start_time).total_seconds()
        
        stats = {
            'total_cards': len(all_cards),
            'embedded_cards': len(documents),
            'time_taken': time_taken,
            'status': 'created'
        }
        
        # Salvar metadata da coleção
        self._save_collection_metadata(stats)
        
        print(f"\n✅ Embeddings criados com sucesso!")
        print(f"   Total de cartas: {stats['total_cards']}")
        print(f"   Cartas com embeddings: {stats['embedded_cards']}")
        print(f"   Tempo gasto: {stats['time_taken']:.2f} segundos")
        
        return stats
    
    def search_similar_cards(self, 
                           strategy_text: str, 
                           n_results: int = 60,
                           filter_factions: Optional[List[str]] = None,
                           include_market: bool = False,
                           cost_range: Optional[tuple] = None) -> List[Dict]:
        """
        Busca cartas similares baseado na estratégia
        
        Args:
            strategy_text: Texto da estratégia do usuário
            n_results: Número de resultados desejados
            filter_factions: Lista de facções permitidas (opcional)
            include_market: Se deve incluir cartas de mercado
            cost_range: Tupla (min_cost, max_cost) opcional
            
        Returns:
            Lista de dicionários com cartas e scores de similaridade
        """
        # Obter coleção
        collection = self.chroma_client.get_collection(self.collection_name)
        
        # 🚨 ÂNCORA: SEMANTIC_FILTERS - Filtros aplicados após busca semântica
        # Contexto: ChromaDB permite where clauses para filtrar metadata
        # Cuidado: Filtros muito restritivos podem reduzir qualidade semântica
        # Dependências: Metadata deve estar correta na criação dos embeddings
        
        # Construir filtros
        where_clause = {}
        
        if filter_factions:
            # Filtrar por facções usando operador $or
            faction_filters = []
            for faction in filter_factions:
                faction_filters.append({"factions": {"$contains": faction}})
            
            if len(faction_filters) > 1:
                where_clause["$or"] = faction_filters
            else:
                where_clause = faction_filters[0]
        
        if not include_market:
            where_clause["is_market"] = False
        
        if cost_range:
            where_clause["cost"] = {
                "$gte": cost_range[0],
                "$lte": cost_range[1]
            }
        
        # Realizar busca semântica
        results = collection.query(
            query_texts=[strategy_text],
            n_results=n_results,
            where=where_clause if where_clause else None,
            include=["documents", "metadatas", "distances"]
        )
        
        # Formatar resultados
        formatted_results = []
        
        if results['ids'] and len(results['ids'][0]) > 0:
            for i, card_id in enumerate(results['ids'][0]):
                formatted_results.append({
                    'id': card_id,
                    'name': results['metadatas'][0][i]['name'],
                    'metadata': results['metadatas'][0][i],
                    'text': results['documents'][0][i],
                    'similarity_score': 1 - results['distances'][0][i],  # Converter distância em similaridade
                    'distance': results['distances'][0][i]
                })
        
        return formatted_results
    
    def _create_embedding_text(self, card: Card) -> str:
        """
        Cria texto otimizado para embedding de uma carta
        
        Args:
            card: Objeto Card
            
        Returns:
            Texto formatado para embedding
        """
        # 🚨 ÂNCORA: EMBEDDING_FORMAT - Formato do texto para embeddings
        # Contexto: Estrutura otimizada para capturar semântica de TCG
        # Cuidado: Manter ordem e estrutura para consistência
        # Dependências: search_similar_cards espera este formato
        
        parts = [
            f"Card: {card.name}",
            f"Type: {card.type}",
            f"Cost: {card.cost}",
        ]
        
        if card.factions:
            parts.append(f"Factions: {', '.join(card.factions)}")
        
        if card.is_unit:
            parts.append(f"Stats: {card.attack}/{card.health}")
        
        if card.card_text:
            parts.append(f"Text: {card.card_text}")
        
        if card.rarity:
            parts.append(f"Rarity: {card.rarity}")
        
        # Adicionar keywords implícitos baseados no texto
        keywords = self._extract_keywords(card)
        if keywords:
            parts.append(f"Keywords: {', '.join(keywords)}")
        
        return " | ".join(parts)
    
    def _extract_keywords(self, card: Card) -> List[str]:
        """Extrai keywords relevantes do texto da carta"""
        keywords = []
        
        if not card.card_text:
            return keywords
        
        text_lower = card.card_text.lower()
        
        # Keywords de mecânicas
        mechanics = [
            'flying', 'charge', 'deadly', 'lifesteal', 'overwhelm',
            'aegis', 'endurance', 'quickdraw', 'unblockable', 'warcry',
            'echo', 'destiny', 'revenge', 'scout', 'inspire', 'empower',
            'summon', 'entomb', 'ultimate', 'mastery', 'tribute',
            'infiltrate', 'killer', 'reckless', 'berserk', 'decay'
        ]
        
        for mechanic in mechanics:
            if mechanic in text_lower:
                keywords.append(mechanic)
        
        # Keywords de estratégia
        if 'draw' in text_lower:
            keywords.append('card-draw')
        if 'damage' in text_lower:
            keywords.append('removal')
        if 'kill' in text_lower or 'destroy' in text_lower:
            keywords.append('hard-removal')
        if '+' in card.card_text and '/' in card.card_text:
            keywords.append('buff')
        if 'power' in text_lower and 'play' in text_lower:
            keywords.append('ramp')
        if 'void' in text_lower:
            keywords.append('graveyard')
        
        return keywords
    
    def _is_market_card(self, card: Card) -> bool:
        """Detecta se é uma carta relacionada a mercado"""
        if not card.card_text:
            return False
        
        market_terms = ['market', 'merchant', 'smuggler', 'etchings']
        text_lower = card.card_text.lower()
        
        return any(term in text_lower for term in market_terms)
    
    def _save_collection_metadata(self, stats: Dict):
        """Salva metadata sobre a coleção"""
        metadata_path = os.path.join(self.persist_directory, 'collection_metadata.json')
        
        metadata = {
            'created_at': datetime.now().isoformat(),
            'stats': stats,
            'embedding_model': 'all-MiniLM-L6-v2',
            'collection_name': self.collection_name
        }
        
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
    
    def get_collection_info(self) -> Dict:
        """Retorna informações sobre a coleção atual"""
        try:
            collection = self.chroma_client.get_collection(self.collection_name)
            
            metadata_path = os.path.join(self.persist_directory, 'collection_metadata.json')
            
            if os.path.exists(metadata_path):
                with open(metadata_path, 'r') as f:
                    metadata = json.load(f)
            else:
                metadata = {}
            
            return {
                'exists': True,
                'count': collection.count(),
                'metadata': metadata
            }
        except:
            return {
                'exists': False,
                'count': 0,
                'metadata': {}
            }


# Script de teste/setup se executado diretamente
if __name__ == "__main__":
    print("🚀 Iniciando setup do ChromaDB para Eternal Deck Builder...")
    
    manager = ChromaDBManager()
    
    # Verificar se já existe
    info = manager.get_collection_info()
    
    if info['exists']:
        print(f"\n📊 Coleção existente encontrada com {info['count']} cartas")
        response = input("Deseja recriar do zero? (s/n): ")
        force_recreate = response.lower() == 's'
    else:
        print("\n📊 Nenhuma coleção encontrada, criando nova...")
        force_recreate = True
    
    # Executar setup
    stats = manager.setup_card_embeddings(force_recreate=force_recreate)
    
    # Testar busca
    if stats['embedded_cards'] > 0:
        print("\n🔍 Testando busca semântica...")
        
        test_queries = [
            "aggressive fire creatures with charge",
            "control deck with removal and card draw",
            "flying units with aegis",
            "ramp strategies with big creatures"
        ]
        
        for query in test_queries:
            print(f"\nQuery: '{query}'")
            results = manager.search_similar_cards(query, n_results=5)
            
            print(f"Top 5 resultados:")
            for i, result in enumerate(results[:5]):
                print(f"  {i+1}. {result['name']} (Score: {result['similarity_score']:.3f})")