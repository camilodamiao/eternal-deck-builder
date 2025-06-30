"""Componentes de UI para o Streamlit"""
import streamlit as st
from typing import List
from data.models import Card, Deck, DeckCard
from config.constants import FACTIONS

def display_card(card: Card, show_quantity: bool = False, quantity: int = 1):
    """Exibir uma carta com formatação e imagem"""
    # Cor baseada na facção
    faction_colors = {
        'FIRE': '#FF4444',
        'TIME': '#FFD700', 
        'JUSTICE': '#90EE90',
        'PRIMAL': '#4169E1',
        'SHADOW': '#9370DB'
    }
    
    # Pegar cor da primeira facção
    color = faction_colors.get(card.factions[0] if card.factions else 'NEUTRAL', '#808080')
    
    # Layout com imagem
    if card.image_url:
        # Layout com 4 colunas: imagem, custo, info, stats
        col1, col2, col3, col4 = st.columns([1.5, 0.5, 3, 1])
        
        with col1:
            try:
                st.image(card.image_url, width=100)
            except:
                st.write("🖼️")  # Fallback se a imagem não carregar
        
        with col2:
            st.markdown(
                f"<div style='color: {color}; font-size: 24px; text-align: center; margin-top: 20px;'>"
                f"{card.cost}</div>", 
                unsafe_allow_html=True
            )
        
        with col3:
            # Nome e quantidade
            qty_text = f"{quantity}x " if show_quantity and quantity > 1 else ""
            st.markdown(f"**{qty_text}{card.name}**")
            
            # Tipo e raridade
            st.caption(f"{card.card_type} • {card.rarity}")
            
            # Texto da carta
            if card.text:
                st.caption(card.text[:100] + "..." if len(card.text) > 100 else card.text)
        
        with col4:
            if card.is_unit and card.attack is not None:
                st.markdown(f"**{card.attack}/{card.health}**")
            
            # Mostrar se não é deck buildable
            if not card.deck_buildable:
                st.caption("❌ Não jogável")
    
    else:
        # Layout sem imagem (fallback)
        col1, col2, col3 = st.columns([1, 3, 1])
        
        with col1:
            st.markdown(
                f"<div style='color: {color}; font-size: 24px; text-align: center;'>{card.cost}</div>", 
                unsafe_allow_html=True
            )
        
        with col2:
            qty_text = f"{quantity}x " if show_quantity and quantity > 1 else ""
            st.markdown(f"**{qty_text}{card.name}**")
            if card.text:
                st.caption(card.text[:100] + "..." if len(card.text) > 100 else card.text)
        
        with col3:
            if card.is_unit and card.attack is not None:
                st.markdown(f"**{card.attack}/{card.health}**")
            st.caption(card.card_type)

def display_deck_list(deck: Deck):
    """Exibir lista completa do deck"""
    # Separar por tipo
    units = [dc for dc in deck.main_deck if dc.card.is_unit]
    spells = [dc for dc in deck.main_deck if dc.card.card_type == "Spell"]
    powers = [dc for dc in deck.main_deck if dc.card.is_power]
    others = [dc for dc in deck.main_deck if dc.card.card_type not in ["Unit", "Spell", "Power"]]
    
    # Mostrar cada categoria
    if units:
        st.subheader(f"⚔️ Unidades ({sum(dc.quantity for dc in units)})")
        for dc in sorted(units, key=lambda x: (x.card.cost, x.card.name)):
            display_card(dc.card, show_quantity=True, quantity=dc.quantity)
    
    if spells:
        st.subheader(f"✨ Feitiços ({sum(dc.quantity for dc in spells)})")
        for dc in sorted(spells, key=lambda x: (x.card.cost, x.card.name)):
            display_card(dc.card, show_quantity=True, quantity=dc.quantity)
    
    if others:
        st.subheader(f"🎯 Outros ({sum(dc.quantity for dc in others)})")
        for dc in sorted(others, key=lambda x: (x.card.cost, x.card.name)):
            display_card(dc.card, show_quantity=True, quantity=dc.quantity)
    
    if powers:
        st.subheader(f"💎 Poder ({sum(dc.quantity for dc in powers)})")
        for dc in sorted(powers, key=lambda x: x.card.name):
            st.write(f"- {dc.quantity}x {dc.card.name}")
    
    # Mercado
    if deck.market:
        st.subheader(f"🏪 Mercado ({len(deck.market)})")
        for dc in sorted(deck.market, key=lambda x: (x.card.cost, x.card.name)):
            display_card(dc.card)

def display_deck_stats(deck: Deck):
    """Exibir estatísticas do deck"""
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total de Cartas", deck.total_cards)
    
    with col2:
        st.metric("Cartas de Poder", deck.power_count)
    
    with col3:
        power_ratio = (deck.power_count / deck.total_cards * 100) if deck.total_cards > 0 else 0
        st.metric("% de Poder", f"{power_ratio:.1f}%")
    
    with col4:
        avg_cost = deck.average_cost
        st.metric("Custo Médio", f"{avg_cost:.1f}")