# -*- coding: utf-8 -*-
"""
Petite démo Streamlit pour visualiser le S&P 500
"""

import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta

def main():
    st.set_page_config(page_title="S&P 500 Demo", page_icon="📈", layout="wide")

    st.title("📈 S&P 500 Demo")
    st.markdown("Visualisation simple de l'indice S&P 500")

    # Configuration sidebar
    st.sidebar.header("Paramètres")
    periode = st.sidebar.selectbox(
        "Période",
        ["1mo", "3mo", "6mo", "1y", "2y", "5y"],
        index=2
    )

    # Chargement des données
    with st.spinner("Chargement des données du S&P 500..."):
        try:
            # Ticker S&P 500
            sp500 = yf.Ticker("^GSPC")
            data = sp500.history(period=periode)

            if data.empty:
                st.error("Impossible de charger les données. Vérifiez votre connexion.")
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

if __name__ == "__main__":
    main()
