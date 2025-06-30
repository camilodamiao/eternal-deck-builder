"""Deck Builder AI v2 - Com modelos atualizados"""
import streamlit as st
from langchain_openai import ChatOpenAI
from data.google_sheets_client import GoogleSheetsClient
from core.deck_validator import DeckValidator
from config.settings import settings
import json

st.set_page_config(page_title="Deck Builder AI - Eternal", layout="wide")
st.title("🤖 Deck Builder AI - Eternal")
st.markdown("---")

# Configurações dos modelos
MODEL_CONFIGS = {
    "gpt-4o": {
        "name": "GPT-4o (Mais recente e capaz)",
        "supports_temperature": True,
        "supports_stop": True,
        "cost_per_1k": 0.005
    },
    "gpt-4o-mini": {
        "name": "GPT-4o Mini (Rápido e barato)",
        "supports_temperature": True,
        "supports_stop": True,
        "cost_per_1k": 0.00015
    },
    "o4-mini": {
        "name": "O4 Mini (Raciocínio avançado)",
        "supports_temperature": False,
        "supports_stop": False,
        "cost_per_1k": 0.003
    },
    "gpt-4-turbo": {
        "name": "GPT-4 Turbo (Anterior)",
        "supports_temperature": True,
        "supports_stop": True,
        "cost_per_1k": 0.01
    },
    "gpt-3.5-turbo": {
        "name": "GPT-3.5 Turbo (Mais barato)",
        "supports_temperature": True,
        "supports_stop": True,
        "cost_per_1k": 0.0005
    }
}

def create_llm(model_key):
    """Cria o LLM com as configurações corretas para cada modelo"""
    config = MODEL_CONFIGS[model_key]
    
    # Para o4-mini, configuração especial
    if model_key == "o4-mini":
        return ChatOpenAI(
            model="o4-mini",
            api_key=settings.OPENAI_API_KEY,
            # NÃO incluir temperature nem stop
        )
    else:
        # Para outros modelos
        return ChatOpenAI(
            model=model_key,
            api_key=settings.OPENAI_API_KEY,
            temperature=0.3 if config["supports_temperature"] else None
        )

# Inicializar
validator = DeckValidator()

# Cache de cartas
@st.cache_data(ttl=3600)
def load_all_cards():
    client = GoogleSheetsClient()
    return client.get_all_cards()

