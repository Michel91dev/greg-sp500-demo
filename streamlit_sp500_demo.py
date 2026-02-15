# -*- coding: utf-8 -*-
"""
Petite démo Streamlit pour visualiser le S&P 500
"""

import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import numpy as np

# Lire la version depuis le fichier
def get_version():
    try:
        with open('version.txt', 'r') as f:
            return f.read().strip()
    except:
        return "2.0.0"

# Fonctions pour les indicateurs techniques
def calculate_rsi(data, period=14):
    """Calculer le RSI (Relative Strength Index)"""
    delta = data['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def calculate_macd(data, fast=12, slow=26, signal=9):
    """Calculer le MACD (Moving Average Convergence Divergence)"""
    ema_fast = data['Close'].ewm(span=fast).mean()
    ema_slow = data['Close'].ewm(span=slow).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal).mean()
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram

def calculate_bollinger_bands(data, period=20, std_dev=2):
    """Calculer les Bollinger Bands"""
    sma = data['Close'].rolling(window=period).mean()
    std = data['Close'].rolling(window=period).std()
    upper_band = sma + (std * std_dev)
    lower_band = sma - (std * std_dev)
    return sma, upper_band, lower_band

# Documentation des indicateurs
def get_indicator_docs():
    """Retourner la documentation des indicateurs"""
    docs = {
        "MA50/MA200": """
        **Moyennes Mobiles (MA50/MA200)**

        **Qu'est-ce que c'est ?**
        Les moyennes mobiles lissent les prix pour montrer la tendance sur une période.

        **MA50** : Moyenne des 50 derniers jours (tendance à moyen terme)
        **MA200** : Moyenne des 200 derniers jours (tendance à long terme)

        **Signaux :**
        - 🟢 **Golden Cross** : MA50 passe au-dessus de MA200 = SIGNAL D'ACHAT
        - 🔴 **Death Cross** : MA50 passe en dessous de MA200 = SIGNAL DE VENTE

        **Pourquoi ça marche ?**
        Les institutionnels utilisent ces niveaux pour prendre des décisions,
        donc quand les courbes se croisent, beaucoup d'argent bouge en même temps.
        """,

        "RSI": """
        **RSI (Relative Strength Index)**

        **Qu'est-ce que c'est ?**
        Indicateur de momentum qui mesure si l'action est surachetée ou survendue.
        Échelle de 0 à 100.

        **Signaux :**
        - 🔴 **Surachat** (>70) : L'action est trop chère, risque de baisse
        - 🟢 **Survente** (<30) : L'action est bon marché, risque de hausse
        - 🟡 **Neutre** (30-70) : Zone normale

        **Pourquoi ça marche ?**
        Quand tout le monde achète (RSI > 70), il n'y a plus d'acheteurs.
        Quand tout le monde vend (RSI < 30), les acheteurs reviennent.
        """,

        "MACD": """
        **MACD (Moving Average Convergence Divergence)**

        **Qu'est-ce que c'est ?**
        Indicateur qui suit la tendance et le momentum en même temps.

        **Composantes :**
        - **Ligne MACD** (bleue) : Différence entre moyennes rapides/lentes
        - **Ligne de signal** (orange) : Moyenne de la ligne MACD
        - **Histogramme** : Distance entre les deux lignes

        **Signaux :**
        - 🟢 **Achat** : Ligne MACD croise la ligne de signal vers le haut
        - 🔴 **Vente** : Ligne MACD croise la ligne de signal vers le bas

        **Pourquoi ça marche ?**
        Combine tendance (direction) et momentum (force) pour des signaux plus fiables.
        """,

        "Bollinger": """
        **Bollinger Bands**

        **Qu'est-ce que c'est ?**
        Bandes qui entourent le prix, basées sur la volatilité.

        **Composantes :**
        - **Bande du milieu** : Moyenne mobile sur 20 jours
        - **Bandes sup/inf** : ±2 écarts-types (95% des prix)

        **Signaux :**
        - 🟢 **Achat** : Prix touche la bande inférieure
        - 🔴 **Vente** : Prix touche la bande supérieure
        - 🟡 **Squeeze** : Bandes rétrécies = grosse variation à venir

        **Pourquoi ça marche ?**
        Les prix reviennent toujours vers leur moyenne (régression à la moyenne).
        """
    }
    return docs

