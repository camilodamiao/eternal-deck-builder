"""Agente LangChain para construir decks"""
from typing import Dict
from langchain_openai import ChatOpenAI
from langchain.agents import create_react_agent, AgentExecutor
from langchain.prompts import PromptTemplate
from langchain.memory import ConversationBufferMemory
from agents.tools import search_cards, validate_deck_rules, get_faction_powers
from config.settings import settings

# Template do prompt ReAct
DECK_BUILDER_PROMPT = """Você é um expert em Eternal Card Game especializado em construir decks competitivos.

IMPORTANTE: Use as ferramentas da seguinte forma:
- search_cards: Use parâmetros individuais como faction="Fire", max_cost=3, card_type="Unit"
- get_basic_aggro_package: Use para obter cartas aggro básicas
- get_faction_powers: Use para obter powers de uma facção específica
REGRAS FUNDAMENTAIS:
- Decks devem ter 75-150 cartas (padrão 75)
- Mínimo 1/3 devem ser power cards
- Máximo 4 cópias por carta (exceto Sigils)
- Formato Throne permite todas as cartas

Você tem acesso às seguintes ferramentas:

{tools}

Nomes das ferramentas disponíveis: {tool_names}

Use o seguinte formato:

Question: a pergunta que você deve responder
Thought: você deve sempre pensar sobre o que fazer
Action: a ação a tomar, deve ser uma de [{tool_names}]
Action Input: a entrada para a ação
Observation: o resultado da ação
... (este padrão Thought/Action/Action Input/Observation pode repetir N vezes)
Thought: Agora eu sei a resposta final
Final Answer: a resposta final para a pergunta original

Comece! Lembre-se de sempre usar o formato exato especificado acima.

Question: {input}
{agent_scratchpad}"""

class DeckBuilderAgent:
    def __init__(self):
        # LLM
        self.llm = ChatOpenAI(
            model="o4-mini",  # Começar com modelo mais barato para testes
            temperature=1,
            api_key=settings.OPENAI_API_KEY
        )
        
        # Ferramentas
        self.tools = [search_cards, validate_deck_rules, get_faction_powers]
        
        # Prompt
        self.prompt = PromptTemplate(
            template=DECK_BUILDER_PROMPT,
            input_variables=["input", "tools", "tool_names", "agent_scratchpad"]
        )
        
        # Memória simples (sem o deprecated ConversationBufferMemory)
        self.chat_history = []
        
        # Agente
        self.agent = create_react_agent(
            llm=self.llm,
            tools=self.tools,
            prompt=self.prompt
        )
        
        # Executor
        self.executor = AgentExecutor(
            agent=self.agent,
            tools=self.tools,
            verbose=True,
            max_iterations=10,
            handle_parsing_errors=True
        )
    
    def build_deck(self, strategy: str, detailed: bool = False) -> Dict:
        """Constrói um deck baseado na estratégia"""
        
        # Adicionar instruções sobre o modo de output
        prompt = strategy
        if detailed:
            prompt += "\n\nPor favor, forneça explicações detalhadas para cada escolha."
        else:
            prompt += "\n\nForneça apenas: lista de cartas no formato '4 Nome da Carta', estratégia resumida (2-3 linhas) e como jogar (3-4 pontos)."
        
        prompt += "\n\nLembre-se: o deck deve ter exatamente 75 cartas, com pelo menos 25 sendo power cards."
        
        # Executar agente
        try:
            result = self.executor.invoke({"input": prompt})
            output = result.get("output", "")
            
            # Salvar no histórico
            self.chat_history.append({
                "input": strategy,
                "output": output
            })
            
            return {
                "deck": output,
                "strategy": strategy,
                "detailed": detailed
            }
        except Exception as e:
            return {
                "deck": f"Erro ao gerar deck: {str(e)}",
                "strategy": strategy,
                "detailed": detailed
            }
    
    def ask_followup(self, question: str) -> str:
        """Responde perguntas sobre o deck gerado"""
        try:
            # Adicionar contexto do último deck
            if self.chat_history:
                last_deck = self.chat_history[-1]
                question = f"Sobre o deck anterior: {question}"
            
            result = self.executor.invoke({"input": question})
            return result.get("output", "")
        except Exception as e:
            return f"Erro ao responder: {str(e)}"