"""Teste simples de geração de deck com GPT-4"""
import streamlit as st
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
from config.settings import settings
from data.google_sheets_client import GoogleSheetsClient

st.set_page_config(page_title="Teste AI Simples", layout="wide")
st.title("🧪 Teste Simples - Deck Builder AI")

# Carregar algumas cartas de exemplo
@st.cache_data
def load_sample_cards():
    client = GoogleSheetsClient()
    all_cards = client.get_all_cards()
    
    # Separar por tipo e custo
    sample = {
        "units_1": [c for c in all_cards if c.card_type == "Unit" and c.cost == 1][:10],
        "units_2": [c for c in all_cards if c.card_type == "Unit" and c.cost == 2][:10],
        "units_3": [c for c in all_cards if c.card_type == "Unit" and c.cost == 3][:10],
        "spells": [c for c in all_cards if c.card_type == "Spell" and c.cost <= 3][:10],
        "powers": [c for c in all_cards if c.card_type == "Power"][:20]
    }
    
    return sample, all_cards

# Interface
strategy = st.text_area("Estratégia desejada:", value="Deck aggro mono Fire")

model = st.selectbox("Modelo:", ["gpt-3.5-turbo", "gpt-4", "gpt-4-turbo-preview"])

if st.button("Gerar Deck"):
    with st.spinner("Carregando cartas..."):
        sample, all_cards = load_sample_cards()
        
    # Preparar lista de cartas disponíveis
    cards_text = "CARTAS DISPONÍVEIS:\n\n"
    
    cards_text += "Units de 1 custo:\n"
    for c in sample["units_1"]:
        cards_text += f"- {c.name} ({c.cost} custo, {c.attack}/{c.health}, {'/'.join(c.factions)})\n"
    
    cards_text += "\nUnits de 2 custo:\n"
    for c in sample["units_2"]:
        cards_text += f"- {c.name} ({c.cost} custo, {c.attack}/{c.health}, {'/'.join(c.factions)})\n"
    
    cards_text += "\nSpells:\n"
    for c in sample["spells"]:
        cards_text += f"- {c.name} ({c.cost} custo, {c.card_type}, {'/'.join(c.factions)})\n"
    
    cards_text += "\nPower cards:\n"
    for c in sample["powers"][:10]:
        cards_text += f"- {c.name}\n"
    
    # Criar prompt
    prompt = f"""Você é um expert em Eternal Card Game. 

REGRAS:
- Deck deve ter exatamente 75 cartas
- Mínimo 25 devem ser power cards (1/3 do deck)
- Máximo 4 cópias de cada carta (exceto Sigils básicos)

{cards_text}

Estratégia solicitada: {strategy}

Por favor, construa um deck de 75 cartas no formato:
4 Nome da Carta
3 Outra Carta
...

Inclua:
1. Lista completa do deck (75 cartas)
2. Breve explicação da estratégia (2-3 linhas)
3. Como jogar (3-4 pontos)
"""
    
    # Gerar com GPT
    with st.spinner(f"Gerando deck com {model}..."):
        llm = ChatOpenAI(
            model=model,
            temperature=0.3,
            api_key=settings.OPENAI_API_KEY
        )
        
        response = llm.invoke(prompt)
        
    st.markdown("### Resposta do AI:")
    st.text(response.content)
    
    # Mostrar tokens usados (estimativa)
    tokens_estimate = len(prompt.split()) + len(response.content.split())
    st.caption(f"Tokens estimados: ~{tokens_estimate}")
    