def detecter_croisements_ma(data):
    """Détecte les croisements MA50/MA200"""
    # Calculer les moyennes mobiles
    data['MA50'] = data['Close'].rolling(window=50).mean()
    data['MA200'] = data['Close'].rolling(window=200).mean()

    # Supprimer les valeurs NaN
    data_clean = data.dropna()

    if len(data_clean) < 2:
        return [], []

    # Détecter les croisements
    golden_crosses = []  # MA50 croise MA200 vers le haut (signal d'achat)
    death_crosses = []   # MA50 croise MA200 vers le bas (signal de vente)

    for i in range(1, len(data_clean)):
        prev_ma50 = data_clean['MA50'].iloc[i-1]
        prev_ma200 = data_clean['MA200'].iloc[i-1]
        curr_ma50 = data_clean['MA50'].iloc[i]
        curr_ma200 = data_clean['MA200'].iloc[i]

        # Golden Cross: MA50 passe au-dessus de MA200
        if prev_ma50 <= prev_ma200 and curr_ma50 > curr_ma200:
            golden_crosses.append(data_clean.index[i])

        # Death Cross: MA50 passe en dessous de MA200
        elif prev_ma50 >= prev_ma200 and curr_ma50 < curr_ma200:
            death_crosses.append(data_clean.index[i])

    return golden_crosses, death_crosses

