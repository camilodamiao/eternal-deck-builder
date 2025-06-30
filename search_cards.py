"""Sistema de busca de cartas com paginação melhorada"""
import streamlit as st
import sys
import os
import math
from data.google_sheets_client import GoogleSheetsClient
from data.models import Card
from ui.components import display_card
from config.constants import FACTIONS, CARD_TYPES

st.set_page_config(page_title="Buscar Cartas - Eternal", layout="wide")

st.title("🔍 Buscar Cartas - Eternal")

# Inicializar session state
if 'view_mode' not in st.session_state:
    st.session_state.view_mode = "Detalhada"
if 'cards_per_page' not in st.session_state:
    st.session_state.cards_per_page = 20

# Botão para parar o servidor
col1, col2 = st.columns([6, 1])
with col2:
    if st.button("🛑 Parar Servidor", type="secondary"):
        st.success("Servidor parado! Pode fechar esta aba.")
        st.stop()
        os._exit(0)

st.markdown("---")

# Carregar cartas com cache
@st.cache_data(ttl=3600)
def load_all_cards():
    client = GoogleSheetsClient()
    return client.get_all_cards()

# Carregar todas as cartas
with st.spinner("Carregando base de cartas..."):
    all_cards = load_all_cards()

# Mostrar estatísticas
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Total de Cartas", len(all_cards))
with col2:
    unique_types = len(set(c.card_type for c in all_cards))
    st.metric("Tipos Diferentes", unique_types)
with col3:
    total_factions = len(set(f for c in all_cards for f in c.factions))
    st.metric("Facções", total_factions)

st.markdown("---")

# Sidebar com filtros
with st.sidebar:
    st.header("🎯 Filtros")
    
    # Busca por nome
    name_query = st.text_input("🔤 Nome da carta", placeholder="Ex: Torch")
    
    # Filtro por facção
    st.subheader("🎨 Facções")
    selected_factions = []
    cols = st.columns(2)
    for i, (key, faction) in enumerate(FACTIONS.items()):
        col = cols[i % 2]
        if col.checkbox(f"{faction['symbol']} {faction['name']}", key=f"search_{key}"):
            selected_factions.append(key)
    
    # Opções de filtro de facção
    require_all_factions = False
    exclude_multifaction = False
    
    if len(selected_factions) == 1:
        # Opção para excluir multifacção quando só uma facção selecionada
        exclude_multifaction = st.checkbox(
            "🎯 Apenas mono-facção",
            help="Excluir cartas multifacção, mostrar apenas cartas puras desta facção"
        )
    elif len(selected_factions) > 1:
        # Opção para requerer todas as facções
        st.info(f"📌 {len(selected_factions)} facções selecionadas")
        require_all_factions = st.checkbox(
            "🔗 Apenas cartas multifacção",
            help="Mostrar apenas cartas que tenham TODAS as facções selecionadas"
        )
    
    # Filtro por tipo
    st.subheader("📋 Tipo de Carta")
    available_types = sorted(set(c.card_type for c in all_cards))
    selected_types = st.multiselect("Selecione os tipos", available_types)
    
    # Filtro por custo
    st.subheader("💎 Custo")
    max_cost = st.slider("Custo máximo", 0, 12, 12)
    
    # Filtro por texto
    st.subheader("📝 Texto")
    text_contains = st.text_input("Texto contém", placeholder="Ex: Flying")
    
    # Configuração de visualização
    st.subheader("⚙️ Visualização")
    
    # Cartas por página
    cards_options = [10, 20, 50, 100]
    st.session_state.cards_per_page = st.selectbox(
        "Cartas por página",
        cards_options,
        index=cards_options.index(st.session_state.cards_per_page)
    )
    
    # Botão para limpar filtros
    if st.button("🔄 Limpar Filtros"):
        st.rerun()

