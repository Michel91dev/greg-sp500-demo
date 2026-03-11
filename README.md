# 📈 Analyse Boursière — Streamlit App v2.6.x

Application d'analyse d'actions boursières personnelle pour **Romain, Roger et Michel**.
Déployée sur Streamlit Community Cloud, données via Yahoo Finance, ISIN persistés dans MySQL sur VPS Hostinger.

---

## Table des matières

1. [Fonctionnalités](#fonctionnalités)
2. [Architecture du projet](#architecture-du-projet)
3. [Interface utilisateur](#interface-utilisateur)
4. [Indicateurs techniques](#indicateurs-techniques)
5. [Persistance MySQL — Infrastructure](#persistance-mysql--infrastructure)
6. [Configuration Streamlit Cloud](#configuration-streamlit-cloud)
7. [Installation et lancement local](#installation-et-lancement-local)
8. [Déploiement](#déploiement)
9. [Gestion des versions](#gestion-des-versions)
10. [Dépendances](#dépendances)
11. [Maintenance et opérations](#maintenance-et-opérations)

---

## Fonctionnalités

### Sidebar de navigation
- **Sélection d'utilisateur** : Michel, Roger, Romain — chacun avec ses propres portefeuilles
- **Liste PEA / TITRES** : affichage en cartouches séparés par catégorie
- **Signal de recommandation coloré** : 🟢 Acheter / 🟡 Attente / 🔴 Vendre / ⚪ Neutre
- **Sélection visuelle** : boule de signal entourée en rouge sur la ligne active, flèches ▶▶▶ ◄◄◄
- **Tri des actions** : alphabétique, par signal Acheter en premier, par signal Vendre en premier
- **Affichage ISIN** : optionnel, affiché entre parenthèses dans chaque cartouche

### Gestion des ISIN
- **Cartouche "🔑 Gérer les ISIN"** : ajout, modification, suppression d'ISIN par ticker
- **Validation format** : regex `^[A-Z]{2}[A-Z0-9]{10,12}$`
- **Persistance MySQL** : chaque modification est immédiatement sauvegardée en base de données
- **Par utilisateur** : Michel, Roger et Romain ont chacun leurs propres ISIN indépendants
- **Fallback** : si MySQL inaccessible, les ISIN par défaut (hardcodés) sont utilisés sans erreur visible

### Analyse technique
- Graphique de cours interactif (Plotly) avec chandeliers ou ligne
- Moyennes mobiles MA50 / MA200
- MACD (Moving Average Convergence Divergence)
- RSI (Relative Strength Index)
- Bandes de Bollinger
- Golden Cross / Death Cross détectés automatiquement
- Volume de transactions

### Informations société
- Fiche descriptive de l'entreprise (secteur, pays, capitalisation, P/E ratio…)
- Actualités récentes récupérées via Yahoo Finance

---

## Architecture du projet

```
greg-sp500-demo/
├── streamlit_sp500_demo.py   # Application principale (code unique)
├── requirements.txt          # Dépendances Python (pip)
├── version.txt               # Numéro de version courante (ex: 2.6.1)
├── populate_isin.sql         # Script SQL de population initiale des ISIN
└── README.md                 # Cette documentation
```

### Flux de données

```
Yahoo Finance (yfinance)
        │
        ▼
streamlit_sp500_demo.py
        │
        ├── Calcul indicateurs techniques (MACD, RSI, BB, MA...)
        ├── Affichage graphiques (Plotly)
        ├── Lecture ISIN personnalisés ──► MySQL (VPS Hostinger)
        └── Sauvegarde ISIN modifiés ───► MySQL (VPS Hostinger)
```

---

## Interface utilisateur

### Cartouches sidebar (pattern validé v2.6.0 ⭐)

Chaque ligne de ticker utilise **3 colonnes Streamlit** `[1, 8, 1]` :

```
[🟢]  [ ASML → Acheter (NL0000285116)  ]  [🗑️]
 ↑           ↑ bouton centré               ↑
 boule      (signal + ISIN en texte)     poubelle
 markdown
```

- La **boule** est un `st.markdown` HTML libre (permet le CSS)
- Le **bouton** est un `st.button` standard (pas de HTML dans le label)
- La **boule est entourée** d'un cercle rouge `border: 4px solid #C62828` sur la ligne active
- Le **texte du bouton** affiche `▶▶▶ nom → signal (ISIN) ◄◄◄` sur la ligne active

### CSS global appliqué

```css
/* Alignement gauche du contenu des boutons */
[data-testid="stSidebarContent"] .stButton > button {
    display: flex;
    justify-content: flex-start;
    align-items: center;
}
/* Réduction espacement entre colonnes */
[data-testid="stSidebarContent"] [data-testid="stHorizontalBlock"] {
    gap: 4px;
}
```

---

## Indicateurs techniques

| Indicateur | Période | Signal généré |
|------------|---------|---------------|
| MA50 / MA200 | 50 / 200 jours | Acheter si MA50 > MA200 |
| MACD | 12 / 26 / 9 | Acheter si MACD > Signal |
| RSI | 14 jours | Survente < 30, Surachat > 70 |
| Bandes de Bollinger | 20 jours, σ=2 | Cassure haute/basse |
| Golden Cross | MA50 > MA200 | Signal haussier fort |
| Death Cross | MA50 < MA200 | Signal baissier fort |

**Recommandation finale** : combinaison pondérée de ces indicateurs → Acheter / Attente / Vendre / Neutre.

---

## Persistance MySQL — Infrastructure

### Serveur

| Élément | Valeur |
|---------|--------|
| Hébergeur | Hostinger VPS |
| IP publique | `76.13.49.53` |
| OS | Ubuntu 24.04 LTS |
| Runtime | Docker 29.2.1 |
| Conteneur | `mysql-bourse` (image `mysql:8.0`) |
| Port exposé | `3306` |

### Base de données

```
Base    : bourse_isin
User    : bourse_user
Table   : isin_utilisateurs
```

### Schéma de la table

```sql
CREATE TABLE isin_utilisateurs (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    utilisateur VARCHAR(50)  NOT NULL,
    ticker      VARCHAR(20)  NOT NULL,
    isin        VARCHAR(14)  NOT NULL,
    categorie   VARCHAR(20)  NOT NULL DEFAULT 'PEA',
    date_modif  TIMESTAMP    DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY unique_user_ticker (utilisateur, ticker)
);
```

> **Note :** `VARCHAR(14)` car certains ISIN (ex: `FR001400AYG6`) dépassent 12 caractères.

### Fonctions Python dans le code

```python
get_connexion_mysql()                                    # Connexion via st.secrets["mysql"]
charger_isin_mysql(utilisateur: str) -> dict             # SELECT au démarrage de l'app
sauvegarder_isin_mysql(utilisateur, ticker, isin, cat)   # INSERT ... ON DUPLICATE KEY UPDATE
supprimer_isin_mysql(utilisateur: str, ticker: str)      # DELETE par utilisateur + ticker
```

### Données initiales

74 ISIN pré-chargés via `populate_isin.sql` :
- **Michel** : 9 PEA + 15 TITRES = 24 lignes
- **Romain** : 16 PEA + 2 TITRES = 18 lignes
- **Roger** : 7 PEA + 25 TITRES = 32 lignes

### Commandes de maintenance MySQL

```bash
# Vérifier que le conteneur tourne
docker ps | grep mysql-bourse

# Voir tous les ISIN
docker exec -i mysql-bourse mysql -u bourse_user -pBoursePass2024! bourse_isin \
  -e "SELECT utilisateur, COUNT(*) as nb FROM isin_utilisateurs GROUP BY utilisateur;"

# Voir les ISIN d'un utilisateur
docker exec -i mysql-bourse mysql -u bourse_user -pBoursePass2024! bourse_isin \
  -e "SELECT ticker, isin, categorie FROM isin_utilisateurs WHERE utilisateur='Michel' ORDER BY categorie, ticker;"

# Repeupler depuis le script SQL (si besoin de reset)
docker exec -i mysql-bourse mysql -u bourse_user -pBoursePass2024! bourse_isin < populate_isin.sql

# Redémarrer le conteneur MySQL si arrêté
docker start mysql-bourse
```

---

## Configuration Streamlit Cloud

Les credentials MySQL sont stockés dans **Streamlit Secrets** (jamais dans le code source).

### Accès : [share.streamlit.io](https://share.streamlit.io) → App → Settings → Secrets

```toml
[mysql]
host = "76.13.49.53"
port = 3306
database = "bourse_isin"
user = "bourse_user"
password = "..."
```

> ⚠️ **Sécurité** : ne jamais committer les credentials dans Git. Le mot de passe réel est dans Streamlit Secrets uniquement.

---

## Installation et lancement local

### Prérequis

- Python 3.11+ (via Homebrew sur macOS)
- Accès MySQL (VPS Hostinger ou local)

### Installation

```bash
# Cloner le dépôt
git clone https://github.com/Michel91dev/greg-sp500-demo.git
cd greg-sp500-demo

# Créer l'environnement virtuel
python3 -m venv .venv
source .venv/bin/activate

# Installer les dépendances
pip install -r requirements.txt
```

### Configuration MySQL en local

Créer le fichier `.streamlit/secrets.toml` (non versionné) :

```toml
[mysql]
host = "76.13.49.53"
port = 3306
database = "bourse_isin"
user = "bourse_user"
password = "..."
```

### Lancement

```bash
streamlit run streamlit_sp500_demo.py
```

L'application s'ouvre à http://localhost:8501

---

## Déploiement

- **Plateforme** : Streamlit Community Cloud
- **Branche déployée** : `main`
- **Déclencheur** : chaque push sur `main` déclenche un redéploiement automatique (~1 min)
- **Branche de développement** : `Version-avec-iphone`

### Workflow de déploiement

```bash
# Développer sur la branche Version-avec-iphone
git checkout Version-avec-iphone
# ... modifications ...
git add -A && git commit -m "Description du changement"

# Merger sur main pour déployer
git checkout main
git merge Version-avec-iphone
git push origin main
git checkout Version-avec-iphone
```

---

## Gestion des versions

Le fichier `version.txt` contient le numéro de version courant, affiché dans la sidebar de l'app.

| Version | Description |
|---------|-------------|
| 2.5.23 | Version de référence cartouches sidebar |
| 2.5.31 | ISIN dans les cartouches (texte brut) |
| 2.5.34 | Boule séparée en colonne, cercle rouge sélection |
| 2.5.35 | Bordure boule 4px |
| 2.6.0  | **Version stable de qualité ⭐** — sidebar finalisée |
| 2.6.1  | Persistance ISIN via MySQL (VPS Hostinger) |

---

## Dépendances

```
streamlit>=1.29.0    # Framework web interactif
yfinance>=0.2.28     # Données boursières Yahoo Finance
plotly>=5.17.0       # Graphiques interactifs
pandas>=2.2.0        # Manipulation et analyse de données
pymysql>=1.1.0       # Connexion MySQL (persistance ISIN)
```

---

## Maintenance et opérations

### Ajouter un nouveau ticker pour un utilisateur

1. Ajouter le ticker dans `actions_par_utilisateur` dans `streamlit_sp500_demo.py`
2. Ajouter l'ISIN dans le dict `isin_actions` (valeur par défaut)
3. Mettre à jour `populate_isin.sql` avec la nouvelle ligne
4. Exécuter l'INSERT sur le VPS ou via l'interface "🔑 Gérer les ISIN" dans l'app
5. Incrémenter `version.txt` et pousser sur `main`

### Vérifier la santé de l'infrastructure

```bash
# Sur le VPS Hostinger (terminal web hPanel ou SSH)
docker ps                          # Vérifier que mysql-bourse tourne
docker logs mysql-bourse --tail=20 # Voir les derniers logs MySQL
ufw status                         # Vérifier que le port 3306 est ouvert
```

### Redémarrage d'urgence MySQL

```bash
docker restart mysql-bourse
# Attendre 10 secondes puis vérifier
docker exec -i mysql-bourse mysql -u bourse_user -pBoursePass2024! bourse_isin -e "SHOW TABLES;"
```

### Sauvegarde des données

```bash
# Export complet de la table ISIN
docker exec mysql-bourse mysqldump -u bourse_user -pBoursePass2024! bourse_isin isin_utilisateurs > backup_isin_$(date +%Y%m%d).sql
```