def main():
    version = get_version()
    docs = get_indicator_docs()

    st.set_page_config(page_title="Analyse Actions", page_icon="📈", layout="wide")

    # Sidebar avec documentation
    st.sidebar.markdown(f"**Version : {version}**")
    st.sidebar.markdown("---")

    # Bouton d'aide
    show_help = st.sidebar.button("❓ Aide & Documentation")

    if show_help:
        st.sidebar.markdown("## 📚 Documentation des Indicateurs")

        indicator_choice = st.sidebar.selectbox(
            "Choisir un indicateur :",
            ["MA50/MA200", "RSI", "MACD", "Bollinger"]
        )

        st.sidebar.markdown(docs[indicator_choice])
        st.sidebar.markdown("---")
        st.sidebar.markdown("*💡 Astuce : Lisez la documentation pour comprendre comment utiliser chaque indicateur !*")

    # Configuration sidebar
    st.sidebar.header("Paramètres")

    # Choix entre S&P 500 ou action personnalisée
    mode = st.sidebar.radio("Mode d'analyse", ["S&P 500", "Action personnalisée"])

    if mode == "S&P 500":
        ticker_symbol = "^GSPC"
        nom_action = "S&P 500"
    else:
        ticker_input = st.sidebar.text_input("Ticker de l'action (ex: AAPL, GOOGL, MSFT)", value="AAPL").upper()
        ticker_symbol = ticker_input
        nom_action = ticker_input

        # Validation du ticker
        if not ticker_input:
            st.sidebar.error("Veuillez entrer un ticker valide")
            st.stop()

    periode = st.sidebar.selectbox(
        "Période",
        ["1y", "2y", "5y"],
        index=0  # 1 an par défaut pour MA200
    )

    # Sélection des indicateurs à afficher
    st.sidebar.subheader("📊 Indicateurs techniques")
    show_ma = st.sidebar.checkbox("MA50/MA200", value=True, help="Moyennes mobiles pour la tendance")
    show_rsi = st.sidebar.checkbox("RSI", value=True, help="Surachat/Survente")
    show_macd = st.sidebar.checkbox("MACD", value=True, help="Tendance et momentum")
    show_bollinger = st.sidebar.checkbox("Bollinger Bands", value=False, help="Volatilité")

    st.title(f"📈 Dashboard d'investissements Michel, Romain et Roger")
    st.markdown(f"Analyse technique de {nom_action}")

    # Chargement des données (d'abord pour avoir prix_actuel)
    with st.spinner(f"Chargement des données de {nom_action}..."):
        try:
            # Ticker de l'action
            ticker = yf.Ticker(ticker_symbol)
            data = ticker.history(period=periode)

            if data.empty:
                st.error(f"Impossible de charger les données pour {ticker_symbol}. Vérifiez le ticker et votre connexion.")
                return

        except Exception as e:
            st.error(f"Erreur lors du chargement: {e}")
            return

    # Métriques principales
    col1, col2, col3, col4 = st.columns(4)

    prix_actuel = data['Close'].iloc[-1]
    prix_precedent = data['Close'].iloc[-2] if len(data) > 1 else prix_actuel
    variation = ((prix_actuel - prix_precedent) / prix_precedent) * 100

    col1.metric("Prix Actuel", f"{prix_actuel:.2f} $")
    col2.metric("Variation", f"{variation:+.2f}%", delta=f"{variation:+.2f}%")
    col3.metric("Plus Haut", f"{data['High'].max():.2f} $")
    col4.metric("Plus Bas", f"{data['Low'].min():.2f} $")

    # Recommandation de trading avec croisements (en premier)
    st.subheader("🎯 Recommandation de trading")

    # Calculer les moyennes mobiles pour la recommandation
    data['MA50'] = data['Close'].rolling(window=50).mean()
    data['MA200'] = data['Close'].rolling(window=200).mean()
    dernier_ma50 = data['MA50'].iloc[-1]
    dernier_ma200 = data['MA200'].iloc[-1]

    # Détecter les croisements récents
    golden_crosses, death_crosses = detecter_croisements_ma(data)

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        if prix_actuel > dernier_ma50 > dernier_ma200:
            st.success("🟢 **ACHETER**")
            st.write("Tendance haussière confirmée")
        elif prix_actuel < dernier_ma50 < dernier_ma200:
            st.error("🔴 **VENDRE**")
            st.write("Tendance baissière confirmée")
        else:
            st.warning("🟡 **ATTENTE**")
            st.write("Tendance incertaine")

    with col2:
        st.write("**Signaux MA**")
        st.write(f"- Prix vs MA50: {'✅' if prix_actuel > dernier_ma50 else '❌'}")
        st.write(f"- MA50 vs MA200: {'✅' if dernier_ma50 > dernier_ma200 else '❌'}")
        st.write(f"- Volatilité: {data['Close'].pct_change().std() * 100:.1f}%")

    with col3:
        st.write("**Croisements récents**")
        if golden_crosses:
            dernier_gc = golden_crosses[-1]
            st.write(f"🟢 GC: {dernier_gc.strftime('%d/%m/%Y')}")
        else:
            st.write("🟢 GC: Aucun")
        if death_crosses:
            dernier_dc = death_crosses[-1]
            st.write(f"🔴 DC: {dernier_dc.strftime('%d/%m/%Y')}")
        else:
            st.write("🔴 DC: Aucun")

    with col4:
        st.write("**Niveaux clés**")
        st.write(f"- Support: {data['Low'].tail(20).min():.2f} $")
        st.write(f"- Résistance: {data['High'].tail(20).max():.2f} $")
        st.write(f"- Rendement 50j: {((prix_actuel / data['Close'].iloc[-50]) - 1) * 100:+.1f}%")

    st.markdown("---")

    # Graphiques des indicateurs sélectionnés
    if show_ma:
        st.subheader("📈 Moyennes mobiles (MA50/MA200)")
        data['MA50'] = data['Close'].rolling(window=50).mean()
        data['MA200'] = data['Close'].rolling(window=200).mean()

        # Créer le graphique avec marqueurs de croisements
        fig_ma = go.Figure()

        # Ajouter les lignes
        fig_ma.add_trace(go.Scatter(
            x=data.index, y=data['Close'],
            mode='lines', name='Prix', line=dict(color='blue', width=2)
        ))
        fig_ma.add_trace(go.Scatter(
            x=data.index, y=data['MA50'],
            mode='lines', name='MA50', line=dict(color='orange', width=2)
        ))
        fig_ma.add_trace(go.Scatter(
            x=data.index, y=data['MA200'],
            mode='lines', name='MA200', line=dict(color='red', width=2)
        ))

        # Ajouter les marqueurs de croisements
        golden_crosses, death_crosses = detecter_croisements_ma(data)

        if golden_crosses:
            gc_dates = [date for date in golden_crosses if date in data.index]
            gc_prices = [data.loc[date, 'Close'] for date in gc_dates]
            fig_ma.add_trace(go.Scatter(
                x=gc_dates, y=gc_prices,
                mode='markers',
                name='🟢 Golden Cross',
                marker=dict(color='green', size=12, symbol='triangle-up')
            ))

        if death_crosses:
            dc_dates = [date for date in death_crosses if date in data.index]
            dc_prices = [data.loc[date, 'Close'] for date in dc_dates]
            fig_ma.add_trace(go.Scatter(
                x=dc_dates, y=dc_prices,
                mode='markers',
                name='🔴 Death Cross',
                marker=dict(color='red', size=12, symbol='triangle-down')
            ))

        fig_ma.update_layout(
            title="Prix et moyennes mobiles avec croisements",
            xaxis_title='Date',
            yaxis_title='Prix ($)',
            hovermode='x unified',
            height=500
        )

        st.plotly_chart(fig_ma, use_container_width=True)

        # Commentaires sur les croisements
        if golden_crosses or death_crosses:
            st.write("**💬 Derniers signaux de croisement :**")
            if golden_crosses:
                dernier_gc = golden_crosses[-1]
                st.success(f"🟢 **Golden Cross** le {dernier_gc.strftime('%d/%m/%Y')} : Signal d'achat fort")
            if death_crosses:
                dernier_dc = death_crosses[-1]
                st.error(f"🔴 **Death Cross** le {dernier_dc.strftime('%d/%m/%Y')} : Signal de vente fort")

    if show_rsi:
        st.subheader("📊 RSI (Relative Strength Index)")
        rsi = calculate_rsi(data)

        fig_rsi = go.Figure()

        # Zone de surachat/survente
        fig_rsi.add_hline(y=70, line_dash="dash", line_color="red", annotation_text="Surachat (>70)")
        fig_rsi.add_hline(y=30, line_dash="dash", line_color="green", annotation_text="Survente (<30)")
        fig_rsi.add_hline(y=50, line_dash="dash", line_color="gray", annotation_text="Neutre")

        # Ligne RSI
        fig_rsi.add_trace(go.Scatter(
            x=rsi.index, y=rsi.values,
            mode='lines', name='RSI', line=dict(color='purple', width=2)
        ))

        # Colorier les zones
        fig_rsi.add_trace(go.Scatter(
            x=rsi.index, y=[70]*len(rsi),
            mode='lines', fill='tonexty', fillcolor='rgba(255,0,0,0.1)',
            name='Zone surachat', showlegend=False
        ))

        fig_rsi.update_layout(
            title="RSI - Zones de surachat/survente",
            xaxis_title='Date',
            yaxis_title='RSI (0-100)',
            yaxis=dict(range=[0, 100]),
            height=400
        )

        st.plotly_chart(fig_rsi, use_container_width=True)

        # Analyse RSI actuel
        rsi_actuel = rsi.iloc[-1]
        if rsi_actuel > 70:
            st.error(f"🔴 **RSI = {rsi_actuel:.1f}** : Zone de surachat - Attention à une baisse possible")
        elif rsi_actuel < 30:
            st.success(f"🟢 **RSI = {rsi_actuel:.1f}** : Zone de survente - Opportunité d'achat possible")
        else:
            st.info(f"🟡 **RSI = {rsi_actuel:.1f}** : Zone neutre - Pas de signal clair")

    if show_macd:
        st.subheader("📈 MACD (Moving Average Convergence Divergence)")
        macd_line, signal_line, histogram = calculate_macd(data)

        fig_macd = go.Figure()

        # Histogramme
        colors = ['green' if x >= 0 else 'red' for x in histogram]
        fig_macd.add_trace(go.Bar(
            x=histogram.index, y=histogram.values,
            name='Histogramme', marker_color=colors, opacity=0.6
        ))

        # Lignes MACD et Signal
        fig_macd.add_trace(go.Scatter(
            x=macd_line.index, y=macd_line.values,
            mode='lines', name='MACD', line=dict(color='blue', width=2)
        ))
        fig_macd.add_trace(go.Scatter(
            x=signal_line.index, y=signal_line.values,
            mode='lines', name='Signal', line=dict(color='orange', width=2)
        ))

        fig_macd.update_layout(
            title="MACD - Signaux de tendance et momentum",
            xaxis_title='Date',
            yaxis_title='MACD',
            height=400
        )

        st.plotly_chart(fig_macd, use_container_width=True)

        # Analyse MACD actuelle
        macd_actuel = macd_line.iloc[-1]
        signal_actuel = signal_line.iloc[-1]
        if macd_actuel > signal_actuel:
            st.success(f"🟢 **MACD ({macd_actuel:.3f}) > Signal ({signal_actuel:.3f})** : Tendance haussière")
        else:
            st.error(f"🔴 **MACD ({macd_actuel:.3f}) < Signal ({signal_actuel:.3f})** : Tendance baissière")

    if show_bollinger:
        st.subheader("📊 Bollinger Bands")
        sma, upper_band, lower_band = calculate_bollinger_bands(data)

        fig_bb = go.Figure()

        # Bandes de Bollinger
        fig_bb.add_trace(go.Scatter(
            x=upper_band.index, y=upper_band.values,
            mode='lines', name='Bande supérieure', line=dict(color='red', width=1),
            fill=None
        ))
        fig_bb.add_trace(go.Scatter(
            x=lower_band.index, y=lower_band.values,
            mode='lines', name='Bande inférieure', line=dict(color='red', width=1),
            fill='tonexty', fillcolor='rgba(255,0,0,0.1)'
        ))
        fig_bb.add_trace(go.Scatter(
            x=sma.index, y=sma.values,
            mode='lines', name='Moyenne (20j)', line=dict(color='blue', width=2)
        ))
        fig_bb.add_trace(go.Scatter(
            x=data.index, y=data['Close'],
            mode='lines', name='Prix', line=dict(color='black', width=2)
        ))

        fig_bb.update_layout(
            title="Bollinger Bands - Zones de surachat/survente",
            xaxis_title='Date',
            yaxis_title='Prix ($)',
            height=400
        )

        st.plotly_chart(fig_bb, use_container_width=True)

        # Analyse Bollinger actuelle
        prix_actuel = data['Close'].iloc[-1]
        upper_actuel = upper_band.iloc[-1]
        lower_actuel = lower_band.iloc[-1]

        if prix_actuel > upper_actuel:
            st.error(f"🔴 **Prix ({prix_actuel:.2f} $) > Bande sup ({upper_actuel:.2f} $)** : Surachat - Risque de baisse")
        elif prix_actuel < lower_actuel:
            st.success(f"🟢 **Prix ({prix_actuel:.2f} $) < Bande inf ({lower_actuel:.2f} $)** : Survente - Opportunité d'achat")
        else:
            st.info(f"🟡 **Prix ({prix_actuel:.2f} $) dans les bandes** : Zone normale")

    # Recommandation de trading avec croisements
    st.subheader("🎯 Recommandation de trading")
    dernier_ma50 = data['MA50'].iloc[-1]
    dernier_ma200 = data['MA200'].iloc[-1]

    # Détecter les croisements récents
    golden_crosses, death_crosses = detecter_croisements_ma(data)

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        if prix_actuel > dernier_ma50 > dernier_ma200:
            st.success("🟢 **ACHETER**")
            st.write("Tendance haussière confirmée")
        elif prix_actuel < dernier_ma50 < dernier_ma200:
            st.error("🔴 **VENDRE**")
            st.write("Tendance baissière confirmée")
        else:
            st.warning("🟡 **ATTENTE**")
            st.write("Tendance incertaine")

    with col2:
        st.write("**Signaux MA**")
        st.write(f"- Prix vs MA50: {'✅' if prix_actuel > dernier_ma50 else '❌'}")
        st.write(f"- MA50 vs MA200: {'✅' if dernier_ma50 > dernier_ma200 else '❌'}")
        st.write(f"- Volatilité: {data['Close'].pct_change().std() * 100:.1f}%")

    with col3:
        st.write("**Croisements récents**")
        if golden_crosses:
            dernier_gc = golden_crosses[-1]
            st.write(f"🟢 GC: {dernier_gc.strftime('%d/%m/%Y')}")
        else:
            st.write("🟢 GC: Aucun")
        if death_crosses:
            dernier_dc = death_crosses[-1]
            st.write(f"🔴 DC: {dernier_dc.strftime('%d/%m/%Y')}")
        else:
            st.write("🔴 DC: Aucun")

    with col4:
        st.write("**Niveaux clés**")
        st.write(f"- Support: {data['Low'].tail(20).min():.2f} $")
        st.write(f"- Résistance: {data['High'].tail(20).max():.2f} $")
        st.write(f"- Rendement 50j: {((prix_actuel / data['Close'].iloc[-50]) - 1) * 100:+.1f}%")

    # Statistiques
    st.subheader("📈 Statistiques")
    col1, col2 = st.columns(2)

    with col1:
        st.write("**Informations**")
        st.write(f"- **Période**: {periode}")
        st.write(f"- **Nombre de jours**: {len(data)}")
        st.write(f"- **Volatilité**: {data['Close'].pct_change().std() * 100:.2f}%")
        st.write(f"- **Rendement total**: {((data['Close'].iloc[-1] / data['Close'].iloc[0]) - 1) * 100:+.2f}%")

    with col2:
        st.write("**Volume**")
        st.write(f"- **Volume moyen**: {data['Volume'].mean():,.0f}")
        st.write(f"- **Volume total**: {data['Volume'].sum():,.0f}")

    # Graphique principal
    st.subheader("📊 Évolution du prix")
    fig = px.line(
        data,
        x=data.index,
        y='Close',
        title=f"S&P 500 - {periode}",
        labels={'Close': 'Prix ($)', 'index': 'Date'}
    )
    fig.update_layout(hovermode='x unified')
    st.plotly_chart(fig, use_container_width=True)

    # Volume
    st.subheader("📊 Volume de transactions")
    fig_volume = px.bar(
        data,
        x=data.index,
        y='Volume',
        title="Volume quotidien",
        labels={'Volume': 'Volume', 'index': 'Date'}
    )
    st.plotly_chart(fig_volume, use_container_width=True)

if __name__ == "__main__":
    main()