# Aplicar filtros
if st.button("🔍 Buscar", type="primary"):
    client = GoogleSheetsClient()
    
    filtered_cards = client.search_cards(
        cards=all_cards,
        name_query=name_query,
        factions=selected_factions,
        card_types=selected_types,
        max_cost=max_cost if max_cost < 12 else None,
        text_contains=text_contains,
        require_all_factions=require_all_factions,
        exclude_multifaction=exclude_multifaction
    )
    
    st.session_state['search_results'] = filtered_cards
    st.session_state['search_performed'] = True
    st.session_state['current_page'] = 1

# Mostrar resultados
if st.session_state.get('search_performed', False):
    results = st.session_state.get('search_results', [])
    
    st.header(f"📊 Resultados ({len(results)} cartas)")
    
    # Informações sobre filtros aplicados
    if selected_factions:
        if len(selected_factions) == 1 and exclude_multifaction:
            st.info(f"🎯 Mostrando apenas cartas mono-{selected_factions[0]}")
        elif len(selected_factions) > 1 and require_all_factions:
            st.info(f"🔗 Mostrando apenas cartas com TODAS as facções: {', '.join(selected_factions)}")
        else:
            st.info(f"🎨 Mostrando cartas com: {', '.join(selected_factions)}")
    
    if results:
        # Configuração de paginação
        cards_per_page = st.session_state.cards_per_page
        total_pages = math.ceil(len(results) / cards_per_page)
        
        # Controles de paginação
        col1, col2, col3, col4, col5 = st.columns([1, 1, 2, 1, 1])
        
        with col1:
            if st.button("⏮️ Primeira"):
                st.session_state['current_page'] = 1
                st.rerun()
        
        with col2:
            if st.button("◀️ Anterior"):
                if st.session_state.get('current_page', 1) > 1:
                    st.session_state['current_page'] -= 1
                    st.rerun()
        
        with col3:
            current_page = st.selectbox(
                "Página",
                range(1, total_pages + 1),
                index=st.session_state.get('current_page', 1) - 1,
                key='page_selector'
            )
            if current_page != st.session_state.get('current_page', 1):
                st.session_state['current_page'] = current_page
                st.rerun()
        
        with col4:
            if st.button("Próxima ▶️"):
                if st.session_state.get('current_page', 1) < total_pages:
                    st.session_state['current_page'] += 1
                    st.rerun()
        
        with col5:
            if st.button("Última ⏭️"):
                st.session_state['current_page'] = total_pages
                st.rerun()
        
        # Calcular índices
        current_page = st.session_state.get('current_page', 1)
        start_idx = (current_page - 1) * cards_per_page
        end_idx = min(start_idx + cards_per_page, len(results))
        
        st.caption(f"Mostrando cartas {start_idx + 1} a {end_idx} de {len(results)}")
        
        # Modo de visualização (persistente)
        view_col1, view_col2 = st.columns([1, 5])
        with view_col1:
            view_mode = st.radio(
                "Modo",
                ["Detalhada", "Compacta"],
                index=0 if st.session_state.view_mode == "Detalhada" else 1,
                key="view_mode_radio"
            )
            if view_mode != st.session_state.view_mode:
                st.session_state.view_mode = view_mode
                st.rerun()
        
        # Mostrar cartas
        page_results = results[start_idx:end_idx]
        
        if st.session_state.view_mode == "Detalhada":
            for card in page_results:
                with st.container():
                    display_card(card)
                    st.divider()
        else:  # Compacta
            cols = st.columns(3)
            for i, card in enumerate(page_results):
                with cols[i % 3]:
                    st.write(f"**{card.name}**")
                    st.caption(f"{card.cost} - {card.card_type}")
                    if card.image_url:
                        st.image(card.image_url, width=150)
                    st.divider()
    else:
        st.warning("Nenhuma carta encontrada com esses filtros")
else:
    st.info("👆 Configure os filtros e clique em Buscar")

st.markdown("---")
st.caption("💡 Use os controles de paginação e visualização para navegar pelos resultados")