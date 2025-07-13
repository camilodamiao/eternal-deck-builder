"""
🚨 ÂNCORA: MAIN_FILE - Deck Builder AI v4 com RAG integrado
Contexto: Versão completa com sistema RAG e todas correções
Cuidado: Manter toda estrutura do v3 e adicionar melhorias
Dependências: OpenAI, Streamlit, ChromaDB, Google Sheets
"""

import streamlit as st
import sys
import time
from typing import List, Optional, Dict, Tuple
from dotenv import load_dotenv

# Adicionar path para imports locais
sys.path.append('.')

# Imports do projeto
from langchain_openai import ChatOpenAI
from data.google_sheets_client import GoogleSheetsClient
from core.deck_validator import DeckValidator
from config.settings import settings
from config.constants import FACTIONS
import json

# Carregar variáveis de ambiente
load_dotenv()

# ===============================================
# CONFIGURAÇÃO DA PÁGINA
# ===============================================
st.set_page_config(page_title="Deck Builder AI v4 - Eternal", layout="wide")
st.title("🤖 Deck Builder AI v4 - Eternal")
st.markdown("Sistema com busca semântica RAG integrada")
st.markdown("---")

# ===============================================
# CONFIGURAÇÕES DOS MODELOS
# ===============================================

# 🚨 ÂNCORA: MODEL_CONFIG - Configurações específicas por modelo
# Contexto: Modelos têm diferentes capacidades e custos
# Cuidado: o1 e o1-mini não suportam temperature/stop
# Dependências: create_llm function

MODEL_CONFIGS = {
    "o1": {
        "name": "O1 (Raciocínio avançado)",
        "supports_temperature": False,
        "supports_stop": False,
        "cost_per_1k": 0.015
    },
    "o1-mini": {
        "name": "O1 Mini (Raciocínio rápido)",
        "supports_temperature": False,
        "supports_stop": False,
        "cost_per_1k": 0.003
    },
    "gpt-4o": {
        "name": "GPT-4o (Mais capaz)",
        "supports_temperature": True,
        "supports_stop": True,
        "cost_per_1k": 0.005
    },
    "gpt-4o-mini": {
        "name": "GPT-4o Mini (Econômico)",
        "supports_temperature": True,
        "supports_stop": True,
        "cost_per_1k": 0.00015
    },
    "gpt-4-turbo": {
        "name": "GPT-4 Turbo",
        "supports_temperature": True,
        "supports_stop": True,
        "cost_per_1k": 0.01
    },
    "gpt-3.5-turbo": {
        "name": "GPT-3.5 Turbo",
        "supports_temperature": True,
        "supports_stop": True,
        "cost_per_1k": 0.0005
    }
}

def create_llm(model_key):
    """Cria o LLM com as configurações corretas para cada modelo"""
    config = MODEL_CONFIGS[model_key]
    
    # Parâmetros base
    params = {
        "model": model_key,
        "api_key": settings.openai_api_key,
        "max_tokens": 4000
    }
    
    # Adicionar temperatura e stop se suportado
    if config["supports_temperature"]:
        params["temperature"] = 0.7
    
    if config["supports_stop"]:
        params["stop"] = ["\n\n###", "\n\nNote:"]
    
    return ChatOpenAI(**params)

# ===============================================
# CACHE E INICIALIZAÇÃO
# ===============================================

@st.cache_resource
def get_sheets_client():
    return GoogleSheetsClient()

@st.cache_resource
def get_validator():
    return DeckValidator()

# ===============================================
# SIDEBAR - FILTROS E CONFIGURAÇÕES
# ===============================================

