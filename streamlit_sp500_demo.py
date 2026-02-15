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
    st.set_page_config(page_title="Analyse Actions", page_icon="📈", layout="wide")

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
        ["1mo", "3mo", "6mo", "1y", "2y", "5y"],
        index=3  # 1 an par défaut pour MA200
    )

    # Bouton d'analyse des croisements
    if st.sidebar.button("🔍 Détecter les croisements MA50/MA200"):
        # Vérifier si la période est suffisante pour MA200
        if periode in ["1mo", "3mo", "6mo"]:
            st.sidebar.warning("⚠️ Pour les croisements MA50/MA200, sélectionnez une période d'au moins 1 an")
            st.session_state.show_crossovers = False
        else:
            st.session_state.show_crossovers = True
    else:
        st.session_state.show_crossovers = st.session_state.get('show_crossovers', False)

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

    # Statistiques
    st.subheader("📈 Statistiques")
    col1, col2 = st.columns(2)

    with col1:
        st.write("**Moyennes mobiles**")
        data['MA20'] = data['Close'].rolling(window=20).mean()
        data['MA50'] = data['Close'].rolling(window=50).mean()

        ma_fig = px.line(
            data.tail(100).dropna(),  # 100 derniers jours sans NaN
            x=data.tail(100).dropna().index,
            y=['Close', 'MA20', 'MA50'],
            title="Prix et moyennes mobiles",
            labels={'value': 'Prix ($)', 'index': 'Date'}
        )
        st.plotly_chart(ma_fig, use_container_width=True)

    with col2:
        st.write("**Informations**")
        st.write(f"- **Période**: {periode}")
        st.write(f"- **Nombre de jours**: {len(data)}")
        st.write(f"- **Volatilité**: {data['Close'].pct_change().std() * 100:.2f}%")
        st.write(f"- **Rendement total**: {((data['Close'].iloc[-1] / data['Close'].iloc[0]) - 1) * 100:+.2f}%")

    # Section des croisements MA50/MA200
    if st.session_state.get('show_crossovers', False):
        st.subheader("🎯 Analyse des croisements MA50/MA200")

        golden_crosses, death_crosses = detecter_croisements_ma(data)

        col1, col2 = st.columns(2)

        with col1:
            st.write("**🟢 Golden Cross (Signal d'achat)**")
            if golden_crosses:
                for date in golden_crosses[-5:]:  # 5 derniers
                    prix = data.loc[date, 'Close']
                    st.write(f"- {date.strftime('%d/%m/%Y')} : {prix:.2f} $")
            else:
                st.write("Aucun Golden Cross détecté sur la période")

        with col2:
            st.write("**🔴 Death Cross (Signal de vente)**")
            if death_crosses:
                for date in death_crosses[-5:]:  # 5 derniers
                    prix = data.loc[date, 'Close']
                    st.write(f"- {date.strftime('%d/%m/%Y')} : {prix:.2f} $")
            else:
                st.write("Aucun Death Cross détecté sur la période")

        # Graphique avec croisements
        st.write("**Graphique avec signaux de trading**")
        data_ma = data.copy()
        data_ma['MA50'] = data_ma['Close'].rolling(window=50).mean()
        data_ma['MA200'] = data_ma['Close'].rolling(window=200).mean()

        fig_croisements = go.Figure()

        # Ajouter les lignes
        fig_croisements.add_trace(go.Scatter(
            x=data_ma.index, y=data_ma['Close'],
            mode='lines', name='Prix', line=dict(color='blue')
        ))
        fig_croisements.add_trace(go.Scatter(
            x=data_ma.index, y=data_ma['MA50'],
            mode='lines', name='MA50', line=dict(color='orange')
        ))
        fig_croisements.add_trace(go.Scatter(
            x=data_ma.index, y=data_ma['MA200'],
            mode='lines', name='MA200', line=dict(color='red')
        ))

        # Ajouter les marqueurs de croisements
        if golden_crosses:
            gc_dates = [date for date in golden_crosses if date in data_ma.index]
            gc_prices = [data_ma.loc[date, 'Close'] for date in gc_dates]
            fig_croisements.add_trace(go.Scatter(
                x=gc_dates, y=gc_prices,
                mode='markers',
                name='Golden Cross',
                marker=dict(color='green', size=10, symbol='triangle-up')
            ))

        if death_crosses:
            dc_dates = [date for date in death_crosses if date in data_ma.index]
            dc_prices = [data_ma.loc[date, 'Close'] for date in dc_dates]
            fig_croisements.add_trace(go.Scatter(
                x=dc_dates, y=dc_prices,
                mode='markers',
                name='Death Cross',
                marker=dict(color='red', size=10, symbol='triangle-down')
            ))

        fig_croisements.update_layout(
            title=f"Analyse technique {nom_action} - Croisements MA50/MA200",
            xaxis_title='Date',
            yaxis_title='Prix ($)',
            hovermode='x unified'
        )

        st.plotly_chart(fig_croisements, use_container_width=True)

        # Stratégie actuelle
        st.write("**📊 Stratégie actuelle**")
        dernier_ma50 = data_ma['MA50'].iloc[-1]
        dernier_ma200 = data_ma['MA200'].iloc[-1]

        if dernier_ma50 > dernier_ma200:
            st.success(f"🟢 tendance HAUSSIÈRE - MA50 ({dernier_ma50:.2f} $) > MA200 ({dernier_ma200:.2f} $)")
        else:
            st.error(f"🔴 tendance BAISSIÈRE - MA50 ({dernier_ma50:.2f} $) < MA200 ({dernier_ma200:.2f} $)")

if __name__ == "__main__":
    main()