# Função para preparar contexto de cartas
def prepare_cards_context(cards, strategy):
    """Prepara uma seleção relevante de cartas para o AI"""
    
    # Identificar facções mencionadas
    factions_mentioned = []
    faction_keywords = {
        "FIRE": ["fire", "burn", "aggro", "red", "torch", "oni"],
        "TIME": ["time", "ramp", "big", "yellow", "sandstorm", "sentinel"],
        "JUSTICE": ["justice", "armor", "weapons", "green", "valkyrie", "enforcer"],
        "PRIMAL": ["primal", "spell", "blue", "control", "lightning", "wisdom"],
        "SHADOW": ["shadow", "kill", "void", "purple", "black", "umbren", "stonescar"]
    }
    
    strategy_lower = strategy.lower()
    
    # Detectar facções com base em keywords
    for faction, keywords in faction_keywords.items():
        if any(keyword in strategy_lower for keyword in keywords):
            factions_mentioned.append(faction)
    
    # Se nenhuma facção identificada, incluir todas
    if not factions_mentioned:
        factions_mentioned = list(faction_keywords.keys())
    
    # Detectar arquétipo baseado em keywords
    archetype_keywords = {
        'aggro': ['aggro', 'fast', 'rush', 'burn', 'quick', 'aggressive'],
        'control': ['control', 'slow', 'removal', 'board clear', 'late game'],
        'midrange': ['midrange', 'balanced', 'curve', 'tempo'],
        'combo': ['combo', 'synergy', 'engine', 'infinite']
    }
    
    detected_archetype = 'midrange'  # default
    for arch, keywords in archetype_keywords.items():
        if any(keyword in strategy_lower for keyword in keywords):
            detected_archetype = arch
            break
    
    # Filtrar cartas relevantes com priorização
    relevant_cards = {
        "units_low": [],
        "units_mid": [],
        "units_high": [],
        "spells": [],
        "weapons": [],
        "powers": [],
        "relics": [],
        "sites": []
    }
    
    # Scoring para relevância
    def calculate_relevance(card):
        score = 0
        
        # Facção correta = +10 pontos
        if any(f in card.factions for f in factions_mentioned):
            score += 10
        
        # Custo apropriado para arquétipo
        if detected_archetype == 'aggro' and card.cost <= 3:
            score += 5
        elif detected_archetype == 'control' and card.cost >= 4:
            score += 5
        elif detected_archetype == 'midrange' and 2 <= card.cost <= 5:
            score += 5
        
        # Keywords relevantes no texto
        relevant_keywords = {
            'aggro': ['charge', 'warcry', 'quickdraw', 'overwhelm'],
            'control': ['endurance', 'aegis', 'silence', 'kill', 'destroy'],
            'midrange': ['summon', 'bond', 'ally', 'empower'],
            'combo': ['echo', 'destiny', 'revenge', 'amplify']
        }
        
        if card.text:
            for keyword in relevant_keywords.get(detected_archetype, []):
                if keyword.lower() in card.text.lower():
                    score += 3
        
        return score
    
    # Classificar e pontuar cartas
    scored_cards = [(card, calculate_relevance(card)) for card in cards]
    scored_cards.sort(key=lambda x: x[1], reverse=True)
    
    # Distribuir cartas nas categorias
    for card, score in scored_cards:
        # Pular cartas com score muito baixo (não relevantes)
        if score < 5 and len(scored_cards) > 100:
            continue
        
        if card.card_type == "Unit":
            if card.cost <= 2:
                if len(relevant_cards["units_low"]) < 25:
                    relevant_cards["units_low"].append(card)
            elif card.cost <= 4:
                if len(relevant_cards["units_mid"]) < 20:
                    relevant_cards["units_mid"].append(card)
            else:
                if len(relevant_cards["units_high"]) < 15:
                    relevant_cards["units_high"].append(card)
        elif card.card_type == "Spell":
            if len(relevant_cards["spells"]) < 20:
                relevant_cards["spells"].append(card)
        elif card.card_type == "Weapon":
            if len(relevant_cards["weapons"]) < 15:
                relevant_cards["weapons"].append(card)
        elif card.card_type == "Power":
            if len(relevant_cards["powers"]) < 30:
                relevant_cards["powers"].append(card)
        elif card.card_type == "Relic":
            if len(relevant_cards["relics"]) < 10:
                relevant_cards["relics"].append(card)
        elif card.card_type == "Site":
            if len(relevant_cards["sites"]) < 5:
                relevant_cards["sites"].append(card)
    
    # Formatar texto de forma mais clara
    context = f"CARTAS RELEVANTES PARA {', '.join(factions_mentioned)} {detected_archetype.upper()}:\n\n"
    
    # Adicionar estatísticas rápidas
    total_cards = sum(len(cards) for cards in relevant_cards.values())
    context += f"(Total: {total_cards} cartas selecionadas de {len(cards)} disponíveis)\n\n"
    
    if relevant_cards["units_low"]:
        context += "=== EARLY GAME (1-2 custo) ===\n"
        for c in relevant_cards["units_low"]:
            context += f"• {c.name} ({c.cost} custo, {c.attack}/{c.health}"
            if c.text:
                # Destacar keywords importantes
                important_text = c.text[:50]
                for keyword in ['Charge', 'Warcry', 'Flying', 'Quickdraw', 'Aegis']:
                    if keyword in c.text:
                        important_text = f"**{keyword}**, " + important_text
                context += f") - {important_text}..."
            else:
                context += ")"
            context += "\n"
    
    if relevant_cards["units_mid"]:
        context += "\n=== MID GAME (3-4 custo) ===\n"
        for c in relevant_cards["units_mid"]:
            context += f"• {c.name} ({c.cost} custo, {c.attack}/{c.health})\n"
    
    if relevant_cards["units_high"]:
        context += "\n=== LATE GAME (5+ custo) ===\n"
        for c in relevant_cards["units_high"][:10]:
            context += f"• {c.name} ({c.cost} custo, {c.attack}/{c.health})\n"
    
    if relevant_cards["spells"]:
        context += "\n=== SPELLS ===\n"
        # Agrupar por tipo de efeito
        removal_spells = [c for c in relevant_cards["spells"] if any(word in c.text.lower() for word in ['kill', 'destroy', 'damage', 'deal'])]
        draw_spells = [c for c in relevant_cards["spells"] if 'draw' in c.text.lower()]
        other_spells = [c for c in relevant_cards["spells"] if c not in removal_spells and c not in draw_spells]
        
        if removal_spells:
            context += "Remoção:\n"
            for c in removal_spells[:7]:
                context += f"  • {c.name} ({c.cost}) - {c.text[:40]}...\n"
        
        if draw_spells:
            context += "Card Draw:\n"
            for c in draw_spells[:5]:
                context += f"  • {c.name} ({c.cost}) - {c.text[:40]}...\n"
        
        if other_spells:
            context += "Outros:\n"
            for c in other_spells[:5]:
                context += f"  • {c.name} ({c.cost})\n"
    
    if relevant_cards["weapons"]:
        context += "\n=== WEAPONS ===\n"
        for c in relevant_cards["weapons"][:10]:
            context += f"• {c.name} ({c.cost} custo)\n"
    
    if relevant_cards["powers"]:
        context += "\n=== POWER CARDS ===\n"
        # Separar por tipo
        sigils = [c for c in relevant_cards["powers"] if "Sigil" in c.name]
        dual_powers = [c for c in relevant_cards["powers"] if len(c.factions) > 1]
        utility_powers = [c for c in relevant_cards["powers"] if c not in sigils and c not in dual_powers]
        
        if sigils:
            context += "Sigils:\n"
            for c in sigils:
                context += f"  • {c.name}\n"
        
        if dual_powers:
            context += "Dual Powers:\n"
            for c in dual_powers[:10]:
                context += f"  • {c.name} ({'/'.join(c.factions)})\n"
        
        if utility_powers:
            context += "Utility Powers:\n"
            for c in utility_powers[:5]:
                context += f"  • {c.name}\n"
    
    return context