with st.sidebar:
    st.header("⚙️ Configurações")
    
    # Seleção de modelo
    selected_model = st.selectbox(
        "Modelo de IA",
        list(MODEL_CONFIGS.keys()),
        format_func=lambda x: MODEL_CONFIGS[x]["name"],
        help="Escolha o modelo de IA para gerar o deck"
    )
    
    st.caption(f"💰 Custo estimado: ${MODEL_CONFIGS[selected_model]['cost_per_1k']}/1k tokens")
    
    # Formato do deck
    deck_format = st.selectbox(
        "Formato",
        ["Throne", "Expedition"],
        help="Throne = todas as cartas, Expedition = sets recentes"
    )
    
    # Modo detalhado
    detailed_mode = st.checkbox(
        "Modo Detalhado",
        value=True,
        help="Incluir análise completa de cada carta escolhida"
    )
    
    # Debug mode
    debug_mode = st.checkbox(
        "Modo Debug",
        value=False,
        help="Mostrar informações técnicas"
    )
    
    st.markdown("---")
    st.subheader("🎯 Filtros de Cartas")
    
    # 🚨 ÂNCORA: CARD_FILTERS - Sistema completo de filtros
    # Contexto: Controla quais cartas são enviadas para IA
    # Cuidado: Ordem dos filtros importa para UX
    # Dependências: prepare_cards_context, GoogleSheetsClient
    
    # 1. Seleção de facções
    st.markdown("#### Facções Permitidas")
    selected_factions = []
    
    cols = st.columns(3)
    faction_list = list(FACTIONS.keys())
    
    for i, faction in enumerate(faction_list):
        col = cols[i % 3]
        if col.checkbox(
            f"{FACTIONS[faction]['symbol']} {FACTIONS[faction]['name']}",
            key=f"faction_{faction}",
            value=i < 2  # Default: primeiras 2 facções
        ):
            selected_factions.append(faction)
    
    # 2. Máximo de facções
    max_factions = st.slider(
        "Máximo de Facções no Deck",
        min_value=1,
        max_value=5,
        value=2,
        help="Limita a complexidade de influência do deck"
    )
    
    # Validar seleção
    if len(selected_factions) > max_factions:
        st.warning(f"⚠️ Você selecionou {len(selected_factions)} facções, mas o limite é {max_factions}")
        selected_factions = selected_factions[:max_factions]
    
    # 3. Incluir mercado
    use_market = st.checkbox(
        "🏪 Incluir Mercado",
        value=False,
        help="Adiciona 5 cartas de mercado + merchants para acessá-lo"
    )
    
    # 4. Cartas obrigatórias
    st.markdown("#### Cartas Específicas")
    required_cards_input = st.text_area(
        "✅ Cartas Obrigatórias",
        placeholder="Digite uma carta por linha:\nTorch\nHarsh Rule",
        height=80
    )
    
    # 5. Cartas proibidas
    forbidden_cards_input = st.text_area(
        "❌ Cartas Proibidas",
        placeholder="Digite uma carta por linha",
        height=80
    )
    
    # 6. Modo de filtragem
    use_filtering = st.radio(
        "Modo de Contexto",
        ["Filtrar cartas relevantes", "Incluir todas as cartas"],
        index=0,
        help="Filtrado: ~100 cartas relevantes | Completo: 500+ cartas"
    ) == "Filtrar cartas relevantes"
    
    # ===============================================
    # CONFIGURAÇÃO RAG
    # ===============================================
    
    st.markdown("---")
    st.markdown("### ⚡ Busca Semântica (RAG)")
    
    use_rag = st.checkbox(
        "🚀 Usar busca semântica",
        value=True,
        help="Usa IA para encontrar as cartas mais relevantes para sua estratégia"
    )
    
    # Verificar status do RAG
    if use_rag:
        try:
            from rag.semantic_search import create_semantic_search
            from rag.chromadb_setup import ChromaDBManager
            
            searcher = create_semantic_search()
            stats = searcher.get_search_statistics()
            
            if stats['chromadb_status'] == 'ready':
                st.success(f"✅ RAG ativo: {stats['total_embeddings']:,} cartas indexadas")
                
                # Mostrar metadata se disponível
                if stats.get('metadata'):
                    created = stats['metadata'].get('created_at', 'N/A')
                    if created != 'N/A':
                        st.caption(f"Índice criado: {created[:10]}")
            else:
                st.warning("⚠️ RAG não inicializado")
                
                if st.button("🔧 Inicializar RAG", type="primary", use_container_width=True):
                    with st.spinner("Criando embeddings... (2-3 minutos)"):
                        manager = ChromaDBManager()
                        result = manager.setup_card_embeddings()
                        st.success(f"✅ {result['embedded_cards']:,} cartas indexadas!")
                        time.sleep(1)
                        st.rerun()
                
                use_rag = False
                
        except ImportError:
            st.error("❌ Módulos RAG não instalados")
            st.code("pip install chromadb sentence-transformers", language="bash")
            use_rag = False
        except Exception as e:
            st.error(f"❌ Erro: {str(e)}")
            use_rag = False

    # Mostrar comparação RAG vs Tradicional
    if use_rag:
        with st.expander("📊 Como funciona o RAG?"):
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**🔤 Busca Tradicional**")
                st.markdown("- Keywords básicas")
                st.markdown("- ~200+ cartas")
                st.markdown("- Pode perder sinergias")
            
            with col2:
                st.markdown("**🧠 Busca Semântica**")
                st.markdown("- Entende conceitos")
                st.markdown("- ~80 cartas relevantes")
                st.markdown("- Encontra sinergias ocultas")
    
    # Exemplos de estratégias
    st.markdown("---")
    st.caption("💡 Exemplos de estratégias:")
    st.caption("• Aggro Fire com burn direto")
    st.caption("• Control com removal e card draw")
    st.caption("• Midrange Time com criaturas grandes")
    st.caption("• Combo void com recursão")

