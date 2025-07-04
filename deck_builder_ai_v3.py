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
    "o1": {
        "name": "O1 (Mais avançado)",
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
    if model_key in ["o1", "o4-mini"]:
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

def is_market_access_card(card):
    """Identifica se uma carta pode acessar o mercado"""
    if not card.text:
        return False
    
    text_lower = card.text.lower()
    
    # Termos que indicam acesso ao mercado
    market_access_terms = [
        'your market',
        'bargain',
    ]
    
    # Verificar se tem algum termo de acesso
    has_access = any(term in text_lower for term in market_access_terms)
    
    # Verificar se é um merchant pelo nome
    is_merchant = 'merchant' in card.name.lower()
    
    # Verificar smugglers (também acessam mercado)
    is_smuggler = 'smuggler' in card.name.lower()
    
    return has_access or is_merchant or is_smuggler

# Função para preparar contexto de cartas ATUALIZADA
def prepare_cards_context(cards, strategy, filters=None):
    """Prepara uma seleção relevante de cartas para o AI com dados completos"""
    
    # Configurações padrão se não forem passados filtros
    if filters is None:
        filters = {
            'allowed_factions': ['FIRE', 'TIME', 'JUSTICE', 'PRIMAL', 'SHADOW'],
            'max_factions': 5,
            'use_market': True,
            'required_cards': [],
            'banned_cards': [],
            'filter_mode': 'relevant'
        }
    
    # Debug dos filtros
    if filters['required_cards']:
        st.info(f"🔍 Cartas obrigatórias solicitadas: {filters['required_cards']}")
    
    # Debug do total de cartas
    st.info(f"📊 Total de cartas na base: {len(cards)}")
    
    # NOVO: Coletar cartas de mercado se use_market está ativo
    market_access_cards = []
    if filters['use_market']:
        st.info("🏪 Mercado habilitado - buscando cartas de acesso...")
        
        for card in cards:
            # Verificar se é carta banida
            if card.name in filters['banned_cards']:
                continue
                
            # Verificar se é carta de acesso ao mercado
            if is_market_access_card(card):
                # Verificar se tem facções permitidas
                if card.factions and any(f in filters['allowed_factions'] for f in card.factions):
                    market_access_cards.append(card)
                elif not card.factions:  # Cartas neutras
                    market_access_cards.append(card)
        
        st.success(f"✅ Encontradas {len(market_access_cards)} cartas de acesso ao mercado")
        
        # Debug - mostrar algumas cartas encontradas
        if market_access_cards:
            st.write("Exemplos de cartas de mercado encontradas:")
            for card in market_access_cards[:5]:
                st.write(f"  - {card.name} ({'/'.join(card.factions) if card.factions else 'Neutral'})")

    # PRIMEIRO: Processar cartas obrigatórias/banidas (SEMPRE)
    cards_to_process = []
    required_cards_found = []
    
    # Remover cartas banidas
    for card in cards:
        if card.name not in filters['banned_cards']:
            cards_to_process.append(card)
    
    # Buscar cartas obrigatórias
    for required_name in filters['required_cards']:
        found = False
        # Busca exata primeiro
        for card in cards:
            if card.name.lower() == required_name.lower():
                required_cards_found.append(card)
                st.success(f"✅ Carta obrigatória '{card.name}' encontrada!")
                found = True
                break
        
        if not found:
            # Busca parcial
            partial_matches = []
            for card in cards:
                if required_name.lower() in card.name.lower():
                    partial_matches.append(card)
            
            if partial_matches:
                st.warning(f"⚠️ '{required_name}' não encontrado exatamente. Encontradas {len(partial_matches)} correspondências parciais:")
                for match in partial_matches[:5]:
                    st.write(f"  - {match.name}")
                # Adicionar a primeira correspondência
                required_cards_found.append(partial_matches[0])
                st.info(f"➕ Adicionando '{partial_matches[0].name}' como melhor correspondência")
            else:
                st.error(f"❌ Carta '{required_name}' não encontrada de forma alguma na base!")
    
    # Função auxiliar para formatar influência
    def format_influence(card):
        """Formata influência no estilo {F}{T}{J}"""
        # Usar influence_string se disponível
        if hasattr(card, 'influence_string') and card.influence_string:
            return f"{card.cost}{card.influence_string}"
        
        # Fallback para o método antigo
        if not card.influence:
            return str(card.cost)
        
        influence_str = str(card.cost)
        influence_map = {'FIRE': 'F', 'TIME': 'T', 'JUSTICE': 'J', 'PRIMAL': 'P', 'SHADOW': 'S'}
        
        for faction in ['FIRE', 'TIME', 'JUSTICE', 'PRIMAL', 'SHADOW']:
            if faction in card.influence:
                count = card.influence[faction]
                symbol = influence_map[faction]
                influence_str += '{' + symbol + '}' * count
                
        return influence_str
    
    # Inicializar categorias
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
    
    # MODO COMPLETO - Incluir todas as cartas
    if filters['filter_mode'] == 'Incluir todas as cartas':
        st.info(f"📊 Modo completo: incluindo {len(cards_to_process)} cartas (após remover banidas)")
        
        # Adicionar cartas obrigatórias primeiro
        for card in required_cards_found:
            if card.card_type == "Unit":
                if card.cost <= 2:
                    relevant_cards["units_low"].append(card)
                elif card.cost <= 4:
                    relevant_cards["units_mid"].append(card)
                else:
                    relevant_cards["units_high"].append(card)
            elif card.card_type == "Spell":
                relevant_cards["spells"].append(card)
            elif card.card_type == "Weapon":
                relevant_cards["weapons"].append(card)
            elif card.card_type == "Power":
                relevant_cards["powers"].append(card)
            elif card.card_type == "Relic":
                relevant_cards["relics"].append(card)
            elif card.card_type == "Site":
                relevant_cards["sites"].append(card)
        
        # Adicionar todas as outras cartas
        for card in cards_to_process:
            # Pular se já foi adicionada como obrigatória
            if card in required_cards_found:
                continue
                
            if card.card_type == "Unit":
                if card.cost <= 2:
                    relevant_cards["units_low"].append(card)
                elif card.cost <= 4:
                    relevant_cards["units_mid"].append(card)
                else:
                    relevant_cards["units_high"].append(card)
            elif card.card_type == "Spell":
                relevant_cards["spells"].append(card)
            elif card.card_type == "Weapon":
                relevant_cards["weapons"].append(card)
            elif card.card_type == "Power":
                relevant_cards["powers"].append(card)
            elif card.card_type == "Relic":
                relevant_cards["relics"].append(card)
            elif card.card_type == "Site":
                relevant_cards["sites"].append(card)
        
        # Usar facções permitidas pelos filtros
        factions_for_context = filters['allowed_factions']
        archetype_for_context = 'ALL CARDS'
        
    else:
        # MODO FILTRADO - Aplicar todos os filtros
        
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
        
        # Se nenhuma facção identificada, usar as permitidas
        if not factions_mentioned:
            factions_mentioned = filters['allowed_factions']
        
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
        scored_cards = [(card, calculate_relevance(card)) for card in cards_to_process]
        scored_cards.sort(key=lambda x: x[1], reverse=True)
        
        # Aplicar filtros antes de distribuir nas categorias
        filtered_cards = []
        
        for card, score in scored_cards:
            # 1. SEMPRE incluir cartas obrigatórias (verificar PRIMEIRO)
            if any(req.lower() == card.name.lower() for req in filters['required_cards']):
                filtered_cards.append((card, 100))  # Score máximo
                continue
            
            # 2. Verificar se a carta está banida (já foi removida em cards_to_process)
            
            # 3. Verificar facções permitidas
            if card.factions:  # Se a carta tem facções
                if not any(f in filters['allowed_factions'] for f in card.factions):
                    continue
            
            # 4. Verificar número máximo de facções
            if len(card.factions) > filters['max_factions']:
                continue
            
            # 5. Verificar filtro de mercado (CORRIGIDO)
            if not filters['use_market']:
                card_text_lower = card.text.lower()
                # Lista expandida de termos de mercado
                market_terms = [
                    'your market',
                    'bargain',
                    'from your market',
                    'into your market',
                    'market card',
                    'smuggler'  # Smugglers também acessam mercado
                ]
                
                # Excluir apenas se tem termo de mercado E não afeta mercado inimigo
                has_market_interaction = any(term in card_text_lower for term in market_terms)
                affects_enemy_market = any(term in card_text_lower for term in [
                    'their market',
                    'enemy market',
                    "opponent's market",
                    'each market'  # Afeta ambos
                ])
                
                if has_market_interaction and not affects_enemy_market:
                    continue
            
            # 6. IMPORTANTE: Se usar mercado, garantir que temos merchants/smugglers
            if filters['use_market']:
                # Dar boost para cartas que acessam mercado
                if any(term in card.text.lower() for term in ['your market', 'smuggler', 'merchant', 'bargain']):
                    score += 20  # Boost significativo
            
            # 7. Score mínimo mais permissivo
            min_score = 3  # Era 5
            
            # Sempre incluir powers (são essenciais)
            if card.card_type == "Power":
                filtered_cards.append((card, score))
            # Para outras cartas, aplicar score mínimo
            elif score >= min_score or len(scored_cards) <= 200:  # Era 100
                filtered_cards.append((card, score))
        
        # Debug
        st.info(f"🎯 Cartas após filtros: {len(filtered_cards)}")
        
        # Garantir que cartas obrigatórias estejam incluídas
        for req_card in required_cards_found:
            if not any(c[0].name == req_card.name for c in filtered_cards):
                filtered_cards.insert(0, (req_card, 100))
                st.warning(f"⚠️ Adicionando '{req_card.name}' que foi perdida nos filtros")

        # NOVO: Forçar inclusão das cartas de mercado PRIMEIRO
        if market_access_cards:
            st.info(f"🏪 Adicionando {len(market_access_cards)} cartas de mercado ao contexto...")
            
            for card in market_access_cards:
                # Adicionar à categoria apropriada
                if card.card_type == "Unit":
                    if card.cost <= 2:
                        relevant_cards["units_low"].append(card)
                    elif card.cost <= 4:
                        relevant_cards["units_mid"].append(card)
                    else:
                        relevant_cards["units_high"].append(card)
                elif card.card_type == "Spell":
                    relevant_cards["spells"].append(card)
                elif card.card_type == "Relic":
                    relevant_cards["relics"].append(card)
                
                # Remover da lista filtered_cards para evitar duplicação
                filtered_cards = [(c, s) for c, s in filtered_cards if c.name != card.name]
        
        # Distribuir cartas nas categorias
        for card, score in filtered_cards:
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
        
        # Definir variáveis para o contexto
        factions_for_context = factions_mentioned
        archetype_for_context = detected_archetype.upper()
    
    # FORMATAR CONTEXTO (comum para ambos os modos)
    context = f"CARTAS DISPONÍVEIS PARA {', '.join(factions_for_context)} {archetype_for_context}:\n\n"
    
    # Se temos cartas obrigatórias, destacá-las
    if required_cards_found:
        context += "⭐ CARTAS OBRIGATÓRIAS (devem ser incluídas no deck):\n"
        for card in required_cards_found:
            influence = format_influence(card)
            if card.card_type == "Unit":
                context += f"• {card.name} | {influence} | {card.attack}/{card.health} | {card.rarity}\n"
            else:
                context += f"• {card.name} | {influence} | {card.card_type} | {card.rarity}\n"
        context += "\n"
    
    context += "IMPORTANTE: Use EXATAMENTE as informações fornecidas abaixo. NÃO invente raridades ou influências.\n\n"
    
    # Adicionar estatísticas rápidas
    total_cards = sum(len(cards) for cards in relevant_cards.values())
    context += f"(Total: {total_cards} cartas selecionadas de {len(cards)} disponíveis)\n\n"
    
    # Se usar mercado, destacar cartas de acesso
    if filters['use_market']:
        market_access_cards = []
        for category in relevant_cards.values():
            for card in category:
                if any(term in card.text.lower() for term in ['your market', 'smuggler', 'merchant', 'bargain']):
                    market_access_cards.append(card)
        
        if market_access_cards:
            context += "=== CARTAS DE ACESSO AO MERCADO ===\n"
            for card in market_access_cards[:8]:
                influence = format_influence(card)
                context += f"• {card.name} | {influence} | "
                if card.card_type == "Unit":
                    context += f"{card.attack}/{card.health} | "
                context += f"{card.rarity} | Acessa mercado\n"
            context += "\n"
        else:
            context += "⚠️ ATENÇÃO: Mercado solicitado mas nenhuma carta de acesso encontrada!\n\n"
    
    # Continuar com o formato normal
    if relevant_cards["units_low"]:
        context += "=== EARLY GAME (1-2 custo) ===\n"
        for c in relevant_cards["units_low"]:
            influence = format_influence(c)
            context += f"• {c.name} | {influence} | {c.attack}/{c.health} | {c.rarity}"
            if c.text:
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
            stats = f"+{c.attack}/+{c.health}" if c.attack is not None and c.health is not None else "N/A"
            context += f"• {c.name} | {influence} | {stats} | {c.rarity}\n"
    
    if relevant_cards["powers"]:
        context += "\n=== POWER CARDS ===\n"
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
    # Coletar valores dos filtros
    filters = {
        'allowed_factions': [],
        'max_factions': st.session_state.get('max_factions', 2),
        'use_market': st.session_state.get('use_market', True),
        'required_cards': [card.strip() for card in st.session_state.get('required_cards', '').split('\n') if card.strip()],
        'banned_cards': [card.strip() for card in st.session_state.get('banned_cards', '').split('\n') if card.strip()],
        'filter_mode': st.session_state.get('filter_mode', 'Filtrar cartas relevantes')
    }
    
    # Coletar facções permitidas
    if st.session_state.get('filter_fire', True):
        filters['allowed_factions'].append('FIRE')
    if st.session_state.get('filter_time', True):
        filters['allowed_factions'].append('TIME')
    if st.session_state.get('filter_justice', True):
        filters['allowed_factions'].append('JUSTICE')
    if st.session_state.get('filter_primal', True):
        filters['allowed_factions'].append('PRIMAL')
    if st.session_state.get('filter_shadow', True):
        filters['allowed_factions'].append('SHADOW')
    
    # Se nenhuma facção selecionada, permitir todas
    if not filters['allowed_factions']:
        filters['allowed_factions'] = ['FIRE', 'TIME', 'JUSTICE', 'PRIMAL', 'SHADOW']
    
    # Preparar contexto
    cards_context = prepare_cards_context(cards, strategy, filters)
    
    # Prompt CAMPEÃO para todos os modelos
    prompt = f"""Você é um CAMPEÃO MUNDIAL de TCGs, especialista supremo em Eternal Card Game, com anos de experiência competitiva em torneios de alto nível. Sua missão é construir decks CAMPEÕES que dominam o meta competitivo.

=== REGRAS FUNDAMENTAIS DE CONSTRUÇÃO ===

REQUISITOS OBRIGATÓRIOS (NUNCA VIOLE ESTAS REGRAS):
1. Tamanho do Deck: EXATAMENTE 75-150 cartas (padrão competitivo: 75)
2. Proporção de Power: MÍNIMO 1/3 do deck (25+ em deck de 75)
3. Proporção de Não-Power: MÍNIMO 2/3 do deck (50+ em deck de 75)
4. Limite de Cópias: MÁXIMO 4 por carta (EXCETO Sigils básicos = ilimitados)
5. Validação: TODAS as cartas devem ter DeckBuildable=TRUE
6. Mercado: OPCIONAL - até 5 cartas únicas (requer cartas no deck principal que acessem, troquem, comprem ou copiem cartas do mercado), as cartas do mercado devem ser únicas e não podem ser repetidas no deck principal. Apenas 1 cópia de cada carta pode ser incluída no mercado. As 5 cartas do mercado devem ser escolhidas com base na sinergia com o deck principal e na estratégia geral. Elas são cartas extras que podem ser compradas durante o jogo, mas não fazem parte do deck principal, ou seja, são cartas adicionais ao deck principal, mas não contam para o total de 75 cartas. Exemplo, se o deck principal tiver 75 cartas, o mercado terá 5 cartas adicionais, totalizando 80 cartas jogáveis e no deck principal devemos ter ao menos 4 cartas que interajam com o mercado, como "your market", "Bargain", "Market Access", "Market Interaction" ou similares, para poder utilizar essas cartas que estão no mercado.
7. Ainda sobre o Mercado - Cartas NO MERCADO, não devem ser cartas que tenham "your market", "Bargain", "Market Access", "Market Interaction" ou similares, pois essas cartas só acessam o mercado a partir do deck principal, portanto, não devem ser incluídas no mercado, pois devem fazer parte do deck principal, sem essas cartas no deck principal não conseguimos comprar ou utilizar cartas do mercado e se elas estão dentro no mercado não faz sentido algum. O mercado é uma extensão do deck principal, mas as cartas que interagem com o mercado devem estar no deck principal. Podem ser incluidas quaisquer cartas válidas no mercado, desde que sejam únicas e que não estejam repetidas no deck principal.
8. Cartas Obrigatórias: Se solicitado, inclua cartas específicas (ex.: "4x Fire Sigil") e garanta que elas estejam no deck final.

VALIDAÇÃO MATEMÁTICA OBRIGATÓRIA:
- Some TODAS as quantidades: (X units + Y spells + Z weapons + W relics + P powers = 75)
- Verifique: Total ≥ 75, Powers ≥ 25, Não-Powers ≥ 50
- Se houver mercado, verifique se Mercado <= 5 e se o deck principal tem ao menos 4 cartas que interajam com o mercado.
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

    # NOVO: Sistema de Filtros Avançados
    st.markdown("---")
    with st.expander("🎛️ Filtros Avançados", expanded=False):
        
        # 1. Facções Permitidas
        st.markdown("#### Facções Permitidas")
        col1, col2 = st.columns(2)
        with col1:
            fire_allowed = st.checkbox("🔥 Fire", value=True, key="filter_fire")
            time_allowed = st.checkbox("⏰ Time", value=True, key="filter_time")
            justice_allowed = st.checkbox("⚖️ Justice", value=True, key="filter_justice")
        with col2:
            primal_allowed = st.checkbox("🌊 Primal", value=True, key="filter_primal")
            shadow_allowed = st.checkbox("💀 Shadow", value=True, key="filter_shadow")
        
        st.markdown("---")
        
        # 2. Número Máximo de Facções
        max_factions = st.selectbox(
            "**Número Máximo de Facções**",
            options=[1, 2, 3, 4, 5],
            index=1,  # Default: 2
            help="Limita cartas a no máximo X facções",
            key="max_factions"  # ADICIONAR
        )        
        
        # 3. Usar Mercado
        use_market = st.checkbox(
            "**Incluir Cartas de Mercado**",
            value=True,
            help="Desmarque para excluir cartas com 'your market' ou 'Bargain'",
            key="use_market"  # ADICIONAR
        )
        
        st.markdown("---")
        
        # 4. Cartas Obrigatórias
        st.markdown("#### Cartas Específicas")
        required_cards = st.text_area(
            "Cartas Obrigatórias (uma por linha):",
            height=100,  # Altura mínima corrigida
            help="Estas cartas sempre serão incluídas no contexto",
            placeholder="Ex:\nTorch\nHarsh Rule",
            key="required_cards"
        )
        
        # 5. Cartas Proibidas
        banned_cards = st.text_area(
            "Cartas Proibidas (uma por linha):",
            height=100,  # Altura mínima corrigida
            help="Estas cartas nunca serão incluídas",
            placeholder="Ex:\nSeek Power\nBore",
            key="banned_cards"
        )
        
        st.markdown("---")
        
        # 6. Modo de Filtragem
        filter_mode = st.radio(
            "**Modo de Filtragem**",
            ["Filtrar cartas relevantes", "Incluir todas as cartas"],
            index=0,
            help="Filtrar = IA focada | Todas = IA vê tudo",
            key="filter_mode"  # ADICIONAR
        )
    
    # 7. Exibir Exemplos de Estratégias   
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
st.caption("💡 Dica: Para melhores resultados, teste com o1 ou gpt-4.5-preview para análises mais precisas")