"""Deck Builder AI v3 - Com modelos atualizados"""
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
    "o1-pro": {
        "name": "O1 Pro (Mais avançado)",
        "supports_temperature": False,
        "supports_stop": False,
        "cost_per_1k": 0.015
    },
    "gpt-4.5-preview-2025-02-27": {
        "name": "GPT-4.5 Preview (Experimental)",
        "supports_temperature": True,
        "supports_stop": True,
        "cost_per_1k": 0.01
    },
    "gpt-4.1": {
        "name": "GPT-4.1 (Versão estável)",
        "supports_temperature": True,
        "supports_stop": True,
        "cost_per_1k": 0.008
    },
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
    
    # Para modelos o1/o4, configuração especial
    if model_key in ["o1-pro", "o4-mini"]:
        return ChatOpenAI(
            model=model_key,
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

# Função para preparar contexto de cartas ATUALIZADA
def prepare_cards_context(cards, strategy):
    """Prepara uma seleção relevante de cartas para o AI com dados completos"""
    
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
    
    # Função auxiliar para formatar influência
    def format_influence(card):
        """Formata influência no estilo {F}{T}{J}"""
        if not card.influence:
            return str(card.cost)
        
        influence_str = str(card.cost)
        influence_map = {'FIRE': 'F', 'TIME': 'T', 'JUSTICE': 'J', 'PRIMAL': 'P', 'SHADOW': 'S'}
        
        for faction, count in sorted(card.influence.items()):
            symbol = influence_map.get(faction, '?')
            influence_str += '{' + symbol + '}' * count
            
        return influence_str
    
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
    
    # Formatar texto com dados COMPLETOS
    context = f"CARTAS DISPONÍVEIS PARA {', '.join(factions_mentioned)} {detected_archetype.upper()}:\n\n"
    context += "IMPORTANTE: Use EXATAMENTE as informações fornecidas abaixo. NÃO invente raridades ou influências.\n\n"
    
    # Adicionar estatísticas rápidas
    total_cards = sum(len(cards) for cards in relevant_cards.values())
    context += f"(Total: {total_cards} cartas selecionadas de {len(cards)} disponíveis)\n\n"
    
    if relevant_cards["units_low"]:
        context += "=== EARLY GAME (1-2 custo) ===\n"
        for c in relevant_cards["units_low"]:
            influence = format_influence(c)
            context += f"• {c.name} | {influence} | {c.attack}/{c.health} | {c.rarity}"
            if c.text:
                # Destacar keywords importantes
                important_keywords = ['Charge', 'Warcry', 'Flying', 'Quickdraw', 'Aegis', 'Deadly', 'Overwhelm']
                keywords_found = [kw for kw in important_keywords if kw in c.text]
                if keywords_found:
                    context += f" | {', '.join(keywords_found)}"
            context += "\n"
    
    if relevant_cards["units_mid"]:
        context += "\n=== MID GAME (3-4 custo) ===\n"
        for c in relevant_cards["units_mid"]:
            influence = format_influence(c)
            context += f"• {c.name} | {influence} | {c.attack}/{c.health} | {c.rarity}\n"
    
    if relevant_cards["units_high"]:
        context += "\n=== LATE GAME (5+ custo) ===\n"
        for c in relevant_cards["units_high"][:10]:
            influence = format_influence(c)
            context += f"• {c.name} | {influence} | {c.attack}/{c.health} | {c.rarity}\n"
    
    if relevant_cards["spells"]:
        context += "\n=== SPELLS ===\n"
        # Agrupar por tipo de efeito
        removal_spells = [c for c in relevant_cards["spells"] if any(word in c.text.lower() for word in ['kill', 'destroy', 'damage', 'deal'])]
        draw_spells = [c for c in relevant_cards["spells"] if 'draw' in c.text.lower()]
        other_spells = [c for c in relevant_cards["spells"] if c not in removal_spells and c not in draw_spells]
        
        if removal_spells:
            context += "Remoção:\n"
            for c in removal_spells[:7]:
                influence = format_influence(c)
                context += f"  • {c.name} | {influence} | {c.rarity} | {c.text[:40]}...\n"
        
        if draw_spells:
            context += "Card Draw:\n"
            for c in draw_spells[:5]:
                influence = format_influence(c)
                context += f"  • {c.name} | {influence} | {c.rarity} | {c.text[:40]}...\n"
        
        if other_spells:
            context += "Outros:\n"
            for c in other_spells[:5]:
                influence = format_influence(c)
                context += f"  • {c.name} | {influence} | {c.rarity}\n"
    
    if relevant_cards["weapons"]:
        context += "\n=== WEAPONS ===\n"
        for c in relevant_cards["weapons"][:10]:
            influence = format_influence(c)
            # Weapons geralmente dão bônus de ataque/vida
            stats = f"+{c.attack}/+{c.health}" if c.attack is not None and c.health is not None else "N/A"
            context += f"• {c.name} | {influence} | {stats} | {c.rarity}\n"
    
    if relevant_cards["powers"]:
        context += "\n=== POWER CARDS ===\n"
        # Separar por tipo
        sigils = [c for c in relevant_cards["powers"] if "Sigil" in c.name]
        dual_powers = [c for c in relevant_cards["powers"] if len(c.factions) > 1]
        utility_powers = [c for c in relevant_cards["powers"] if c not in sigils and c not in dual_powers]
        
        if sigils:
            context += "Sigils (podem ter mais de 4 cópias):\n"
            for c in sigils:
                context += f"  • {c.name} | 0 | N/A | Basic\n"
        
        if dual_powers:
            context += "Dual Powers:\n"
            for c in dual_powers[:10]:
                factions_str = '/'.join(c.factions)
                context += f"  • {c.name} | 0 | {factions_str} | {c.rarity}\n"
        
        if utility_powers:
            context += "Utility Powers:\n"
            for c in utility_powers[:5]:
                context += f"  • {c.name} | 0 | {c.rarity}\n"
    
    # Adicionar aviso final
    context += "\n⚠️ ATENÇÃO: Use APENAS as cartas listadas acima com as EXATAS informações fornecidas.\n"
    
    return context

# Função para gerar deck ATUALIZADA
def generate_deck(strategy, cards, model_key="gpt-4o", detailed=False):
    """Gera um deck usando o AI"""
    
    # Preparar contexto
    cards_context = prepare_cards_context(cards, strategy)
    
    # Prompt CAMPEÃO para todos os modelos
    prompt = f"""Você é um CAMPEÃO MUNDIAL de TCGs, especialista supremo em Eternal Card Game, com anos de experiência competitiva em torneios de alto nível. Sua missão é construir decks CAMPEÕES que dominam o meta competitivo.

=== REGRAS FUNDAMENTAIS DE CONSTRUÇÃO ===

REQUISITOS OBRIGATÓRIOS (NUNCA VIOLE ESTAS REGRAS):
1. Tamanho do Deck: EXATAMENTE 75-150 cartas (padrão competitivo: 75)
2. Proporção de Power: MÍNIMO 1/3 do deck (25+ em deck de 75)
3. Proporção de Não-Power: MÍNIMO 2/3 do deck (50+ em deck de 75)
4. Limite de Cópias: MÁXIMO 4 por carta (EXCETO Sigils básicos = ilimitados)
5. Validação: TODAS as cartas devem ter DeckBuildable=TRUE
6. Mercado: OPCIONAL - até 5 cartas únicas (requer cartas no deck principal que acessem, troquem, comprem ou copiem cartas do mercado)

VALIDAÇÃO MATEMÁTICA OBRIGATÓRIA:
- Some TODAS as quantidades: (X units + Y spells + Z weapons + W relics + P powers = 75)
- Verifique: Total ≥ 75, Powers ≥ 25, Não-Powers ≥ 50
- Conte cada linha individualmente antes de finalizar

{cards_context}

ESTRATÉGIA SOLICITADA: {strategy}

=== FORMATO PADRÃO DE RESPOSTA ===

**[NOME DO DECK] - [Facções] [Arquétipo]**
*"[Tagline criativa descrevendo a estratégia em uma frase]"*

=== UNITS (total) ===
4x Nome da Carta | Custo{{F}}{{F}} | Attack/Health | Rarity
3x Outra Carta | Custo{{T}}{{S}} | Attack/Health | Rarity

=== SPELLS (total) ===
4x Nome do Spell | Custo{{J}} | N/A | Rarity

=== WEAPONS (total) === (se houver)
2x Nome da Arma | Custo{{P}} | +Attack/+Health | Rarity

=== RELICS (total) === (se houver)
3x Nome da Relíquia | Custo{{T}}{{J}} | N/A | Rarity

=== POWERS (total) === (OBRIGATÓRIO - mínimo 25)
25x Fire Sigil | 0 | N/A | Basic
4x Seat of Glory | 0 | N/A | Uncommon
4x Diplomatic Seal | 0 | N/A | Common

=== MARKET (5) === (se incluir cartas que interagem com mercado)
1x Carta Situacional | Custo | Stats | Rarity

LEGENDAS DE INFLUÊNCIA:
{{F}} = Fire, {{T}} = Time, {{J}} = Justice, {{P}} = Primal, {{S}} = Shadow

=== ESTRATÉGIA GERAL ===
[Parágrafo explicando a filosofia central do deck, win conditions principais e por que este deck é competitivo no meta atual]

=== GUIA DE JOGO ===
1. **Early Game (Turnos 1-3):** [Detalhe as jogadas ideais, mulligans e objetivos]
2. **Mid Game (Turnos 4-6):** [Transições, desenvolvimento de board e timing de remoções]
3. **Late Game (Turnos 7+):** [Win conditions, como fechar o jogo e recursos finais]
4. **Combos Principais:** [Liste interações específicas entre 2-3 cartas]
5. **Matchups:** [Forte contra X, fraco contra Y, como adaptar sideboard]

{"=== ANÁLISE DETALHADA DE TODAS AS CARTAS ===" if detailed else ""}
{'''
Para TODAS AS CARTAS NÃO-POWER do deck, forneça análise completa:

**[Nome da Carta] (X cópias)**
* *Custo:* X | *Influência:* {{F}}{{F}}
* *Attack/Health:* X/X (ou N/A para não-unidades)
* *Texto:* "[Texto completo da habilidade]"
* *Expansão:* [Nome do Set]
* *Motivo no deck:* [Explicação detalhada de por que esta carta específica foi escolhida]
* *Sinergias/Combos:*
  * **[Carta 1]:** [Como interage e por quê é poderoso]
  * **[Carta 2]:** [Situações específicas onde brilha]
* *Possíveis substituições:* [Alternativas budget ou tech choices]
''' if detailed else ""}

LEMBRE-SE: Você está construindo um deck para VENCER CAMPEONATOS. Cada escolha deve ser justificada com rigor competitivo. Use APENAS cartas da lista fornecida e mantenha foco absoluto em PODER e CONSISTÊNCIA.

⚠️ VALIDAÇÃO: Antes de responder, verifique se TODAS as cartas usadas existem na lista fornecida 
com as EXATAS raridades e influências mostradas."""
    
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
        index=3  # Default para gpt-4o
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
            if "o1" in selected_model.lower() or "o4" in selected_model.lower():
                st.info("💡 Os modelos O1/O4 têm limitações específicas. Tente com GPT-4o ou GPT-4o-mini.")

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
        is_valid, errors, stats = validator.validate_text_deck(deck_for_validation)
        
        if is_valid:
            st.success("✅ Deck válido!")
        else:
            st.error("❌ Deck com problemas:")
            for error in errors:
                st.warning(error)
        
        # Mostrar estatísticas do parser
        with st.expander("🔍 Debug - Estatísticas do Parser"):
            st.write(f"Total de cartas: {stats['total_cards']}")
            st.write(f"Cartas de poder: {stats['power_cards']}")
            st.write(f"Formato detectado: {stats.get('format_detected', 'unknown')}")
            st.write(f"Linhas parseadas: {stats['parsed_lines']}")
            st.write(f"Linhas de metadata ignoradas: {stats['skipped_metadata']}")
    
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
        # Botão de exportação
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
st.caption("💡 Dica: Para melhores resultados, teste com o1-pro ou gpt-4o-preview para análises mais precisas")