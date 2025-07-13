# test_rag_comparison.py
"""
Script de teste para comparar busca tradicional vs RAG
"""

import streamlit as st
import time
from typing import Dict, List
import pandas as pd

# Imports do projeto
from data.google_sheets_client import GoogleSheetsClient
from rag.semantic_search import create_semantic_search
from rag.chromadb_setup import ChromaDBManager


def test_traditional_search(strategy: str, factions: List[str], limit: int = 50) -> Dict:
    """Testa busca tradicional por keywords"""
    start_time = time.time()
    
    client = GoogleSheetsClient()
    
    # Extrair keywords da estratégia
    keywords = strategy.lower().split()
    
    # Buscar por keywords
    results = []
    for keyword in keywords[:5]:  # Limitar keywords
        cards = client.search_cards(
            card_text=keyword,
            factions=factions,
            limit=20
        )
        results.extend(cards)
    
    # Remover duplicatas
    unique_cards = {}
    for card in results:
        unique_cards[card.name] = card
    
    final_results = list(unique_cards.values())[:limit]
    
    end_time = time.time()
    
    return {
        'method': 'Traditional Keyword Search',
        'cards': final_results,
        'count': len(final_results),
        'time': end_time - start_time,
        'details': f"Keywords used: {keywords[:5]}"
    }


def test_rag_search(strategy: str, factions: List[str], limit: int = 50) -> Dict:
    """Testa busca com RAG"""
    start_time = time.time()
    
    try:
        searcher = create_semantic_search()
        
        # Verificar se está inicializado
        stats = searcher.get_search_statistics()
        if stats['chromadb_status'] != 'ready':
            return {
                'method': 'RAG Semantic Search',
                'error': 'ChromaDB not initialized',
                'cards': [],
                'count': 0,
                'time': 0
            }
        
        # Buscar semanticamente
        results = searcher.search_cards_for_strategy(
            strategy=strategy,
            allowed_factions=factions,
            max_results=limit
        )
        
        end_time = time.time()
        
        return {
            'method': 'RAG Semantic Search',
            'cards': results,
            'count': len(results),
            'time': end_time - start_time,
            'details': f"Embeddings searched: {stats['total_embeddings']}"
        }
        
    except Exception as e:
        return {
            'method': 'RAG Semantic Search',
            'error': str(e),
            'cards': [],
            'count': 0,
            'time': 0
        }


