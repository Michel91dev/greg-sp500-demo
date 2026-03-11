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
import re
import requests
import pymysql

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

def get_connexion_mysql():
    """Connexion MySQL via Streamlit Secrets."""
    if "mysql" not in st.secrets:
        cles = list(st.secrets.keys()) if hasattr(st.secrets, 'keys') else "non lisible"
        raise RuntimeError(f"Secrets MySQL non configurés — clés disponibles : {cles}")
    cfg = st.secrets["mysql"]
    return pymysql.connect(
        host=cfg["host"],
        port=int(cfg["port"]),
        database=cfg["database"],
        user=cfg["user"],
        password=cfg["password"],
        charset="utf8mb4",
        connect_timeout=5
    )


def charger_isin_mysql(utilisateur: str) -> dict:
    """Charger les ISIN depuis MySQL pour un utilisateur."""
    try:
        conn = get_connexion_mysql()
        with conn.cursor() as cur:
            cur.execute(
                "SELECT ticker, isin FROM isin_utilisateurs WHERE utilisateur = %s",
                (utilisateur,)
            )
            rows = cur.fetchall()
        conn.close()
        return {ticker: isin for ticker, isin in rows}
    except Exception:
        return {}


def charger_tickers_mysql(utilisateur: str) -> dict:
    """Charger les tickers depuis MySQL pour un utilisateur. Retourne {categorie: {ticker: 'emoji nom'}}"""
    try:
        conn = get_connexion_mysql()
        with conn.cursor() as cur:
            cur.execute(
                "SELECT ticker, nom, categorie, emoji FROM isin_utilisateurs WHERE utilisateur = %s ORDER BY categorie, nom",
                (utilisateur,)
            )
            rows = cur.fetchall()
        conn.close()
        resultat = {}
        for ticker, nom, categorie, emoji in rows:
            if categorie not in resultat:
                resultat[categorie] = {}
            nom_affiche = nom if nom else ticker
            resultat[categorie][ticker] = f"{emoji} {nom_affiche}"
        return resultat
    except Exception:
        return {}