# ===============================================
# FUNÇÕES DE PREPARAÇÃO DE CONTEXTO
# ===============================================

def prepare_cards_context(strategy, allowed_factions=None, use_market=False, 
                         required_cards=None, forbidden_cards=None, 
                         use_filtering=True, use_rag=True):
    """
    🚨 ÂNCORA: RAG_CONTEXT - Preparação de contexto principal
    Contexto: Usa RAG quando disponível, fallback para tradicional
    Cuidado: Manter compatibilidade com código existente
    Dependências: ChromaDB (opcional), GoogleSheetsClient
    """
    
    client = get_sheets_client()
    
    # Se não filtrar, retornar todas as cartas
    if not use_filtering:
        return prepare_all_cards_context(client)
    
    # Tentar usar RAG
    if use_rag and use_filtering:
        try:
            from rag.semantic_search import create_semantic_search
            
            searcher = create_semantic_search()
            stats = searcher.get_search_statistics()
            
            if stats['chromadb_status'] == 'ready':
                if debug_mode:
                    st.info("🚀 Usando busca semântica RAG...")
                
                # Buscar cartas via RAG
                relevant_cards = searcher.search_cards_for_strategy(
                    strategy=strategy,
                    allowed_factions=allowed_factions,
                    use_market=use_market,
                    required_cards=required_cards,
                    forbidden_cards=forbidden_cards,
                    max_results=80
                )
                
                return format_cards_context_from_rag(
                    relevant_cards, strategy, required_cards, 
                    forbidden_cards, use_market
                )
                
        except Exception as e:
            if debug_mode:
                st.warning(f"RAG falhou: {e}")
    
    # Fallback para método tradicional
    return prepare_cards_context_traditional(
        client, strategy, allowed_factions, use_market, 
        required_cards, forbidden_cards
    )

