"""Constantes do Eternal Card Game"""

# Facções
FACTIONS = {
    'FIRE': {'name': 'Fire', 'color': '#FF4444', 'symbol': '🔥'},
    'TIME': {'name': 'Time', 'color': '#FFD700', 'symbol': '⏰'},
    'JUSTICE': {'name': 'Justice', 'color': '#90EE90', 'symbol': '⚖️'},
    'PRIMAL': {'name': 'Primal', 'color': '#4169E1', 'symbol': '🌊'},
    'SHADOW': {'name': 'Shadow', 'color': '#9370DB', 'symbol': '💀'}
}

# Tipos de carta
CARD_TYPES = ['Unit', 'Spell', 'Power', 'Relic', 'Weapon', 'Curse', 'Site']

# Regras básicas
DECK_RULES = {
    'MIN_CARDS': 75,
    'MAX_CARDS': 150,
    'MIN_POWER_RATIO': 1/3,
    'MAX_COPIES': 4,
    'MARKET_SIZE': 5
}
