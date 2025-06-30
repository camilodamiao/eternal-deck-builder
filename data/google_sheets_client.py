"""Cliente para conexão com Google Sheets"""
import gspread
from google.oauth2.service_account import Credentials
from typing import List, Dict, Any, Optional
from data.models import Card
import os
from dotenv import load_dotenv

load_dotenv()

class GoogleSheetsClient:
    """Cliente simplificado para Google Sheets"""
    
    def __init__(self):
        self.client = None
        self.sheet = None
        self._connect()
    
    def _connect(self):
        """Conectar ao Google Sheets"""
        try:
            # Credenciais
            creds = Credentials.from_service_account_file(
                os.getenv('GOOGLE_SHEETS_CREDENTIALS_PATH'),
                scopes=[
                    'https://www.googleapis.com/auth/spreadsheets',
                    'https://www.googleapis.com/auth/drive'
                ]
            )
            
            # Conectar
            self.client = gspread.authorize(creds)
            self.sheet = self.client.open_by_key(os.getenv('GOOGLE_SHEETS_ID'))
            print("✅ Conectado ao Google Sheets")
            
        except Exception as e:
            print(f"❌ Erro ao conectar: {e}")
            raise
    
    def get_sample_cards(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Buscar algumas cartas de exemplo"""
        try:
            # Pegar a primeira aba
            worksheet = self.sheet.get_worksheet(0)
            
            # Pegar cabeçalhos
            headers = worksheet.row_values(1)
            print(f"📋 Colunas encontradas: {len(headers)}")
            
            # Pegar algumas linhas de exemplo
            all_values = worksheet.get_all_values()
            
            # Converter para lista de dicionários
            cards = []
            for i in range(1, min(limit + 1, len(all_values))):
                row = all_values[i]
                card_dict = {}
                for j, header in enumerate(headers):
                    if j < len(row):
                        card_dict[header] = row[j]
                cards.append(card_dict)
            
            return cards
            
        except Exception as e:
            print(f"❌ Erro ao buscar cartas: {e}")
            return []
    
    def parse_card(self, row_data: Dict[str, Any]) -> Optional[Card]:
        """Converter linha do Sheets em Card"""
        try:
            # Mapear colunas para nosso modelo
            name = row_data.get('Name', '')
            if not name:
                return None
            
            # Verificar se é deck buildable
            deck_buildable_str = row_data.get('DeckBuildable', 'TRUE')
            deck_buildable = deck_buildable_str.upper() == 'TRUE'
            
            # Parsear custo
            cost = 0
            cost_str = row_data.get('Cost', '0')
            if cost_str and str(cost_str).isdigit():
                cost = int(cost_str)
            
            # Parsear tipo
            card_type = row_data.get('Type', 'Unit')
            
            # Parsear influência (formato {F} ou {FF} etc)
            influence = {}
            influence_str = row_data.get('Influence', '')
            if influence_str:
                # Contar ocorrências de cada letra
                if 'F' in influence_str:
                    influence['FIRE'] = influence_str.count('F')
                if 'T' in influence_str:
                    influence['TIME'] = influence_str.count('T')
                if 'J' in influence_str:
                    influence['JUSTICE'] = influence_str.count('J')
                if 'P' in influence_str:
                    influence['PRIMAL'] = influence_str.count('P')
                if 'S' in influence_str:
                    influence['SHADOW'] = influence_str.count('S')
            
            # Determinar facções baseado na influência
            factions = list(influence.keys())
            
            # Pegar raridade
            rarity = row_data.get('Rarity', 'Common')
            if not rarity:
                rarity = 'Common'
            
            # Criar carta
            card = Card(
                name=name,
                cost=cost,
                influence=influence,
                card_type=card_type,
                factions=factions,
                text=row_data.get('CardText', ''),
                rarity=rarity,
                deck_buildable=deck_buildable,
                image_url=row_data.get('ImageUrl', '')
            )
            
            # Adicionar attack/health se for unidade
            if card.is_unit:
                attack_str = row_data.get('Attack', '')
                health_str = row_data.get('Health', '')
                if attack_str and str(attack_str).isdigit():
                    card.attack = int(attack_str)
                if health_str and str(health_str).isdigit():
                    card.health = int(health_str)
            
            # Adicionar set_number e eternal_id
            if 'SetNumber' in row_data:
                card.set_number = row_data.get('SetNumber', '1')

            if 'EternalID' in row_data:
                card.eternal_id = row_data.get('EternalID', '1')
            
            return card
            
        except Exception as e:
            print(f"⚠️ Erro ao parsear carta {row_data.get('Name', 'Unknown')}: {e}")
            return None
        
    def get_all_cards(self) -> List[Card]:
        """Buscar TODAS as cartas jogáveis da planilha"""
        try:
            worksheet = self.sheet.get_worksheet(0)
            headers = worksheet.row_values(1)
            all_values = worksheet.get_all_values()
            
            cards = []
            # Começar da linha 2 (pular header)
            for i in range(1, len(all_values)):
                row = all_values[i]
                card_dict = {}
                for j, header in enumerate(headers):
                    if j < len(row):
                        card_dict[header] = row[j]
                
                # Parsear carta
                card = self.parse_card(card_dict)
                # Só adicionar cartas jogáveis
                if card and card.deck_buildable:
                    cards.append(card)
            
            print(f"✅ {len(cards)} cartas jogáveis carregadas")
            return cards
            
        except Exception as e:
            print(f"❌ Erro ao buscar todas as cartas: {e}")
            return []

    def search_cards(self, 
                    cards: List[Card],
                    name_query: str = "",
                    factions: List[str] = None,
                    card_types: List[str] = None,
                    max_cost: int = None,
                    text_contains: str = "",
                    require_all_factions: bool = False,
                    exclude_multifaction: bool = False) -> List[Card]:
    
        """Filtrar cartas baseado em critérios"""
        
        results = cards
        
        # Filtro por nome
        if name_query:
            query_lower = name_query.lower()
            results = [c for c in results if query_lower in c.name.lower()]
        
        # Filtro por facções
        if factions:
            if require_all_factions:
                # Modo AND: carta deve ter TODAS as facções selecionadas
                results = [c for c in results if all(f in c.factions for f in factions)]
            else:
                # Modo OR: carta deve ter PELO MENOS UMA das facções selecionadas
                results = [c for c in results if any(f in c.factions for f in factions)]
            # Se exclude_multifaction está ativo e temos apenas uma facção selecionada
            if exclude_multifaction and len(factions) == 1:
                # Filtrar apenas cartas mono-facção
                results = [c for c in results if len(c.factions) == 1]
            
        # Filtro por tipos
        if card_types:
            results = [c for c in results if c.card_type in card_types]
        
        # Filtro por custo máximo
        if max_cost is not None:
            results = [c for c in results if c.cost <= max_cost]
        
        # Filtro por texto
        if text_contains:
            text_lower = text_contains.lower()
            results = [c for c in results if text_lower in c.text.lower()]
        
        return results
        