def format_cards_context_from_rag(cards, strategy, required_cards, 
                                 forbidden_cards, use_market):
    """Formata contexto a partir dos resultados RAG"""
    
    # Separar por tipo
    units = []
    spells = []
    powers = []
    weapons = []
    relics = []
    markets = []
    
    for card in cards:
        # Usar influence_string diretamente da planilha
        influence = card.influence_string or ""
        
        if card.is_unit:
            info = f"• {card.name} | {card.cost}{influence} | {card.attack}/{card.health} | {card.rarity}"
            if card.card_text:
                info += f" | {card.card_text}"
            units.append(info)
            
        elif card.is_power:
            info = f"• {card.name} | {card.cost}{influence}"
            if card.card_text:
                info += f" | {card.card_text}"
            powers.append(info)
            
        elif 'Spell' in card.type:
            info = f"• {card.name} | {card.cost}{influence} | {card.rarity}"
            if card.card_text:
                info += f" | {card.card_text}"
            spells.append(info)
            
        elif 'Weapon' in card.type:
            stats = f"+{card.attack}/+{card.health}" if card.attack else ""
            info = f"• {card.name} | {card.cost}{influence} | {stats} | {card.rarity}"
            if card.card_text:
                info += f" | {card.card_text}"
            weapons.append(info)
            
        elif 'Relic' in card.type:
            info = f"• {card.name} | {card.cost}{influence} | {card.rarity}"
            if card.card_text:
                info += f" | {card.card_text}"
            relics.append(info)
        
        # Detectar merchants
        if card.card_text and any(term in card.card_text.lower() 
                                for term in ['market', 'merchant', 'smuggler', 'etchings']):
            markets.append(f"• {card.name} | {card.cost}{influence} | {card.card_text}")
    
    # Construir contexto
    parts = []
    parts.append(f"=== ESTRATÉGIA SOLICITADA ===")
    parts.append(strategy)
    parts.append("")
    parts.append(f"=== CARTAS RELEVANTES (via busca semântica) ===")
    parts.append(f"Total encontrado: {len(cards)} cartas")
    parts.append("")
    
    if units:
        parts.append(f"=== UNIDADES ({len(units)}) ===")
        parts.extend(units[:30])
        parts.append("")
    
    if spells:
        parts.append(f"=== SPELLS ({len(spells)}) ===")
        parts.extend(spells[:20])
        parts.append("")
    
    if weapons:
        parts.append(f"=== WEAPONS ({len(weapons)}) ===")
        parts.extend(weapons[:10])
        parts.append("")
    
    if relics:
        parts.append(f"=== RELICS ({len(relics)}) ===")
        parts.extend(relics[:10])
        parts.append("")
    
    if powers:
        parts.append(f"=== POWERS ({len(powers)}) ===")
        parts.extend(powers[:15])
        parts.append("")
    
    if use_market and markets:
        parts.append(f"=== MERCHANTS/MARKET ACCESS ({len(markets)}) ===")
        parts.extend(markets[:5])
        parts.append("")
    
    if required_cards:
        parts.append("=== CARTAS OBRIGATÓRIAS ===")
        parts.append(f"DEVE incluir: {', '.join(required_cards)}")
        parts.append("")
    
    if forbidden_cards:
        parts.append("=== CARTAS PROIBIDAS ===")
        parts.append(f"NÃO incluir: {', '.join(forbidden_cards)}")
        parts.append("")
    
    # Legenda de influência
    parts.append("=== LEGENDA DE INFLUÊNCIA ===")
    parts.append("{F} = Fire, {T} = Time, {J} = Justice, {P} = Primal, {S} = Shadow")
    
    return "\n".join(parts)