# Função para gerar deck
def generate_deck(strategy, cards, model_key="gpt-4o", detailed=False):
    """Gera um deck usando o AI"""
    
    # Preparar contexto
    cards_context = prepare_cards_context(cards, strategy)
    
    # Ajustar prompt baseado no modelo
    if model_key == "o4-mini":
        # Modelo o4-mini prefere instruções mais diretas
        prompt = f"""Construa um deck competitivo de Eternal Card Game.

REQUISITOS:
- Exatamente 75 cartas total
- Mínimo 25 powers (1/3 do deck)
- Máximo 4 cópias por carta (exceto Sigils)
- Use apenas cartas da lista fornecida

{cards_context}

ESTRATÉGIA: {strategy}

Responda com:
1. Lista do deck (formato: "4 Nome da Carta")
2. Estratégia principal (2-3 linhas)
3. Guia de jogo (4-5 pontos)
"""
    else:
        # Modelos GPT tradicionais
        prompt = f"""Você é um expert em Eternal Card Game, especialista em construir decks competitivos.

REGRAS OBRIGATÓRIAS:
1. O deck deve ter EXATAMENTE 75 cartas
2. MÍNIMO 25 cartas devem ser Power cards (Sigils, Banners, etc)
3. Máximo 4 cópias de cada carta (exceto Sigils básicos que podem ter mais)
4. Use APENAS cartas da lista fornecida abaixo
5. O formato de saída deve ser: "4 Nome Exato da Carta"

{cards_context}

ESTRATÉGIA SOLICITADA: {strategy}

{"MODO DETALHADO: Explique cada escolha importante." if detailed else ""}

Por favor, construa um deck otimizado seguindo estas instruções:

FORMATO DE RESPOSTA OBRIGATÓRIO:
=== DECK (75 cartas) ===
4 Nome da Carta
3 Outra Carta
(liste todas as 75 cartas)

=== ESTRATÉGIA ===
(2-3 linhas explicando o plano central)

=== COMO JOGAR ===
(4-5 pontos sobre pilotagem)

{"=== EXPLICAÇÕES DETALHADAS ===\n(justifique as escolhas principais)" if detailed else ""}
"""
    
    # Gerar resposta
    llm = create_llm(model_key)
    response = llm.invoke(prompt)
    
    # Calcular custo estimado
    tokens = len(prompt.split()) + len(response.content.split())
    cost = tokens * MODEL_CONFIGS[model_key]["cost_per_1k"] / 1000
    
    return response.content, tokens, cost

