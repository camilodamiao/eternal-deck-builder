"""
Eternal Deck Builder - Aplicação Principal
"""
import streamlit as st
import pandas as pd
from config.constants import FACTIONS, CARD_TYPES, DECK_RULES

# Configuração da página
st.set_page_config(
    page_title="Eternal Deck Builder AI",
    page_icon="🎴",
    layout="wide"
)

# CSS customizado
st.markdown("""
    <style>
    .main {
        padding-top: 2rem;
    }
    .stButton>button {
        width: 100%;
    }
    </style>
""", unsafe_allow_html=True)

# Título principal
st.title("🎴 Eternal Deck Builder AI")
st.markdown("---")

# Sidebar
with st.sidebar:
    st.header("⚙️ Configurações")
    
    # Seleção de facções
    st.subheader("Facções")
    selected_factions = []
    cols = st.columns(2)
    for i, (key, faction) in enumerate(FACTIONS.items()):
        col = cols[i % 2]
        if col.checkbox(f"{faction['symbol']} {faction['name']}", key=f"faction_{key}"):
            selected_factions.append(key)
    
    # Tipo de deck
    st.subheader("Arquétipo")
    archetype = st.selectbox(
        "Escolha o estilo do deck",
        ["Aggro", "Midrange", "Control", "Combo", "Automático"]
    )
    
    # Opções adicionais
    st.subheader("Opções")
    include_market = st.checkbox("Incluir Mercado", value=True)
    budget_mode = st.checkbox("Modo Budget", value=False)

# Área principal
col1, col2 = st.columns([2, 1])

with col1:
    st.header("📝 Estratégia do Deck")
    
    # Campo de entrada para estratégia
    strategy = st.text_area(
        "Descreva a estratégia desejada para o deck:",
        placeholder="Ex: Quero um deck agressivo com unidades voadoras que causem dano direto ao oponente...",
        height=150
    )
    
    # Botão para gerar deck
    if st.button("🎯 Gerar Deck", type="primary"):
        if not strategy:
            st.error("Por favor, descreva uma estratégia para o deck!")
        elif not selected_factions:
            st.error("Por favor, selecione pelo menos uma facção!")
        else:
            with st.spinner("🤖 Analisando estratégia e construindo deck..."):
                # Aqui vamos integrar com o LangChain/OpenAI
                st.success("✅ Deck gerado com sucesso!")
                
                # Placeholder para o deck
                st.subheader("🎴 Deck Sugerido: 'Nome do Deck'")
                
                # Tabs para diferentes visualizações
                tab1, tab2, tab3, tab4 = st.tabs(["📋 Lista", "📊 Análise", "💡 Estratégia", "🔄 Simulação"])
                
                with tab1:
                    st.write("Lista de cartas virá aqui...")
                
                with tab2:
                    st.write("Gráficos e análises virão aqui...")
                
                with tab3:
                    st.write("Explicação da estratégia virá aqui...")
                
                with tab4:
                    st.write("Simulações virão aqui...")

with col2:
    st.header("📚 Informações")
    
    # Regras do deck
    with st.expander("📏 Regras de Construção"):
        st.write(f"**Tamanho:** {DECK_RULES['MIN_CARDS']}-{DECK_RULES['MAX_CARDS']} cartas")
        st.write(f"**Power mínimo:** {DECK_RULES['MIN_POWER_RATIO']*100:.0f}% do deck")
        st.write(f"**Cópias máximas:** {DECK_RULES['MAX_COPIES']} por carta")
        st.write(f"**Mercado:** até {DECK_RULES['MARKET_SIZE']} cartas")
    
    # Facções selecionadas
    if selected_factions:
        st.subheader("Facções Selecionadas")
        for faction in selected_factions:
            f = FACTIONS[faction]
            st.write(f"{f['symbol']} **{f['name']}**")
    
    # Status da conexão
    with st.expander("🔌 Status da Conexão"):
        # Testar conexão com Google Sheets
        try:
            from test_connection import test_google_sheets_connection
            if test_google_sheets_connection():
                st.success("✅ Google Sheets conectado")
            else:
                st.error("❌ Erro na conexão com Google Sheets")
        except:
            st.warning("⚠️ Módulo de teste não encontrado")

# Footer
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center'>
        <p>Desenvolvido com ❤️ para a comunidade Eternal Card Game</p>
    </div>
    """, 
    unsafe_allow_html=True
)