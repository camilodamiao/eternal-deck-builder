"""Página de teste para visualizar cartas do Google Sheets"""
import streamlit as st
from data.google_sheets_client import GoogleSheetsClient
from data.models import Card, Deck, DeckCard
from ui.components import display_card, display_deck_list, display_deck_stats

st.set_page_config(page_title="Visualizador de Cartas", layout="wide")

st.title("🎴 Visualizador de Cartas - Eternal")
st.markdown("---")

# Inicializar cliente
@st.cache_resource
def get_client():
    return GoogleSheetsClient()

client = get_client()

# Sidebar para filtros
with st.sidebar:
    st.header("🔍 Filtros")
    
    # Quantidade de cartas para mostrar
    num_cards = st.slider("Número de cartas", 5, 50, 20)
    
    # Botão para recarregar
    if st.button("🔄 Recarregar Cartas"):
        st.cache_resource.clear()
        st.rerun()

# Buscar cartas
with st.spinner("Carregando cartas..."):
    raw_cards = client.get_sample_cards(limit=num_cards)
    
    # Parsear cartas
    cards = []
    for raw in raw_cards:
        card = client.parse_card(raw)
        if card:
            cards.append(card)

# Mostrar estatísticas
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Total de Cartas", len(raw_cards))
with col2:
    st.metric("Cartas Parseadas", len(cards))
with col3:
    success_rate = (len(cards) / len(raw_cards) * 100) if raw_cards else 0
    st.metric("Taxa de Sucesso", f"{success_rate:.1f}%")

# Tabs para diferentes visualizações
tab1, tab2, tab3 = st.tabs(["📋 Lista de Cartas", "🎮 Deck de Teste", "📊 Dados Brutos"])

with tab1:
    st.subheader("Cartas Carregadas")
    
    if cards:
        # Mostrar cada carta
        for i, card in enumerate(cards):
            with st.container():
                display_card(card)
                if i < len(cards) - 1:
                    st.divider()
    else:
        st.warning("Nenhuma carta foi parseada com sucesso")

with tab2:
    st.subheader("Deck de Teste")
    
    if cards:
        # Criar um deck de teste com as primeiras cartas
        test_deck = Deck(
            name="Deck de Teste",
            main_deck=[]
        )
        
        # Adicionar algumas cartas ao deck
        for card in cards[:10]:  # Primeiras 10 cartas
            if card.is_power:
                # Mais cópias de power
                test_deck.main_deck.append(DeckCard(card=card, quantity=4))
            else:
                # 2 cópias de outras cartas
                test_deck.main_deck.append(DeckCard(card=card, quantity=2))
        
        # Mostrar estatísticas
        display_deck_stats(test_deck)
        
        # Mostrar lista
        st.markdown("---")
        display_deck_list(test_deck)
    else:
        st.warning("Precisa de cartas para criar um deck de teste")

with tab3:
    st.subheader("Dados Brutos (Primeira Carta)")
    
    if raw_cards:
        # Mostrar dados da primeira carta
        first = raw_cards[0]
        
        # Criar duas colunas
        col1, col2 = st.columns(2)
        
        # Dividir os campos
        fields = list(first.items())
        mid = len(fields) // 2
        
        with col1:
            for key, value in fields[:mid]:
                st.text(f"{key}: {value}")
        
        with col2:
            for key, value in fields[mid:]:
                st.text(f"{key}: {value}")
    else:
        st.warning("Nenhum dado encontrado")