def prepare_cards_context_traditional(client, strategy, allowed_factions, 
                                    use_market, required_cards, forbidden_cards):
    """
    🚨 ÂNCORA: TRADITIONAL_CONTEXT - Método tradicional de filtragem
    Contexto: Usado quando RAG não está disponível
    Cuidado: Manter sincronizado com formato do RAG
    Dependências: GoogleSheetsClient
    """
    
    # Buscar todas as cartas
    all_cards = client.get_all_cards()
    
    # Filtrar jogáveis
    playable_cards = [c for c in all_cards if c.deck_buildable]
    
    # Filtrar por facções
    if allowed_factions:
        filtered_cards = []
        for card in playable_cards:
            if not card.factions:  # Cartas neutras
                filtered_cards.append(card)
            elif any(f in allowed_factions for f in card.factions):
                filtered_cards.append(card)
        playable_cards = filtered_cards
    
    # Filtrar proibidas
    if forbidden_cards:
        playable_cards = [c for c in playable_cards 
                         if not any(f.lower() in c.name.lower() 
                                   for f in forbidden_cards)]
    
    # Detectar arquétipo da estratégia
    strategy_lower = strategy.lower()
    is_aggro = any(word in strategy_lower for word in ['aggro', 'aggressive', 'fast', 'rush'])
    is_control = any(word in strategy_lower for word in ['control', 'removal', 'slow'])
    is_midrange = any(word in strategy_lower for word in ['midrange', 'value', 'balanced'])
    is_combo = any(word in strategy_lower for word in ['combo', 'synergy', 'engine'])
    
    # Sistema de scoring
    scored_cards = []
    
    for card in playable_cards:
        score = 0
        
        # Score baseado no texto da carta
        if card.card_text:
            text_lower = card.card_text.lower()
            
            # Aggro scoring
            if is_aggro:
                if any(kw in text_lower for kw in ['charge', 'overwhelm', 'warcry', 'quickdraw']):
                    score += 3
                if card.is_unit and card.cost <= 3:
                    score += 2
                if 'burn' in text_lower or 'damage' in text_lower:
                    score += 2
            
            # Control scoring
            if is_control:
                if any(kw in text_lower for kw in ['kill', 'silence', 'void', 'draw', 'harsh rule']):
                    score += 3
                if 'sweep' in text_lower or 'board' in text_lower:
                    score += 2
            
            # Keywords específicos da estratégia
            strategy_words = strategy_lower.split()
            for word in strategy_words:
                if len(word) > 3 and word in text_lower:
                    score += 2
            
            # Mercado
            if use_market and any(kw in text_lower for kw in ['market', 'merchant', 'smuggler']):
                score += 10
        
        # Score por tipo e custo
        if card.is_unit:
            if is_aggro and card.cost <= 3:
                score += 1
            elif is_control and card.cost >= 5:
                score += 1
            elif is_midrange and 3 <= card.cost <= 5:
                score += 1
        
        if score > 0 or (required_cards and 
                        any(req.lower() in card.name.lower() for req in required_cards)):
            scored_cards.append((card, score))
    
    # Ordenar por score
    scored_cards.sort(key=lambda x: x[1], reverse=True)
    
    # Limitar quantidade
    top_cards = [card for card, _ in scored_cards[:150]]
    
    # Garantir cartas obrigatórias
    if required_cards:
        for req_name in required_cards:
            found = False
            for card in top_cards:
                if req_name.lower() in card.name.lower():
                    found = True
                    break
            
            if not found:
                # Buscar na lista completa
                results = client.search_cards(name=req_name, limit=1)
                if results:
                    top_cards.insert(0, results[0])
    
    # Formatar contexto
    return format_traditional_context(top_cards, strategy, required_cards, 
                                    forbidden_cards, use_market)