def sauvegarder_ticker_mysql(utilisateur: str, ticker: str, isin: str, categorie: str, nom: str, emoji: str):
    """Sauvegarder ou mettre à jour un ticker+ISIN dans MySQL. Retourne True ou le message d'erreur."""
    try:
        conn = get_connexion_mysql()
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO isin_utilisateurs (utilisateur, ticker, isin, categorie, nom, emoji)
                   VALUES (%s, %s, %s, %s, %s, %s)
                   ON DUPLICATE KEY UPDATE isin = %s, categorie = %s, nom = %s, emoji = %s""",
                (utilisateur, ticker, isin, categorie, nom, emoji, isin, categorie, nom, emoji)
            )
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        return str(e)


def sauvegarder_isin_mysql(utilisateur: str, ticker: str, isin: str, categorie: str):
    """Mettre à jour uniquement l'ISIN d'un ticker existant. Retourne True ou le message d'erreur."""
    try:
        conn = get_connexion_mysql()
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO isin_utilisateurs (utilisateur, ticker, isin, categorie)
                   VALUES (%s, %s, %s, %s)
                   ON DUPLICATE KEY UPDATE isin = %s, categorie = %s""",
                (utilisateur, ticker, isin, categorie, isin, categorie)
            )
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        return str(e)


def supprimer_isin_mysql(utilisateur: str, ticker: str) -> bool:
    """Supprimer un ISIN de MySQL pour un utilisateur."""
    try:
        conn = get_connexion_mysql()
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM isin_utilisateurs WHERE utilisateur = %s AND ticker = %s",
                (utilisateur, ticker)
            )
        conn.commit()
        conn.close()
        return True
    except Exception:
        return False


def main():
    version = get_version()
    docs = get_indicator_docs()

    st.set_page_config(page_title="Analyse Actions", page_icon="📈", layout="wide")

    # CSS global : alignement gauche des boutons sidebar
    st.markdown("""
    <style>
    [data-testid="stSidebarContent"] .stButton > button {
        text-align: left !important;
        justify-content: flex-start !important;
        padding-left: 6px !important;
        display: flex !important;
        align-items: center !important;
    }
    [data-testid="stSidebarContent"] .stButton > button p {
        text-align: left !important;
        width: 100% !important;
        margin: 0 !important;
    }
    [data-testid="stSidebarContent"] button[kind="secondary"][data-testid="baseButton-secondary"] {
        padding: 2px 4px !important;
        font-size: 0.75em !important;
        min-height: 0 !important;
    }
    [data-testid="stSidebarContent"] [data-testid="stHorizontalBlock"] {
        gap: 4px !important;
    }
    /* Boutons PEA(bleu) CTO(vert) Annuler(rouge) — ciblage par aria-label */
    button[aria-label="🏛️ PEA"] {
        background-color: #1565C0 !important;
        color: white !important;
        border: none !important;
    }
    button[aria-label="📈 CTO"] {
        background-color: #2E7D32 !important;
        color: white !important;
        border: none !important;
    }
    button[aria-label="❌"] {
        background-color: #C62828 !important;
        color: white !important;
        border: none !important;
    }
    </style>
    """, unsafe_allow_html=True)

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
        "PANX.PA": "FR0014003TT8",
        "IFX.DE": "DE0006231004",
        "NP5.DE": "IT0003506015",
        "005930.KS": "KR7005930003",
        "TSM": "US8740391003",
        "NEE": "US65339F1012",
        "MC.PA": "FR0000121014",
        "OR.PA": "FR0000121248",
        "AI.PA": "FR0000120073",
        "SAN.PA": "FR0000120571",
        "BNP.PA": "FR0000131104",
        "SU.PA": "FR0000120571",
        "RMS.PA": "FR0000032364",
        "RI.PA": "FR0000062270",
        "CA.PA": "FR0000060172",
        "KER.PA": "FR0000121485",
        "EN.PA": "FR0010202515",
        "WLN.PA": "FR0010421017",
        "ML.PA": "FR0000032252",
        "TEF.PA": "FR0000054722",
        "TTE.PA": "FR0000120271",
        "SOGO.PA": "FR0000060336",
        "HO.PA": "FR0000124489",
        "BN.PA": "FR0000120644",
        "LR.PA": "FR0000045072",
        "CGG.PA": "FR0010208767",
        "ALO.PA": "FR0000039300",
        "MTX.PA": "FR0014003TT8"
    }

    # Charger les ISIN personnalisés depuis MySQL et les appliquer par-dessus les valeurs par défaut
    isin_mysql = charger_isin_mysql(utilisateur)
    isin_actions.update(isin_mysql)

    # Charger les tickers depuis MySQL (plus de hardcode)
    actions_par_utilisateur_mysql = charger_tickers_mysql(utilisateur)
    # Fallback : dict vide si MySQL inaccessible
    actions_par_utilisateur = {utilisateur: actions_par_utilisateur_mysql}

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

    # Tri des titres
    ordre_tri = st.sidebar.selectbox(
        "🔀 Trier par :",
        ["Défaut", "Alphabétique", "Signal (Acheter en 1er)", "Signal (Vendre en 1er)"],
        key="ordre_tri"
    )

    # Charger tous les signaux en parallèle (cache 15 min)
    signaux_cache = get_all_signals(tuple(liste_tickers))

    # Grouper par catégories pour l'affichage
    options_par_categorie = {}
    for ticker_key, nom in actions_disponibles.items():
        categorie = actions_categories[ticker_key]
        signal = signaux_cache.get(ticker_key, "Neutre")
        emoji_feu = {"Acheter": "🟢", "Vendre": "🔴", "Attente": "🟡", "Neutre": "⚪"}.get(signal, "⚪")

        option_text = f"{emoji_feu} {nom} → {signal}"

        if categorie not in options_par_categorie:
            options_par_categorie[categorie] = []
        options_par_categorie[categorie].append((ticker_key, option_text))

    # Appliquer le tri choisi dans chaque catégorie
    ordre_signal = {"Acheter": 0, "Attente": 1, "Neutre": 2, "Vendre": 3}
    for cat in options_par_categorie:
        if ordre_tri == "Alphabétique":
            # Trier sur le nom pur (sans emoji) depuis actions_disponibles
            options_par_categorie[cat].sort(key=lambda x: actions_disponibles[x[0]].split(" ", 1)[-1].lower())
        elif ordre_tri == "Signal (Acheter en 1er)":
            options_par_categorie[cat].sort(key=lambda x: ordre_signal.get(signaux_cache.get(x[0], "Neutre"), 2))
        elif ordre_tri == "Signal (Vendre en 1er)":
            options_par_categorie[cat].sort(key=lambda x: -ordre_signal.get(signaux_cache.get(x[0], "Neutre"), 2))

    # Initialiser le ticker sélectionné dans session_state
    if "selected_ticker_key" not in st.session_state:
        st.session_state["selected_ticker_key"] = liste_tickers[0] if liste_tickers else None
    if st.session_state["selected_ticker_key"] not in actions_disponibles:
        st.session_state["selected_ticker_key"] = liste_tickers[0] if liste_tickers else None

    # Afficher la liste par catégorie avec bouton sélection + poubelle (style v2.5.23)
    for categorie in ["PEA", "TITRES"]:
        if categorie not in options_par_categorie:
            continue
        st.sidebar.markdown(
            f'<div style="font-weight:bold;color:#888;font-size:0.8em;'
            f'margin:10px 0 8px 0;border-bottom:1px solid #ccc;padding-bottom:3px;">📊 {categorie}</div>',
            unsafe_allow_html=True
        )
        couleur_signal = {"Acheter": "#2E7D32", "Vendre": "#C62828", "Attente": "#E65100", "Neutre": "#666"}
        for ticker_key, option_text in options_par_categorie[categorie]:
            isin_val = isin_actions.get(ticker_key, "ISIN inconnu")
            signal = signaux_cache.get(ticker_key, "Neutre")
            nom_pur = actions_disponibles[ticker_key].split(" ", 1)[-1]
            emoji_feu = {"Acheter": "🟢", "Vendre": "🔴", "Attente": "🟡", "Neutre": "⚪"}.get(signal, "⚪")
            est_selectionne = (st.session_state["selected_ticker_key"] == ticker_key)

            col_boule, col_sel, col_del = st.sidebar.columns([1, 8, 1])
            with col_boule:
                if est_selectionne:
                    st.markdown(
                        f'<div style="border:4px solid #C62828;border-radius:50%;'
                        f'width:28px;height:28px;display:flex;align-items:center;'
                        f'justify-content:center;font-size:1.1em;margin-top:3px;margin-right:-6px;">{emoji_feu}</div>',
                        unsafe_allow_html=True
                    )
                else:
                    st.markdown(
                        f'<div style="font-size:1.1em;margin-top:4px;padding-left:2px;">{emoji_feu}</div>',
                        unsafe_allow_html=True
                    )
            with col_sel:
                isin_txt = ""
                if afficher_isin:
                    isin_txt = " ( )" if isin_val == "ISIN inconnu" else f" ({isin_val})"
                if est_selectionne:
                    label = f"▶▶▶ {nom_pur} → {signal}{isin_txt} ◄◄◄"
                else:
                    label = f"{nom_pur} → {signal}{isin_txt}"
                if st.button(label, key=f"sel_{ticker_key}", use_container_width=True):
                    st.session_state["selected_ticker_key"] = ticker_key
                    st.rerun()
            with col_del:
                if st.button("🗑️", key=f"del_{ticker_key}", help=f"Supprimer ISIN de {ticker_key}", use_container_width=True):
                    if "isin_custom" not in st.session_state:
                        st.session_state["isin_custom"] = {}
                    st.session_state["isin_custom"].pop(ticker_key, None)
                    isin_actions[ticker_key] = "ISIN inconnu"
                    st.rerun()

    selected_ticker = st.session_state.get("selected_ticker_key") or (liste_tickers[0] if liste_tickers else None)

    # ── Gestion ISIN ── cartouche coloré
    st.sidebar.markdown(
        '<div style="background:linear-gradient(90deg,#FFAA80,#FF8C66);'
        'color:white;padding:4px 8px;border-radius:6px;font-weight:bold;'
        'font-size:0.9em;margin:6px 0 2px 0;">🔑 Gérer les ISIN</div>',
        unsafe_allow_html=True
    )
    with st.sidebar.expander("", expanded=True):
        onglet_add, onglet_edit, onglet_dl = st.tabs(["➕ Ajouter", "✏️ Modifier", "📈 Export"])

        # ── Onglet Ajouter un nouveau ticker ──
        with onglet_add:
            st.caption(f"Ajouter un ticker pour **{utilisateur}**")

            # Étape 1 : saisie ISIN
            nouvel_isin_add = st.text_input(
                "ISIN :", key="nouvel_isin_add_input", max_chars=14, placeholder="ex: GB0009895292"
            ).strip().upper()
            cat_add = st.radio(
                "Catégorie :", ["PEA", "COMPTE TITRES"], horizontal=True, key="cat_add_radio"
            )
            cat_key_add = "PEA" if cat_add == "PEA" else "TITRES"
            isin_valide_add = bool(re.match(r'^[A-Z]{2}[A-Z0-9]{9,12}$', nouvel_isin_add)) if nouvel_isin_add else False
            if nouvel_isin_add and not isin_valide_add:
                st.caption("⚠️ ISIN invalide")
            elif isin_valide_add:
                st.caption("✅ ISIN valide")

            if st.button("🔍 Rechercher", key="btn_rechercher_isin"):
                if not nouvel_isin_add:
                    st.warning("ISIN vide.")
                elif not isin_valide_add:
                    st.error("Format ISIN invalide.")
                else:
                    try:
                        resp = requests.get(
                            "https://query2.finance.yahoo.com/v1/finance/search",
                            params={"q": nouvel_isin_add, "quotesCount": 1, "newsCount": 0},
                            headers={"User-Agent": "Mozilla/5.0"},
                            timeout=5
                        )
                        quotes = resp.json().get("quotes", [])
                        if quotes:
                            st.session_state["add_ticker_trouve"] = quotes[0].get("symbol", "")
                            st.session_state["add_nom_trouve"] = quotes[0].get("longname") or quotes[0].get("shortname") or ""
                            st.session_state["add_isin_trouve"] = nouvel_isin_add
                            st.session_state["add_cat_trouve"] = cat_key_add
                        else:
                            st.session_state["add_ticker_trouve"] = ""
                            st.error(f"Aucun résultat pour {nouvel_isin_add} — vérifiez l'ISIN.")
                    except Exception as e:
                        st.session_state["add_ticker_trouve"] = ""
                        st.error(f"Erreur recherche : {e}")

            # Étape 2 : validation si un résultat est trouvé
            if st.session_state.get("add_ticker_trouve"):
                tk = st.session_state["add_ticker_trouve"]
                nm = st.session_state["add_nom_trouve"]
                isv = st.session_state["add_isin_trouve"]
                cat = st.session_state["add_cat_trouve"]

                # Alerte doublon
                if tk in actions_disponibles:
                    st.warning(f"⚠️ **{tk}** est déjà dans votre liste en {actions_categories.get(tk, '?')}.")

                # Alerte éligibilité PEA
                pays_pea = {"FR", "DE", "NL", "BE", "ES", "IT", "PT", "FI", "AT", "IE", "LU", "DK", "SE", "NO"}
                pays_isin = isv[:2] if len(isv) >= 2 else ""
                eligible_pea = pays_isin in pays_pea
                if cat == "PEA" and not eligible_pea:
                    st.warning(f"⚠️ L'ISIN `{isv}` (pays : **{pays_isin}**) n'est probablement **pas éligible au PEA**.")
                elif cat == "TITRES" and eligible_pea:
                    st.info(f"ℹ️ L'ISIN `{isv}` (pays : **{pays_isin}**) pourrait être **éligible au PEA**.")

                st.markdown(f"**Ticker :** `{tk}`")
                nm_edit = st.text_input("Nom :", value=nm, key="add_nom_edit_input")

                def _sauvegarder_et_reset(cat_finale):
                    """Sauvegarder le ticker avec la catégorie choisie et réinitialiser."""
                    res = sauvegarder_ticker_mysql(utilisateur, tk, isv, cat_finale, nm_edit, "📈")
                    if res is True:
                        st.success(f"✅ {tk} — {nm_edit} ajouté en {cat_finale}")
                        for k in ["add_ticker_trouve", "add_nom_trouve", "add_isin_trouve", "add_cat_trouve"]:
                            st.session_state.pop(k, None)
                        st.rerun()
                    elif "Duplicate entry" in str(res):
                        st.warning(f"⚠️ **{tk}** existe déjà en base pour {utilisateur}.")
                    else:
                        st.error(f"Erreur MySQL : {res}")

                st.markdown(
                    '<div style="background:#37474F;color:white;padding:4px 8px;border-radius:4px;'
                    'text-align:center;font-size:0.85em;margin:6px 0 4px 0;font-weight:bold;">'
                    'Confirmez : PEA, CTO ou Annulez</div>',
                    unsafe_allow_html=True
                )
                cat_existante = actions_categories.get(tk)  # "PEA", "TITRES" ou None
                pea_desactive = cat_existante == "PEA"
                cto_desactive = cat_existante == "TITRES"

                col_pea, col_cto, col_ann = st.columns(3)
                with col_pea:
                    if st.button("🏛️ PEA", key="btn_confirmer_pea", use_container_width=True,
                                 disabled=pea_desactive,
                                 help="Déjà en PEA" if pea_desactive else None):
                        _sauvegarder_et_reset("PEA")
                with col_cto:
                    if st.button("📈 CTO", key="btn_confirmer_cto", use_container_width=True,
                                 disabled=cto_desactive,
                                 help="Déjà en CTO" if cto_desactive else None):
                        _sauvegarder_et_reset("TITRES")
                with col_ann:
                    if st.button("❌", key="btn_annuler_add", use_container_width=True):
                        for k in ["add_ticker_trouve", "add_nom_trouve", "add_isin_trouve", "add_cat_trouve"]:
                            st.session_state.pop(k, None)
                        st.rerun()

        # ── Onglet Modifier / Supprimer un ticker existant ──
        with onglet_edit:
            st.caption(f"Modifier l'ISIN d'un ticker existant de **{utilisateur}**")
            tickers_avec_isin = sorted(isin_actions.keys())
            ticker_edit = st.selectbox(
                "Ticker :",
                options=tickers_avec_isin,
                format_func=lambda t: f"{t} — {actions_disponibles.get(t, isin_actions.get(t, t))}",
                key="ticker_edit_sel"
            )
            isin_actuel = isin_actions.get(ticker_edit, "ISIN inconnu")
            st.markdown(
                f'ISIN actuel : <span style="color:#FFAA80;font-weight:bold;">{isin_actuel}</span>',
                unsafe_allow_html=True
            )
            nouvel_isin_edit = st.text_input(
                "Nouvel ISIN :",
                key="nouvel_isin_edit_input",
                max_chars=14,
                placeholder="ex: FR0000035093"
            ).strip().upper()
            isin_valide_edit = bool(re.match(r'^[A-Z]{2}[A-Z0-9]{9,12}$', nouvel_isin_edit)) if nouvel_isin_edit else False
            cat_edit = st.radio(
                "Catégorie :",
                ["PEA", "COMPTE TITRES"],
                horizontal=True,
                key="cat_edit_radio"
            )
            cat_key_edit = "PEA" if cat_edit == "PEA" else "TITRES"
            col_save, col_del = st.columns([3, 1])
            with col_save:
                if st.button("💾 Modifier", key="btn_save_isin_edit"):
                    if not nouvel_isin_edit:
                        st.warning("ISIN vide.")
                    elif not isin_valide_edit:
                        st.error("Format invalide.")
                    else:
                        resultat = sauvegarder_isin_mysql(utilisateur, ticker_edit, nouvel_isin_edit, cat_key_edit)
                        if resultat is True:
                            st.success(f"✅ {nouvel_isin_edit} enregistré")
                            st.rerun()
                        else:
                            st.error(f"Erreur MySQL : {resultat}")
            with col_del:
                if st.button("🗑️", key="btn_del_isin_edit", help="Supprimer cet ISIN"):
                    if supprimer_isin_mysql(utilisateur, ticker_edit):
                        st.success("Supprimé")
                        st.rerun()
                    else:
                        st.error("Erreur MySQL")

        # ── Onglet Export base de données ──
        with onglet_dl:
            st.caption("Télécharger toute la base en CSV")
            try:
                conn_dl = get_connexion_mysql()
                with conn_dl.cursor() as cur_dl:
                    cur_dl.execute(
                        "SELECT utilisateur, ticker, isin, categorie, nom, emoji FROM isin_utilisateurs ORDER BY utilisateur, categorie, ticker"
                    )
                    rows_dl = cur_dl.fetchall()
                conn_dl.close()
                df_dl = pd.DataFrame(rows_dl, columns=["utilisateur", "ticker", "isin", "categorie", "nom", "emoji"])
                csv_dl = df_dl.to_csv(index=False).encode("utf-8")
                st.download_button(
                    label=f"⬇️ Télécharger ({len(df_dl)} lignes)",
                    data=csv_dl,
                    file_name="bourse_isin.csv",
                    mime="text/csv",
                    key="btn_dl_csv"
                )
            except Exception as e:
                st.error(f"Erreur : {e}")

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

    # Extraire le nom pur sans emoji pour le titre (évite les caractères parasites)
    nom_pur_titre = nom_action.split(" ", 1)[-1] if nom_action and not nom_action[0].isascii() else nom_action
    st.title(f"📈 {nom_pur_titre}")
    st.caption(f"Analyse technique de {nom_pur_titre} ({ticker_symbol})")

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
            mode='lines@', name='Prix', line=dict(color='black', width=2)
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

    # ── Section : Informations société + commentaires Yahoo Finance ──
    st.markdown("---")
    st.subheader("🏢 Informations sur la société")

    @st.cache_data(ttl=3600)
    def get_info_societe(ticker_sym: str) -> dict:
        """Récupérer les infos de base de la société depuis Yahoo Finance"""
        try:
            info = yf.Ticker(ticker_sym).info
            return info
        except Exception:
            return {}

    @st.cache_data(ttl=3600)
    def get_actualites(ticker_sym: str) -> list:
        """Récupérer les actualités depuis Yahoo Finance"""
        try:
            news = yf.Ticker(ticker_sym).news
            return news if news else []
        except Exception:
            return []

    info_soc = get_info_societe(selected_ticker)
    actualites = get_actualites(selected_ticker)

    if info_soc:
        col_info1, col_info2 = st.columns(2)
        with col_info1:
            st.write("**📋 Fiche société**")
            if info_soc.get("longName"):
                st.write(f"- **Nom** : {info_soc.get('longName', 'N/A')}")
            if info_soc.get("sector"):
                st.write(f"- **Secteur** : {info_soc.get('sector', 'N/A')}")
            if info_soc.get("industry"):
                st.write(f"- **Industrie** : {info_soc.get('industry', 'N/A')}")
            if info_soc.get("country"):
                st.write(f"- **Pays** : {info_soc.get('country', 'N/A')}")
            if info_soc.get("fullTimeEmployees"):
                st.write(f"- **Employés** : {info_soc.get('fullTimeEmployees', 0):,}")
            if info_soc.get("website"):
                st.write(f"- **Site web** : [{info_soc.get('website')}]({info_soc.get('website')})")
        with col_info2:
            st.write("**💰 Données financières**")
            market_cap = info_soc.get("marketCap")
            if market_cap:
                if market_cap >= 1e12:
                    st.write(f"- **Capitalisation** : {market_cap/1e12:.2f} T$")
                elif market_cap >= 1e9:
                    st.write(f"- **Capitalisation** : {market_cap/1e9:.2f} Mrd$")
                else:
                    st.write(f"- **Capitalisation** : {market_cap/1e6:.2f} M$")
            if info_soc.get("trailingPE"):
                st.write(f"- **PER** : {info_soc.get('trailingPE'):.1f}")
            if info_soc.get("dividendYield"):
                st.write(f"- **Dividende** : {info_soc.get('dividendYield')*100:.2f}%")
            if info_soc.get("fiftyTwoWeekHigh"):
                st.write(f"- **Plus haut 52s** : {info_soc.get('fiftyTwoWeekHigh'):.2f}")
            if info_soc.get("fiftyTwoWeekLow"):
                st.write(f"- **Plus bas 52s** : {info_soc.get('fiftyTwoWeekLow'):.2f}")
            if info_soc.get("targetMeanPrice"):
                st.write(f"- **Objectif analystes** : {info_soc.get('targetMeanPrice'):.2f}")

        # Description de la société
        description = info_soc.get("longBusinessSummary", "")
        if description:
            with st.expander("📖 Description de la société"):
                st.write(description)
    else:
        st.info("Informations société non disponibles pour ce ticker.")

    # Actualités Yahoo Finance
    st.subheader("📰 Dernières actualités (Yahoo Finance)")
    if actualites:
        for article in actualites[:6]:
            titre = article.get("title", "Sans titre")
            lien = article.get("link", "#")
            source = article.get("publisher", "Source inconnue")
            ts = article.get("providerPublishTime", 0)
            if ts:
                date_str = datetime.fromtimestamp(ts).strftime("%d/%m/%Y %H:%M")
            else:
                date_str = "Date inconnue"
            st.markdown(f"- **[{titre}]({lien})** — *{source}* — {date_str}")
    else:
        st.info("Aucune actualité disponible pour ce ticker.")

if __name__ == "__main__":
    main()
