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
from concurrent.futures import ThreadPoolExecutor

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
    st.sidebar.markdown("## 📈 Site d'analyse d'actions")
    st.sidebar.markdown("*Pour Romain, Roger et Michel*")
    st.sidebar.markdown(f"**Version : {version}**")

    couleurs_utilisateur = {"Michel": "#4682B4", "Romain": "#9370DB", "Roger": "#DAA520"}

    st.sidebar.subheader("👤 Utilisateur")
    utilisateur = st.sidebar.radio(
        "Choisir :",
        ["Michel", "Romain", "Roger"],
        key="utilisateur",
        horizontal=True,
        label_visibility="collapsed"
    )

    # Bandeau utilisateur actif
    st.sidebar.markdown(
        f'<div style="background-color:{couleurs_utilisateur[utilisateur]};color:white;'
        f'padding:4px 8px;border-radius:4px;text-align:center;font-weight:bold;">'
        f'👤 {utilisateur}</div>',
        unsafe_allow_html=True
    )

    # ISIN des actions pour affichage optionnel
    isin_actions = {
        "^GSPC": "ISIN inconnu",
        "SATS": "US2787681061",
        "DBX": "US2574671090",
        "COIN": "US1911021031",
        "PYPL": "US70450Y1038",
        "ZM": "US98156N1067",
        "MSFT": "US5949181044",
        "AAPL": "US0378331005",
        "TSLA": "US90384T1077",
        "NFLX": "US6311021038",
        "AMZN": "US0231351067",
        "FGR.PA": "FR0000035093",
        "SOI.PA": "FR0000121663",
        "PSP5.PA": "FR0011871128",
        "PCEU.PA": "FR0013412038",
        "STMPA.PA": "FR0000124141",
        "DSY.PA": "FR0000124141",
        "DEEZR.PA": "FR001400AYG6",
        "FORSE.PA": "FR0014005SB3",
        "LSG.OL": "NO0003096208",
        "BAYN.DE": "DE000BAY0017",
        "C50.PA": "LU1681047236",
        "PAASI.PA": "FR0013412012",
        "VIE.PA": "FR0000124141",
        "CHIP.PA": "LU1900066033",
        "PAEEM.PA": "FR0013412020",
        "AM.PA": "FR0014004L86",
        "WPEA.PA": "IE0002XZSHO1",
        "SAF.PA": "FR0000120274",
        "AIR": "FR0000113220",
        "ASML": "NL0000285116",
        "NEE": "US6523941035",
        "DFNS": "LU1681047236",
        "RYAAY": "IE00BYSNTY28",
        "TSM": "TW0002365886",
        "NVDA": "US67066G1040",
        "STX": "US78463X1075",
        "GOOGL": "US02079K3059",
        "AIBD": "LU1681047236",
        "CCJ": "CA1368951081",
        "AVGO": "US109378X1051",
        "VST": "US91844X1088",
        "V": "US92826C8394",
        "AMD": "US0079031078",
        "ATLX": "US04785V1016",
        "PDN.AX": "AU000000PDN6",
        "RHM.DE": "DE0007030009",
        "NET": "US64106L1061",
        "REGN": "US75886B1075",
        "FRE.DE": "DE0005785604",
        "LRN": "US5366541060",
        "PLTR": "US69745J1060",
        "ABVX": "FR0014003TT8",
        "META": "US30303M1027",
        "AGI": "CA02107B1076",
        "MU": "US5951121038",
        "PANX.PA": "FR0014003TT8"
    }

    # Actions par utilisateur avec catégories PEA/TITRES (corrigées)
    actions_par_utilisateur = {
        "Michel": {
            "PEA": {
                "^GSPC": "📈 S&P 500",
                "PANX.PA": "📈 Amundi NASDAQ-100 ETF"
            },
            "TITRES": {
                "SATS": "🛰️ EchoStar",
                "DBX": "☁️ Dropbox",
                "COIN": "₿ Coinbase",
                "PYPL": "💳 PayPal",
                "ZM": "🎥 Zoom",
                "MSFT": "🖥️ Microsoft",
                "AAPL": "📱 Apple",
                "TSLA": "🚗 Tesla",
                "NFLX": "🎬 Netflix",
                "AMZN": "📦 Amazon"
            }
        },
        "Romain": {
            "PEA": {
                "FGR.PA": "🏗️ Eiffage",
                "SOI.PA": "⚡ Soitec",
                "PSP5.PA": "📈 Amundi PEA S&P 500 ETF",
                "PCEU.PA": "🇪🇺 Amundi PEA MSCI Europe ETF",
                "STMPA.PA": "🔧 STMicroelectronics",
                "DSY.PA": "💻 Dassault Systèmes",
                "WPEA.PA": "🌍 iShares MSCI World PEA ETF",
                "C50.PA": "🇪🇺 Amundi EURO STOXX 50 ETF",
                "PAASI.PA": "🌏 Amundi PEA Asie Émergente ETF",
                "VIE.PA": "♻️ Veolia Environnement",
                "CHIP.PA": "🔬 Amundi Semiconductors ETF",
                "PAEEM.PA": "🌍 Amundi PEA Émergents ETF",
                "AM.PA": "✈️ Dassault Aviation",
                "BAYN.DE": "💊 Bayer",
                "DEEZR.PA": "🎵 Deezer",
                "LSG.OL": "🐟 Lerøy Seafood"
            },
            "TITRES": {
                "FORSE.PA": "🔋 Forsee Power",
                "SATS": "🛰️ EchoStar"
            }
        },
        "Roger": {
            "PEA": {
                "^GSPC": "📈 S&P 500",
                "SAF.PA": "✈️ Safran",
                "AIR": "✈️ Airbus",
                "ASML": "🔬 ASML",
                "NEE": "⚡ NextEra Energy",
                "DFNS": "🛡️ Defence ETF",
                "RYAAY": "✈️ Ryanair",
                "BAYN.DE": "💊 Bayer"
            },
            "TITRES": {
                "SATS": "🛰️ EchoStar",
                "TSM": "🔧 TSMC",
                "NVDA": "🎮 NVIDIA",
                "STX": "💾 Seagate",
                "GOOGL": "🔍 Alphabet",
                "AIBD": "🤖 AI & Big Data ETF",
                "CCJ": "☢️ Cameco",
                "AVGO": "📡 Broadcom",
                "VST": "⚡ Vistra",
                "V": "💳 Visa",
                "AMD": "🖥️ AMD",
                "ATLX": "🔋 Atlas Lithium",
                "PDN.AX": "☢️ Paladin Energy",
                "RHM.DE": "🛡️ Rheinmetall",
                "NET": "☁️ Cloudflare",
                "REGN": "💊 Regeneron",
                "FRE.DE": "🏥 Fresenius",
                "LRN": "🎓 Stride Inc",
                "PLTR": "🛡️ Palantir",
                "ABVX": "💉 Abivax",
                "MSFT": "🖥️ Microsoft",
                "AAPL": "📱 Apple",
                "META": "📘 Meta",
                "AGI": "⛏️ Alamos Gold",
                "MU": "💾 Micron Technology"
            }
        }
    }

    # Actions disponibles pour l'utilisateur courant (aplatir pour le traitement)
    actions_disponibles = {}
    actions_categories = {}

    for categorie, actions in actions_par_utilisateur[utilisateur].items():
        for ticker, nom in actions.items():
            actions_disponibles[ticker] = nom
            actions_categories[ticker] = categorie

    liste_tickers = list(actions_disponibles.keys())

    # Fonction pour déterminer la recommandation (cache 15 min)
    @st.cache_data(ttl=900)
    def get_all_signals(tickers_list):
        """Charger tous les signaux en parallèle"""
        def _signal(sym):
            try:
                d = yf.Ticker(sym).history(period="1y")
                if d.empty:
                    return sym, "Neutre"
                d['MA50'] = d['Close'].rolling(window=50).mean()
                d['MA200'] = d['Close'].rolling(window=200).mean()
                p = d['Close'].iloc[-1]
                m50 = d['MA50'].iloc[-1]
                m200 = d['MA200'].iloc[-1]
                if p > m50 > m200:
                    return sym, "Acheter"
                elif p < m50 < m200:
                    return sym, "Vendre"
                return sym, "Attente"
            except:
                return sym, "Neutre"
        with ThreadPoolExecutor(max_workers=10) as ex:
            results = dict(ex.map(lambda s: _signal(s), tickers_list))
        return results

    # Sélection rapide fusionnée avec recommandations
    st.sidebar.subheader("🎯 Actions & Recommandations")

    # Checkbox pour afficher les ISIN
    afficher_isin = st.sidebar.checkbox("🔍 Afficher les ISIN", key="afficher_isin")

    # Charger tous les signaux en parallèle (cache 15 min)
    signaux_cache = get_all_signals(tuple(liste_tickers))

    # Grouper par catégories pour l'affichage
    options_par_categorie = {}
    for ticker_key, nom in actions_disponibles.items():
        categorie = actions_categories[ticker_key]
        signal = signaux_cache.get(ticker_key, "Neutre")
        emoji_feu = {"Acheter": "🟢", "Vendre": "🔴", "Attente": "🟡", "Neutre": "⚪"}.get(signal, "⚪")

        # Ajouter l'ISIN si la checkbox est cochée
        isin_text = ""
        if afficher_isin:
            isin_val = isin_actions.get(ticker_key, "ISIN inconnu")
            isin_text = f" | {isin_val}"

        option_text = f"{emoji_feu} {nom} → {signal}{isin_text}"

        if categorie not in options_par_categorie:
            options_par_categorie[categorie] = []
        options_par_categorie[categorie].append((ticker_key, option_text))

    # Construire une liste unique avec séparateurs visuels pour un seul radio
    liste_radio = []
    liste_radio_tickers = []

    for categorie in ["PEA", "TITRES"]:
        if categorie in options_par_categorie:
            # Séparateur visuel (non cliquable visuellement mais dans le radio)
            liste_radio.append(f"━━━ 📊 {categorie} ━━━")
            liste_radio_tickers.append(None)
            for ticker_key, option_text in options_par_categorie[categorie]:
                liste_radio.append(option_text)
                liste_radio_tickers.append(ticker_key)

    # Un seul radio pour tout
    # Trouver le premier vrai ticker (pas un séparateur) comme défaut
    default_idx = next(i for i, t in enumerate(liste_radio_tickers) if t is not None)

    action_choisie = st.sidebar.radio(
        "Action :",
        liste_radio,
        index=default_idx,
        key="action_radio",
        label_visibility="collapsed"
    )

    # Récupérer le ticker correspondant
    if action_choisie in liste_radio:
        idx = liste_radio.index(action_choisie)
        selected_ticker = liste_radio_tickers[idx]

    # Si séparateur cliqué, utiliser le premier vrai ticker
    if selected_ticker is None:
        selected_ticker = liste_tickers[0]

    # Option personnalisée en dessous
    custom_mode = st.sidebar.checkbox("🔧 Mode personnalisé")

    if custom_mode:
        ticker_input = st.sidebar.text_input("Ticker personnalisé (ex: GOOGL, META)", value="").upper()
        if ticker_input:
            selected_ticker = ticker_input
            nom_action = f"{ticker_input} (personnalisé)"
        else:
            st.sidebar.info("Entrez un ticker personnalisé")
            st.stop()
    elif selected_ticker:
        nom_action = actions_disponibles[selected_ticker]
    else:
        # Par défaut : S&P 500
        selected_ticker = "^GSPC"
        nom_action = "📈 S&P 500"

    ticker_symbol = selected_ticker

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

    # Documentation tout en bas
    st.sidebar.markdown("---")
    show_help = st.sidebar.button("❓ Documentation")

    if show_help:
        st.sidebar.markdown("## 📚 Documentation des Indicateurs")
        indicator_choice = st.sidebar.selectbox(
            "Choisir un indicateur :",
            ["MA50/MA200", "RSI", "MACD", "Bollinger"]
        )
        st.sidebar.markdown(docs[indicator_choice])
        st.sidebar.markdown("*💡 Astuce : Lisez la documentation pour comprendre comment utiliser chaque indicateur !*")

    # CSS pour resserrer l'espacement vertical de la partie principale ET rendre la sidebar accessible sur mobile
    st.markdown("""
    <style>
    body { margin: 0 !important; padding: 0 !important; }
.stApp { margin: 0 !important; padding: 0 !important; }
.main { margin: 0 !important; padding: 0 !important; }
.block-container { padding-top: 0rem !important; padding-bottom: 0.3rem !important; }
.main .block-container { padding-top: 0rem !important; }
div[data-testid="stVerticalBlock"] > div:first-child { margin-top: 0rem !important; padding-top: 0rem !important; }
.stApp > div:first-child { padding-top: 0rem !important; margin-top: 0rem !important; }
header[data-testid="stHeader"] { background: transparent !important; height: 2.5rem !important; }
    /* Bouton chevrons sidebar : rouge, bien visible, style bouton */
    button[data-testid="collapsedControl"],
    div[data-testid="stSidebarCollapsedControl"] button {
        background-color: #DC3545 !important;
        color: white !important;
        border: none !important;
        border-radius: 8px !important;
        padding: 6px 10px !important;
        font-size: 1.2rem !important;
        box-shadow: 0 2px 6px rgba(0,0,0,0.3) !important;
        opacity: 1 !important;
    }
    button[data-testid="collapsedControl"]:hover,
    div[data-testid="stSidebarCollapsedControl"] button:hover {
        background-color: #B02A37 !important;
    }
    /* Chevron de fermeture dans la sidebar aussi en rouge */
    section[data-testid="stSidebar"] button[data-testid="stSidebarNavCollapseButton"],
    section[data-testid="stSidebar"] button[aria-label="Close"] {
        background-color: #DC3545 !important;
        color: white !important;
        border-radius: 8px !important;
        box-shadow: 0 2px 6px rgba(0,0,0,0.3) !important;
    }
div[data-testid="element-container"] { margin: 0 !important; }
div[data-testid="stVerticalBlock"] { margin: 0 !important; padding: 0 !important; }
    div[data-testid="stMetric"] { padding: 0px !important; margin-bottom: 0px !important; }
    div[data-testid="stMetricValue"] { font-size: 1.3rem !important; }
    h1 { margin: 0px !important; padding: 0px !important; font-size: 1.6rem !important; line-height: 1.2 !important; }
    h2 { margin: 0px !important; padding: 0px !important; font-size: 1.1rem !important; line-height: 1.2 !important; }
    div[data-testid="stHorizontalBlock"] { gap: 0.2rem !important; margin-bottom: 0px !important; }
    hr { margin: 0.1rem 0 !important; }
    div[data-testid="stAlert"] { padding: 0.2rem 0.5rem !important; margin: 0px !important; }
    div[data-testid="stAlert"] p { margin: 0px !important; font-size: 0.82rem !important; line-height: 1.3 !important; }
    div[data-testid="stCaptionContainer"] { margin: 0px !important; padding: 0px !important; }
    div[data-testid="stElementContainer"] { margin-bottom: 0.15rem !important; }
    div[data-testid="stVerticalBlock"] { gap: 0.25rem !important; }
    p { margin-bottom: 0.1rem !important; }

    /* Mobile : texte adapté + padding réduit */
    @media (max-width: 768px) {
        h1 { font-size: 1.2rem !important; }
        h2 { font-size: 1.0rem !important; }
        div[data-testid="stMetricValue"] { font-size: 1.0rem !important; }
        .block-container { padding-left: 0.5rem !important; padding-right: 0.5rem !important; }
    }
    </style>
    """, unsafe_allow_html=True)

    st.title(f"📈 {nom_action}")
    st.caption(f"Analyse technique de {nom_action}")

    # Fonctions cachées pour éviter les appels API répétés
    @st.cache_data(ttl=900)
    def charger_donnees_et_cap(symbol, per):
        """Charger données historiques + capitalisation en un seul appel (cache 15 min)"""
        t = yf.Ticker(symbol)
        data = t.history(period=per)
        try:
            cap = t.info.get('marketCap', None)
        except:
            cap = None
        return data, cap

    # Chargement des données
    try:
        data, market_cap = charger_donnees_et_cap(ticker_symbol, periode)
        if data.empty:
            st.error(f"Impossible de charger les données pour {ticker_symbol}.")
            return
    except Exception as e:
        st.error(f"Erreur lors du chargement: {e}")
        return
    if market_cap:
        if market_cap >= 1e12:
            market_cap_str = f"{market_cap/1e12:.1f} T$"
        elif market_cap >= 1e9:
            market_cap_str = f"{market_cap/1e9:.1f} G$"
        elif market_cap >= 1e6:
            market_cap_str = f"{market_cap/1e6:.1f} M$"
        else:
            market_cap_str = f"{market_cap:.0f} $"
    else:
        market_cap_str = "N/A"

    # Métriques principales (5 colonnes pour inclure la capitalisation)
    col1, col2, col3, col4, col5 = st.columns(5)

    prix_actuel = data['Close'].iloc[-1]
    prix_precedent = data['Close'].iloc[-2] if len(data) > 1 else prix_actuel
    variation = ((prix_actuel - prix_precedent) / prix_precedent) * 100

    col1.metric("Prix Actuel", f"{prix_actuel:.2f} $")
    col2.metric("Variation", f"{variation:+.2f}%", delta=f"{variation:+.2f}%")
    col3.metric("Plus Haut", f"{data['High'].max():.2f} $")
    col4.metric("Plus Bas", f"{data['Low'].min():.2f} $")
    col5.metric("Capitalisation", market_cap_str)

    # Recommandation de trading avec croisements (en premier)
    st.subheader("🎯 Recommandation de trading")

    # Calculer les moyennes mobiles pour la recommandation
    data['MA50'] = data['Close'].rolling(window=50).mean()
    data['MA200'] = data['Close'].rolling(window=200).mean()
    dernier_ma50 = data['MA50'].iloc[-1]
    dernier_ma200 = data['MA200'].iloc[-1]

    # Détecter les croisements récents
    golden_crosses, death_crosses = detecter_croisements_ma(data)

    # Signal principal sur toute la largeur
    if prix_actuel > dernier_ma50 > dernier_ma200:
        st.success("🟢 **ACHETER** — Tendance haussière confirmée")
    elif prix_actuel < dernier_ma50 < dernier_ma200:
        st.error("🔴 **VENDRE** — Tendance baissière confirmée")
    else:
        st.warning("🟡 **ATTENTE** — Tendance incertaine")

    # Signaux techniques sur toute la largeur (pas de retour à la ligne)
    if prix_actuel > dernier_ma50:
        st.success(f"📈 Prix > MA50 ({dernier_ma50:.2f} $) → **CONFIANCE** court terme — Le prix est au-dessus de sa moyenne récente")
    else:
        st.error(f"📉 Prix < MA50 ({dernier_ma50:.2f} $) → **PRUDENCE** court terme — Le prix est sous sa moyenne récente")

    if dernier_ma50 > dernier_ma200:
        st.success(f"🚀 MA50 > MA200 ({dernier_ma200:.2f} $) → **TENDANCE** haussière — La tendance récente est plus forte que le long terme")
    else:
        st.error(f"📉 MA50 < MA200 ({dernier_ma200:.2f} $) → **TENDANCE** baissière — La tendance récente est plus faible que le long terme")

    volatilite = data['Close'].pct_change().std() * 100
    if volatilite < 1.5:
        st.info(f"📊 Volatilité {volatilite:.1f}% → **STABLE**")
    elif volatilite < 2.5:
        st.warning(f"📊 Volatilité {volatilite:.1f}% → **MODÉRÉE**")
    else:
        st.error(f"📊 Volatilité {volatilite:.1f}% → **ÉLEVÉE**")

    # Croisements + Niveaux clés côte à côte, resserrés
    col_g, col_d = st.columns(2)
    with col_g:
        st.markdown("**Croisements récents**")
        gc_txt = f"🟢 GC: {golden_crosses[-1].strftime('%d/%m/%Y')}" if golden_crosses else "🟢 GC: Aucun"
        dc_txt = f"🔴 DC: {death_crosses[-1].strftime('%d/%m/%Y')}" if death_crosses else "🔴 DC: Aucun"
        st.write(f"{gc_txt} · {dc_txt}")
    with col_d:
        st.markdown("**Niveaux clés**")
        st.write(f"Support: {data['Low'].tail(20).min():.2f} $ · Résistance: {data['High'].tail(20).max():.2f} $ · Rdt 50j: {((prix_actuel / data['Close'].iloc[-50]) - 1) * 100:+.1f}%")

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

        # Ajouter les marqueurs de croisements avec annotations
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
            # Ajouter annotations pour les Golden Cross
            for i, (date, price) in enumerate(zip(gc_dates[-3:], gc_prices[-3:])):  # 3 derniers
                fig_ma.add_annotation(
                    x=date, y=price,
                    text=f"🟢 ACHAT<br>{date.strftime('%d/%m')}",
                    showarrow=True,
                    arrowhead=2,
                    arrowsize=1,
                    arrowwidth=2,
                    arrowcolor="green",
                    ax=0,
                    ay=-40,
                    bgcolor="lightgreen",
                    bordercolor="green",
                    borderwidth=1
                )

        if death_crosses:
            dc_dates = [date for date in death_crosses if date in data.index]
            dc_prices = [data.loc[date, 'Close'] for date in dc_dates]
            fig_ma.add_trace(go.Scatter(
                x=dc_dates, y=dc_prices,
                mode='markers',
                name='🔴 Death Cross',
                marker=dict(color='red', size=12, symbol='triangle-down')
            ))
            # Ajouter annotations pour les Death Cross
            for i, (date, price) in enumerate(zip(dc_dates[-3:], dc_prices[-3:])):  # 3 derniers
                fig_ma.add_annotation(
                    x=date, y=price,
                    text=f"🔴 VENTE<br>{date.strftime('%d/%m')}",
                    showarrow=True,
                    arrowhead=2,
                    arrowsize=1,
                    arrowwidth=2,
                    arrowcolor="red",
                    ax=0,
                    ay=40,
                    bgcolor="lightcoral",
                    bordercolor="red",
                    borderwidth=1
                )

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

    # Section d'interprétation globale
    if show_ma or show_rsi or show_macd:
        st.markdown("---")
        st.subheader("🎓 Synthèse et interprétation")

        # Analyse globale des signaux
        signaux_positifs = 0
        signaux_negatifs = 0

        analyse = []

        # Signal MA
        if show_ma:
            if prix_actuel > dernier_ma50 > dernier_ma200:
                signaux_positifs += 2
                analyse.append("🟢 **MA50/MA200** : Tendance haussière confirmée sur tous les horizons")
            elif prix_actuel < dernier_ma50 < dernier_ma200:
                signaux_negatifs += 2
                analyse.append("🔴 **MA50/MA200** : Tendance baissière confirmée sur tous les horizons")
            else:
                signaux_positifs += 1
                signaux_negatifs += 1
                analyse.append("🟡 **MA50/MA200** : Tendances contradictoires - période d'incertitude")

        # Signal RSI
        if show_rsi:
            rsi = calculate_rsi(data)
            rsi_actuel = rsi.iloc[-1]
            if rsi_actuel > 70:
                signaux_negatifs += 1
                analyse.append("🔴 **RSI** : Zone de surachat - risque de correction")
            elif rsi_actuel < 30:
                signaux_positifs += 1
                analyse.append("🟢 **RSI** : Zone de survente - opportunité d'achat")
            else:
                analyse.append("🟡 **RSI** : Zone neutre - pas de signal extrême")

        # Signal MACD
        if show_macd:
            macd_line, signal_line, _ = calculate_macd(data)
            if macd_line.iloc[-1] > signal_line.iloc[-1]:
                signaux_positifs += 1
                analyse.append("🟢 **MACD** : Momentum haussier - force d'achat présente")
            else:
                signaux_negatifs += 1
                analyse.append("🔴 **MACD** : Momentum baissier - force de vente présente")

        # Synthèse finale
        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric("🟢 Signaux positifs", signaux_positifs)
        with col2:
            st.metric("🔴 Signaux négatifs", signaux_negatifs)
        with col3:
            if signaux_positifs > signaux_negatifs:
                st.success("🎯 **CONCLUSION** : HAUSSIÈRE")
            elif signaux_negatifs > signaux_positifs:
                st.error("🎯 **CONCLUSION** : BAISSIÈRE")
            else:
                st.warning("🎯 **CONCLUSION** : NEUTRE")

        # Détail de l'analyse
        st.write("**Détail de l'analyse :**")
        for point in analyse:
            st.write(f"• {point}")

        # Conseil pédagogique
        st.info("💡 **Conseil** : Plus vous avez de signaux alignés dans la même direction, plus le signal est fiable. Les contradictions indiquent souvent une période de transition.")

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
        st.write("**Signaux techniques**")
        if prix_actuel > dernier_ma50:
            st.success(f"📈 Prix > MA50 ({dernier_ma50:.2f} $) → **CONFIANCE** court terme")
            st.write("   Le prix est au-dessus de sa moyenne récente")
        else:
            st.error(f"📉 Prix < MA50 ({dernier_ma50:.2f} $) → **PRUDENCE** court terme")
            st.write("   Le prix est sous sa moyenne récente")

        if dernier_ma50 > dernier_ma200:
            st.success(f"🚀 MA50 > MA200 ({dernier_ma200:.2f} $) → **TENDANCE** haussière")
            st.write("   La tendance récente est plus forte que le long terme")
        else:
            st.error(f"📉 MA50 < MA200 ({dernier_ma200:.2f} $) → **TENDANCE** baissière")
            st.write("   La tendance récente est plus faible que le long terme")

        volatilite = data['Close'].pct_change().std() * 100
        if volatilite < 1.5:
            st.info(f"📊 Volatilité {volatilite:.1f}% → **STABLE**")
        elif volatilite < 2.5:
            st.warning(f"📊 Volatilité {volatilite:.1f}% → **MODÉRÉE**")
        else:
            st.error(f"📊 Volatilité {volatilite:.1f}% → **ÉLEVÉE**")

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