def format_traditional_context(cards, strategy, required_cards, 
                             forbidden_cards, use_market):
    """Formata contexto tradicional"""
    
    # Separar por tipo
    units = [c for c in cards if c.is_unit]
    spells = [c for c in cards if 'Spell' in c.type]
    powers = [c for c in cards if c.is_power]
    weapons = [c for c in cards if 'Weapon' in c.type]
    relics = [c for c in cards if 'Relic' in c.type]
    markets = [c for c in cards if c.card_text and 
               any(term in c.card_text.lower() for term in ['market', 'merchant'])]
    
    parts = []
    parts.append(f"=== ESTRATÉGIA SOLICITADA ===")
    parts.append(strategy)
    parts.append("")
    parts.append("=== CARTAS DISPONÍVEIS ===")
    parts.append("")
    
    if units:
        parts.append(f"=== UNIDADES ({len(units)}) ===")
        for card in units[:40]:
            influence = card.influence_string or ""
            parts.append(f"• {card.name} | {card.cost}{influence} | {card.attack}/{card.health} | {card.rarity}")
    
    if spells:
        parts.append("")
        parts.append(f"=== SPELLS ({len(spells)}) ===")
        for card in spells[:25]:
            influence = card.influence_string or ""
            parts.append(f"• {card.name} | {card.cost}{influence} | {card.rarity}")
    
    if weapons:
        parts.append("")
        parts.append(f"=== WEAPONS ({len(weapons)}) ===")
        for card in weapons[:10]:
            influence = card.influence_string or ""
            parts.append(f"• {card.name} | {card.cost}{influence} | {card.rarity}")
    
    if relics:
        parts.append("")
        parts.append(f"=== RELICS ({len(relics)}) ===")
        for card in relics[:10]:
            influence = card.influence_string or ""
            parts.append(f"• {card.name} | {card.cost}{influence} | {card.rarity}")
    
    if powers:
        parts.append("")
        parts.append(f"=== POWERS ({len(powers)}) ===")
        for card in powers[:20]:
            influence = card.influence_string or ""
            parts.append(f"• {card.name} | {card.cost}{influence}")
    
    if use_market and markets:
        parts.append("")
        parts.append(f"=== MERCHANTS/MARKET ACCESS ({len(markets)}) ===")
        for card in markets[:5]:
            influence = card.influence_string or ""
            parts.append(f"• {card.name} | {card.cost}{influence}")
    
    if required_cards:
        parts.append("")
        parts.append("=== CARTAS OBRIGATÓRIAS ===")
        parts.append(f"DEVE incluir: {', '.join(required_cards)}")
    
    if forbidden_cards:
        parts.append("")
        parts.append("=== CARTAS PROIBIDAS ===")
        parts.append(f"NÃO incluir: {', '.join(forbidden_cards)}")
    
    parts.append("")
    parts.append("=== LEGENDA DE INFLUÊNCIA ===")
    parts.append("{F} = Fire, {T} = Time, {J} = Justice, {P} = Primal, {S} = Shadow")
    
    return "\n".join(parts)

def prepare_all_cards_context(client):
    """Contexto com todas as cartas (sem filtro)"""
    all_cards = client.get_all_cards()
    playable = [c for c in all_cards if c.deck_buildable]
    
    return format_traditional_context(
        playable[:250], 
        "Todas as cartas disponíveis",
        None, None, False
    )

# ===============================================
# PROMPT PARA GERAÇÃO DE DECK
# ===============================================

def create_deck_prompt(strategy, cards_context, detailed_mode, deck_format):
    """
    🚨 ÂNCORA: DECK_PROMPT - Prompt principal CAMPEÃO
    Contexto: Mentalidade competitiva para decks otimizados
    Cuidado: Formato de saída deve ser exato para parser
    Dependências: DeckValidator espera formato específico
    """
    
    # Escape das chaves para evitar interpretação como f-string
    prompt = f"""Você é um jogador CAMPEÃO de Eternal Card Game, top 10 mundial.
Crie o deck MAIS COMPETITIVO possível para a estratégia solicitada.

FORMATO: {deck_format}

{cards_context}

=== REGRAS ABSOLUTAS ===
1. Deck DEVE ter 75-150 cartas (recomendado: 75 para máxima consistência)
2. MÍNIMO 1/3 power cards (25+ em deck de 75)
3. MÁXIMO 4 cópias de cada carta (exceto Sigils = ilimitados)
4. Se incluir Mercado: exatamente 5 cartas únicas + merchants
5. Use APENAS cartas da lista fornecida
6. Influência segue padrão {{F}}={{Fire}}, {{T}}={{Time}}, {{J}}={{Justice}}, {{P}}={{Primal}}, {{S}}={{Shadow}}

=== FORMATO DE SAÍDA OBRIGATÓRIO ===

**[Nome do Deck] - [Arquétipo]**
*"[Frase de efeito]"*

=== DECK ({deck_format.upper()}) - [Total] CARTAS ===

[Qtd]x [Nome] | [Custo com Influência] | [Ataque/Vida se unit] | [Raridade]

Exemplo correto:
4x Torch | 1{{F}} | N/A | Common
4x Oni Ronin | 1{{F}} | 2/1 | Common
3x Sandstorm Titan | 4{{T}}{{T}} | 5/6 | Legendary

SEPARE POR CATEGORIAS:
=== UNITS ([qtd]) ===
=== SPELLS ([qtd]) ===
=== POWERS ([qtd]) ===
=== WEAPONS ([qtd]) === (se houver)
=== RELICS ([qtd]) === (se houver)
=== MARKET (5) === (se incluir)

"""

    if detailed_mode:
        prompt += """
=== ANÁLISE DETALHADA ===
Para CADA carta escolhida, explique:
- Por que foi incluída
- Sinergias específicas
- Papel na estratégia

=== GUIA DE JOGO ===
- Mulligan ideal
- Gameplan por fase (early/mid/late)
- Combos principais
- Matchups favoráveis/desfavoráveis
"""

    prompt += """
LEMBRE-SE: Você é um CAMPEÃO. Cada escolha deve ser OTIMIZADA para VENCER.
Nada de decks casuais - apenas COMPETITIVO e CONSISTENTE!
"""

    return prompt

