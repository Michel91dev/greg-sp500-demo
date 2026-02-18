# DEVBOOK - Analyse Actions (Bourse Roger)

## Description
Application Streamlit d'analyse technique d'actions boursières pour Romain, Roger et Michel.
Déployée sur Streamlit Cloud : bourse200-50.streamlit.app

## Règles de développement
- **Toujours incrémenter la version** dans `version.txt` à chaque commit
- **Numérotation flexible** : v2.5.23, v3.10.15, etc. (pas de limite à 10)
- **Toujours merger dans `main`** avant push (Streamlit Cloud déploie depuis `main`)
- **Pas de `<script>` dans Streamlit** : `st.markdown()` ne supporte pas le JavaScript
- **Tester sur iPhone** après chaque modification CSS mobile

## Historique des versions

### v2.5.6
- Catégories PEA/TITRES sans radio, trait bleu traversant pour séparation visuelle
- Deux radios séparés par catégorie avec keys distinctes
- Design centré pour les titres de catégories

### v2.5.5
- Catégories PEA/TITRES pour tous les utilisateurs
- Affichage avec séparateurs visuels
- Structure imbriquée (PEA/TITRES) mais traitement aplati

### v2.5.4
- Ajout Dassault Aviation (AM.PA) pour Romain

### v2.5.3
- Chevrons sidebar rouge style bouton bien visible
- 7 nouveaux tickers Romain (Bayer, Veolia, ETFs Amundi, EchoStar)

### v2.5.2
- Fix sidebar : header visible pour bouton réouverture
- Actions Romain mises à jour (10 nouveaux tickers)

### v2.5.1
- Perf max : signaux en parallèle (ThreadPool 10 workers)
- 1 seul appel API par action (données + capitalisation fusionnés)
- Retrait splashscreen

### v2.5.0
- Fix double-clic radio (key= au lieu de index=)
- Splashscreen natif st.status() (retiré depuis)

### v2.4.9
- Splashscreen avec spinner au premier lancement
- Disparaît après chargement des signaux

### v2.4.8
- Retrait splashscreen

### v2.4.7
- Ajout splashscreen pendant le chargement des signaux

### v2.4.6
- Optimisation performance : cache API Yahoo Finance (@st.cache_data)
- Signaux sidebar : cache 15 min
- Données historiques : cache 15 min
- Capitalisation boursière : cache 1h

### v2.4.5
- Fix sidebar iPhone : approche CSS pure compatible Streamlit
- initial_sidebar_state="collapsed" pour sidebar fermée par défaut
- Header réaffiché sur mobile pour bouton hamburger natif

### v2.4.4
- Ajout capitalisation boursière dans les métriques principales
- Tentative sidebar mobile (JS retiré car non supporté par Streamlit)
- CSS mobile : sidebar cachée par défaut, bouton rond bleu

### v2.4.3
- CSS ultra-agressif : body, stApp, main, tous les conteneurs avec margin/padding 0

### v2.4.2
- CSS agressif pour supprimer tout espace en haut (header caché, margin/padding 0)

### v2.4.1
- Suppression espace en haut (padding-top: 0)

### v2.4.0 - VERSION STABLE
- Interface optimisée, 34 actions pour Roger, espacement compact

### v2.3.28
- Ajout 16 actions pour Roger (Palantir, Abivax, NextEra, Safran, Airbus, ASML, Meta, etc.)

### v2.3.27
- Ajustement espacement vertical: gap 0.25rem pour éviter chevauchement textes

### v2.3.26
- Ajout 18 actions pour Roger (TSMC, NVIDIA, Broadcom, Visa, AMD, etc.)

### v2.3.25
- Espacement zéro entre alertes colorées, tout le haut ultra-compact

### v2.3.24
- Réorganisation recommandation trading: signaux pleine largeur + espacement ultra-compact

## Prochaines étapes
- [ ] Sidebar accessible sur iPhone (bouton menu visible et fonctionnel)
- [ ] Tester responsive sur différentes tailles d'écran