# Sidebar
with st.sidebar:
    st.header("⚙️ Configurações")
    
    deck_format = st.selectbox("Formato", ["Throne", "Expedition"])
    
    # Seletor de modelo com descrições
    model_options = list(MODEL_CONFIGS.keys())
    model_names = [f"{k} - {v['name']}" for k, v in MODEL_CONFIGS.items()]
    
    selected_index = st.selectbox(
        "Modelo AI",
        range(len(model_options)),
        format_func=lambda x: model_names[x],
        index=0  # Default para gpt-4o
    )
    
    selected_model = model_options[selected_index]
    
    # Mostrar informações do modelo
    model_info = MODEL_CONFIGS[selected_model]
    st.caption(f"💰 ~${model_info['cost_per_1k']:.4f}/1k tokens")
    
    detailed_mode = st.checkbox("Modo Detalhado", help="Incluir explicações detalhadas")
    
    st.markdown("---")
    st.caption("💡 Exemplos de estratégias:")
    st.caption("• Deck aggro Fire com burn")
    st.caption("• Control Justice/Shadow")
    st.caption("• Midrange Time/Primal")
    st.caption("• Combo Xenan reanimator")

# Área principal
st.header("📝 Descreva sua Estratégia")

strategy = st.text_area(
    "O que você quer que o deck faça?",
    placeholder="Ex: Quero um deck aggro Fire/Justice focado em unidades pequenas eficientes e burn direto...",
    height=150
)

col1, col2, col3 = st.columns([1, 1, 3])
with col1:
    generate_button = st.button("🎯 Gerar Deck", type="primary", use_container_width=True)
with col2:
    if st.button("🔄 Limpar", use_container_width=True):
        st.session_state.clear()
        st.rerun()

# Gerar deck
if generate_button and strategy:
    with st.spinner(f"🤖 Gerando deck com {selected_model}..."):
        try:
            # Carregar cartas
            all_cards = load_all_cards()
            
            # Gerar deck
            result, tokens, cost = generate_deck(
                strategy, 
                all_cards, 
                model_key=selected_model,
                detailed=detailed_mode
            )
            
            # Salvar no session state
            st.session_state['current_deck'] = result
            st.session_state['deck_generated'] = True
            st.session_state['tokens_used'] = tokens
            st.session_state['cost_estimate'] = cost
            st.session_state['model_used'] = selected_model
            
        except Exception as e:
            st.error(f"Erro ao gerar deck: {str(e)}")
            if "o4" in selected_model and "stop" in str(e):
                st.info("💡 O modelo O4 tem limitações específicas. Tente com GPT-4o ou GPT-4o-mini.")