# ===============================================
# ÁREA PRINCIPAL
# ===============================================

st.header("📝 Estratégia do Deck")

# Processar inputs de cartas
required_cards = None
forbidden_cards = None

if required_cards_input:
    required_cards = [c.strip() for c in required_cards_input.split('\n') if c.strip()]

if forbidden_cards_input:
    forbidden_cards = [c.strip() for c in forbidden_cards_input.split('\n') if c.strip()]

# Campo de estratégia
deck_strategy = st.text_area(
    "Descreva a estratégia desejada:",
    placeholder="Ex: Deck aggro Fire/Justice com unidades pequenas eficientes, burn direto e finalizadores...",
    height=150,
    help="Seja específico sobre o estilo de jogo desejado"
)

# Exemplo de estratégias
col1, col2 = st.columns([3, 1])
with col2:
    if st.button("📚 Ver Exemplos"):
        st.info("""
        **Aggro Fire**: "Deck agressivo mono Fire com criaturas de baixo custo, charge e burn direto"
        
        **Control Feln**: "Control Primal/Shadow com removal, card draw e finalizadores grandes"
        
        **Midrange Time**: "Deck Time com ramp, criaturas eficientes e boa curva de mana"
        """)

# Validações
if not selected_factions:
    st.warning("⚠️ Selecione pelo menos uma facção no sidebar")

# Botão de geração
generate_button = st.button(
    "🎯 Gerar Deck Competitivo", 
    type="primary",
    disabled=not deck_strategy or not selected_factions,
    use_container_width=True
)

# Gerar deck
if generate_button:
    with st.spinner("🤖 Construindo deck competitivo..."):
        try:
            # Preparar contexto
            cards_context = prepare_cards_context(
                deck_strategy,
                allowed_factions=selected_factions,
                use_market=use_market,
                required_cards=required_cards,
                forbidden_cards=forbidden_cards,
                use_filtering=use_filtering,
                use_rag=use_rag
            )
            
            # Debug info
            if debug_mode:
                with st.expander("🔍 Debug - Contexto"):
                    st.text(f"Tamanho: {len(cards_context)} chars")
                    st.text(f"Cartas: ~{cards_context.count('•')}")
                    st.text(f"Modo: {'RAG' if use_rag else 'Tradicional'}")
                    st.text(f"Facções: {', '.join(selected_factions)}")
            
            # Criar prompt
            prompt = create_deck_prompt(
                deck_strategy,
                cards_context,
                detailed_mode,
                deck_format
            )
            
            # Gerar com LLM
            llm = create_llm(selected_model)
            response = llm.invoke(prompt)
            deck_text = response.content
            
            # Calcular métricas
            tokens = len(prompt.split()) + len(deck_text.split())
            cost = tokens * MODEL_CONFIGS[selected_model]["cost_per_1k"] / 1000
            
            # Salvar no session state
            st.session_state['deck_generated'] = True
            st.session_state['current_deck'] = deck_text
            st.session_state['model_used'] = selected_model
            st.session_state['tokens_used'] = tokens
            st.session_state['cost_estimate'] = cost
            
        except Exception as e:
            st.error(f"❌ Erro ao gerar deck: {str(e)}")
            if "rate limit" in str(e).lower():
                st.info("💡 Tente novamente em alguns segundos ou use outro modelo")

