"""Interface do Deck Builder com IA"""
import streamlit as st
from agents.deck_builder_agent import DeckBuilderAgent
from core.deck_validator import DeckValidator

st.set_page_config(page_title="Deck Builder AI - Eternal", layout="wide")

st.title("🤖 Deck Builder AI - Eternal")
st.markdown("---")

# Inicializar agente
@st.cache_resource
def get_agent():
    return DeckBuilderAgent()

agent = get_agent()
validator = DeckValidator()

# Sidebar
with st.sidebar:
    st.header("⚙️ Configurações")
    
    deck_format = st.selectbox("Formato", ["Throne", "Expedition"])
    detailed_mode = st.checkbox("Modo Detalhado", help="Incluir explicações detalhadas")
    
    st.markdown("---")
    st.caption("💡 Exemplos de estratégias:")
    st.caption("• Deck aggro Fire com muita queima direta")
    st.caption("• Control Justice/Shadow com remoções")
    st.caption("• Midrange Time com unidades grandes")

# Área principal
st.header("📝 Descreva sua Estratégia")

strategy = st.text_area(
    "O que você quer que o deck faça?",
    placeholder="Ex: Quero um deck agressivo Fire/Justice que pressione desde o início com unidades pequenas e eficientes, com queima direta para finalizar...",
    height=150
)

col1, col2 = st.columns([1, 4])
with col1:
    generate_button = st.button("🎯 Gerar Deck", type="primary", use_container_width=True)

# Gerar deck
if generate_button and strategy:
    with st.spinner("🤖 Construindo deck... (pode levar 30-60 segundos)"):
        try:
            result = agent.build_deck(strategy, detailed=detailed_mode)
            
            # Salvar no session state
            st.session_state['current_deck'] = result['deck']
            st.session_state['deck_generated'] = True
            
        except Exception as e:
            st.error(f"Erro ao gerar deck: {str(e)}")

# Mostrar deck gerado
if st.session_state.get('deck_generated', False):
    deck_text = st.session_state.get('current_deck', '')
    
    st.markdown("---")
    st.header("🎴 Deck Gerado")
    
    # Validar deck
    is_valid, errors = validator.validate_text_deck(deck_text)
    
    if is_valid:
        st.success("✅ Deck válido!")
    else:
        st.error("❌ Deck com problemas:")
        for error in errors:
            st.warning(error)
    
    # Mostrar deck
    st.text_area("Deck:", deck_text, height=400)
    
    # Botões de ação
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("📋 Copiar Deck"):
            st.write("Use Ctrl+A e Ctrl+C na caixa acima")
    
    with col2:
        if st.button("💾 Exportar"):
            st.download_button(
                label="Baixar deck.txt",
                data=deck_text,
                file_name="eternal_deck.txt",
                mime="text/plain"
            )
    
    # Chat follow-up
    st.markdown("---")
    st.subheader("💬 Perguntas sobre o deck")
    
    question = st.text_input("Tem alguma dúvida sobre o deck?", placeholder="Ex: Por que escolheu essa carta?")
    
    if st.button("Perguntar") and question:
        with st.spinner("Pensando..."):
            answer = agent.ask_followup(question)
            st.write(answer)

else:
    st.info("👆 Descreva a estratégia desejada e clique em 'Gerar Deck'")