# Mostrar deck gerado
if st.session_state.get('deck_generated', False):
    deck_text = st.session_state.get('current_deck', '')
    
    st.markdown("---")
    st.header("🎴 Deck Gerado")
    
    # Mostrar métricas
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Modelo", st.session_state.get('model_used', 'N/A'))
    with col2:
        tokens = st.session_state.get('tokens_used', 0)
        st.metric("Tokens", f"{tokens:,}")
    with col3:
        cost = st.session_state.get('cost_estimate', 0)
        st.metric("Custo Estimado", f"${cost:.4f}")
    
    # Tentar extrair apenas a lista do deck para validação
    deck_lines = []
    in_deck_section = False
    for line in deck_text.split('\n'):
        if 'DECK' in line.upper() and any(x in line for x in ['75', '===', '---']):
            in_deck_section = True
            continue
        if in_deck_section and line.strip():
            if any(word in line.upper() for word in ['ESTRATÉGIA', 'COMO JOGAR', 'STRATEGY', '===']):
                break
            if line.strip() and line[0].isdigit():
                deck_lines.append(line.strip())
    
    # Validar deck
    if deck_lines:
        deck_for_validation = '\n'.join(deck_lines)
        is_valid, errors = validator.validate_text_deck(deck_for_validation)
        
        if is_valid:
            st.success("✅ Deck válido!")
        else:
            st.error("❌ Deck com problemas:")
            for error in errors:
                st.warning(error)
    
    # Mostrar resposta completa
    st.text_area("Resposta Completa:", deck_text, height=500)
    
    # Botões de ação
    col1, col2, col3 = st.columns(3)
    with col1:
        st.download_button(
            label="💾 Baixar Deck",
            data=deck_text,
            file_name="eternal_deck.txt",
            mime="text/plain"
        )

    with col2:
    # NOVO: Botão de exportação
        if st.button("📤 Exportar para o Jogo"):
            from utils.deck_exporter import DeckExporter
            exporter = DeckExporter()
        
        with st.spinner("Convertendo para formato do jogo..."):
            try:
                exported_deck = exporter.export_deck_text(deck_text, deck_format)
                
                # Mostrar em uma text area para copiar
                st.text_area(
                    "Copie este texto para importar no Eternal:",
                    exported_deck,
                    height=300,
                    key="exported_deck"
                )
                
                # Botão para baixar também
                st.download_button(
                    label="💾 Baixar Deck Formatado",
                    data=exported_deck,
                    file_name=f"eternal_deck_{deck_format.lower()}.txt",
                    mime="text/plain",
                    key="download_formatted"
                )
            except Exception as e:
                st.error(f"Erro ao exportar: {str(e)}")    
    
    # Chat follow-up
    st.markdown("---")
    st.subheader("💬 Perguntas sobre o deck")
    
    question = st.text_input("Tem alguma dúvida sobre o deck?", key="followup_question")
    
    if st.button("Perguntar", key="ask_button") and question:
        with st.spinner("Pensando..."):
            try:
                # Criar contexto com o deck atual
                context = f"Sobre o deck gerado:\n\n{deck_text}\n\nPergunta: {question}"
                
                llm = create_llm(selected_model)
                answer = llm.invoke(context)
                
                st.write(answer.content)
                
                # Calcular custo da pergunta
                tokens_q = len(context.split()) + len(answer.content.split())
                cost_q = tokens_q * MODEL_CONFIGS[selected_model]["cost_per_1k"] / 1000
                st.caption(f"💰 Custo da pergunta: ${cost_q:.4f}")
                
            except Exception as e:
                st.error(f"Erro: {str(e)}")

else:
    st.info("👆 Descreva a estratégia desejada e clique em 'Gerar Deck'")

# Footer
st.markdown("---")
st.caption("💡 Dica: GPT-4o oferece melhor qualidade, GPT-4o-mini é mais econômico, O4-mini é melhor para raciocínio complexo")