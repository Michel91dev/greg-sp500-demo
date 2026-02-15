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

# Lire la version depuis le fichier
def get_version():
    try:
        with open('version.txt', 'r') as f:
            return f.read().strip()
    except:
        return "1.0.0"

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
    st.set_page_config(page_title="Analyse Actions", page_icon="📈", layout="wide")

    # Afficher la version dans la sidebar
    st.sidebar.markdown(f"**Version : {version}**")
    st.sidebar.markdown("---")

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

    st.title(f"📈 {nom_action} Demo")
    st.markdown(f"Visualisation et analyse de {nom_action}")

    # Chargement des données
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

    # Moyennes mobiles - toujours MA50/MA200
    st.subheader("📈 Moyennes mobiles (MA50/MA200)")
    data['MA50'] = data['Close'].rolling(window=50).mean()
    data['MA200'] = data['Close'].rolling(window=200).mean()

    ma_fig = px.line(
        data.tail(200).dropna(),  # 200 derniers jours pour MA200
        x=data.tail(200).dropna().index,
        y=['Close', 'MA50', 'MA200'],
        title="Prix et moyennes mobiles (MA50/MA200)",
        labels={'value': 'Prix ($)', 'index': 'Date'}
    )
    st.plotly_chart(ma_fig, use_container_width=True)

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