def main():
    st.set_page_config(page_title="RAG vs Traditional Search", layout="wide")
    
    st.title("🔍 Comparação: Busca Tradicional vs RAG")
    st.markdown("---")
    
    # Sidebar para configurações
    with st.sidebar:
        st.header("⚙️ Configurações")
        
        # Seleção de facções
        st.subheader("Facções")
        factions = st.multiselect(
            "Selecione as facções",
            options=['FIRE', 'TIME', 'JUSTICE', 'PRIMAL', 'SHADOW'],
            default=['FIRE', 'TIME']
        )
        
        # Número de resultados
        max_results = st.slider(
            "Máximo de resultados",
            min_value=10,
            max_value=100,
            value=50,
            step=10
        )
        
        # Status do RAG
        st.subheader("📊 Status do Sistema")
        
        try:
            manager = ChromaDBManager()
            info = manager.get_collection_info()
            
            if info['exists']:
                st.success(f"✅ ChromaDB: {info['count']} cartas")
            else:
                st.warning("⚠️ ChromaDB não inicializado")
                
                if st.button("🚀 Inicializar ChromaDB"):
                    with st.spinner("Criando embeddings..."):
                        stats = manager.setup_card_embeddings()
                        st.success(f"✅ {stats['embedded_cards']} cartas indexadas!")
                        st.experimental_rerun()
        except:
            st.error("❌ Erro ao verificar ChromaDB")
    
    # Área principal
    st.header("🎯 Teste de Estratégia")
    
    # Exemplos de estratégias
    example_strategies = [
        "Deck agressivo com criaturas pequenas e dano direto",
        "Controle com muita remoção e card draw",
        "Midrange com unidades voadoras eficientes",
        "Combo com sinergias de void e sacrifício",
        "Ramp para jogar criaturas grandes rapidamente"
    ]
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        strategy = st.text_area(
            "Descreva a estratégia do deck:",
            height=100,
            placeholder="Ex: " + example_strategies[0]
        )
    
    with col2:
        st.markdown("### 💡 Exemplos")
        for i, example in enumerate(example_strategies):
            if st.button(f"Ex {i+1}", key=f"ex_{i}"):
                st.session_state['strategy'] = example
                st.experimental_rerun()
    
    # Aplicar exemplo se selecionado
    if 'strategy' in st.session_state:
        strategy = st.session_state['strategy']
    
    if st.button("🔍 Comparar Métodos", type="primary", disabled=not strategy):
        
        # Executar ambos os métodos
        col1, col2 = st.columns(2)
        
        with col1:
            with st.spinner("Buscando (Tradicional)..."):
                traditional_results = test_traditional_search(
                    strategy, factions, max_results
                )
        
        with col2:
            with st.spinner("Buscando (RAG)..."):
                rag_results = test_rag_search(
                    strategy, factions, max_results
                )
        
        # Mostrar resultados
        st.markdown("---")
        st.header("📊 Resultados da Comparação")
        
        # Métricas
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric(
                "Busca Tradicional",
                f"{traditional_results['count']} cartas",
                f"{traditional_results['time']:.2f}s"
            )
        
        with col2:
            st.metric(
                "Busca com RAG",
                f"{rag_results['count']} cartas",
                f"{rag_results['time']:.2f}s"
            )
        
        with col3:
            if rag_results['count'] > 0:
                speed_diff = ((traditional_results['time'] - rag_results['time']) / 
                            traditional_results['time'] * 100)
                st.metric(
                    "Diferença de Velocidade",
                    f"{abs(speed_diff):.1f}%",
                    "RAG mais rápido" if speed_diff > 0 else "Tradicional mais rápido"
                )
        
        # Resultados lado a lado
        st.markdown("### 🎴 Cartas Encontradas")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("🔤 Busca Tradicional")
            if 'error' in traditional_results:
                st.error(traditional_results['error'])
            else:
                st.caption(traditional_results.get('details', ''))
                
                for i, card in enumerate(traditional_results['cards'][:20]):
                    influence = card.influence_string or ""
                    if card.is_unit:
                        st.write(f"{i+1}. **{card.name}** - {card.cost}{influence} - {card.attack}/{card.health}")
                    else:
                        st.write(f"{i+1}. **{card.name}** - {card.cost}{influence}")
                
                if traditional_results['count'] > 20:
                    st.caption(f"... e mais {traditional_results['count'] - 20} cartas")
        
        with col2:
            st.subheader("🧠 Busca com RAG")
            if 'error' in rag_results:
                st.error(rag_results['error'])
            else:
                st.caption(rag_results.get('details', ''))
                
                for i, card in enumerate(rag_results['cards'][:20]):
                    influence = card.influence_string or ""
                    score = getattr(card, 'semantic_score', 0)
                    
                    if card.is_unit:
                        st.write(f"{i+1}. **{card.name}** - {card.cost}{influence} - {card.attack}/{card.health} (Score: {score:.2f})")
                    else:
                        st.write(f"{i+1}. **{card.name}** - {card.cost}{influence} (Score: {score:.2f})")
                
                if rag_results['count'] > 20:
                    st.caption(f"... e mais {rag_results['count'] - 20} cartas")
        
        # Análise de overlap
        if traditional_results['cards'] and rag_results['cards']:
            st.markdown("---")
            st.subheader("📈 Análise de Sobreposição")
            
            trad_names = {card.name for card in traditional_results['cards']}
            rag_names = {card.name for card in rag_results['cards']}
            
            overlap = trad_names.intersection(rag_names)
            only_trad = trad_names - rag_names
            only_rag = rag_names - trad_names
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Cartas em comum", len(overlap))
            with col2:
                st.metric("Apenas Tradicional", len(only_trad))
            with col3:
                st.metric("Apenas RAG", len(only_rag))
            
            # Mostrar diferenças interessantes
            if only_rag and len(only_rag) <= 10:
                st.markdown("#### 🆕 Cartas únicas encontradas pelo RAG:")
                rag_unique = [c for c in rag_results['cards'] if c.name in only_rag][:5]
                for card in rag_unique:
                    st.write(f"- **{card.name}**: {card.card_text[:100]}...")


if __name__ == "__main__":
    main()