# ===============================================
# MOSTRAR DECK GERADO
# ===============================================

if st.session_state.get('deck_generated', False):
    deck_text = st.session_state.get('current_deck', '')
    
    st.markdown("---")
    st.header("🎴 Deck Gerado")
    
    # Métricas
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Modelo", st.session_state.get('model_used', 'N/A'))
    with col2:
        tokens = st.session_state.get('tokens_used', 0)
        st.metric("Tokens", f"{tokens:,}")
    with col3:
        cost = st.session_state.get('cost_estimate', 0)
        st.metric("Custo Estimado", f"${cost:.4f}")
    
    # Validar deck
    validator = get_validator()
    
    # Extrair apenas lista do deck para validação
    deck_lines = []
    in_deck_section = False
    
    for line in deck_text.split('\n'):
        if 'DECK' in line.upper() and any(x in line for x in ['75', '===', '---']):
            in_deck_section = True
            continue
        if in_deck_section and line.strip():
            if any(word in line.upper() for word in ['ESTRATÉGIA', 'ANÁLISE', 'GUIA', 'COMO JOGAR']):
                break
            if line.strip() and line[0].isdigit():
                deck_lines.append(line.strip())
    
    # Validar
    if deck_lines:
        deck_for_validation = '\n'.join(deck_lines)
        is_valid, errors, stats = validator.validate_text_deck(deck_for_validation)
        
        if is_valid:
            st.success("✅ Deck válido!")
        else:
            st.error("❌ Deck com problemas:")
            for error in errors:
                st.warning(error)
        
        # Mostrar estatísticas
        with st.expander("📊 Estatísticas do Deck"):
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Total de Cartas", stats.get('total_cards', 0))
            with col2:
                st.metric("Powers", stats.get('power_cards', 0))
            with col3:
                power_ratio = stats.get('power_ratio', 0)
                st.metric("% Powers", f"{power_ratio:.1%}")
            with col4:
                st.metric("Formato", stats.get('format_detected', 'Unknown'))
            
            if debug_mode:
                st.json(stats)
    
    # Mostrar deck completo
    st.text_area("Deck Completo:", deck_text, height=500)
    
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
            
            with st.spinner("Convertendo..."):
                try:
                    exported_deck = exporter.export_deck_text(deck_text, deck_format)
                    
                    st.text_area(
                        "Copie este texto para importar no Eternal:",
                        exported_deck,
                        height=300,
                        key="exported_deck"
                    )
                    
                    st.download_button(
                        label="💾 Baixar Formatado",
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
    
    question = st.text_input(
        "Tem alguma dúvida sobre o deck?",
        placeholder="Ex: Por que escolheu Sandstorm Titan?",
        key="followup_question"
    )
    
    if st.button("Perguntar", key="ask_button") and question:
        with st.spinner("Analisando..."):
            try:
                # Contexto com o deck
                context = f"Sobre o deck gerado:\n\n{deck_text}\n\nPergunta: {question}"
                
                llm = create_llm(selected_model)
                answer = llm.invoke(context)
                
                st.write(answer.content)
                
                # Custo da pergunta
                tokens_q = len(context.split()) + len(answer.content.split())
                cost_q = tokens_q * MODEL_CONFIGS[selected_model]["cost_per_1k"] / 1000
                st.caption(f"💰 Custo da pergunta: ${cost_q:.4f}")
                
            except Exception as e:
                st.error(f"Erro: {str(e)}")

else:
    st.info("👆 Configure os filtros e descreva sua estratégia para gerar um deck")

# Footer
st.markdown("---")
st.caption("💡 GPT-4o: melhor qualidade | GPT-4o-mini: mais econômico | O1: raciocínio avançado")
if use_rag:
    st.caption("🚀 RAG ativo: busca semântica encontra cartas mais relevantes")
else:
    st.caption("🔤 Modo tradicional: busca por keywords básicas")