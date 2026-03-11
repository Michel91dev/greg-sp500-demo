# Analyse Boursière — Streamlit App v2.6.x

Application d'analyse d'actions boursières pour Romain, Roger et Michel.

## Fonctionnalités

- **Sidebar multi-utilisateur** : Michel, Roger, Romain — chacun avec ses propres actions
- **Liste PEA / TITRES** : cartouches avec signal coloré (🟢 Acheter / 🟡 Attente / 🔴 Vendre)
- **Sélection visuelle** : boule de signal séparée, encadrée en rouge sur la ligne active (▶▶▶ ◄◄◄)
- **ISIN persistants par utilisateur** : stockés dans MySQL (VPS Hostinger), plus de perte au redémarrage
- **Gestion ISIN** : ajout, modification, suppression via le cartouche "🔑 Gérer les ISIN"
- **Tri** : alphabétique, signal Acheter en 1er, signal Vendre en 1er
- **Indicateurs techniques** : MACD, RSI, Moyennes mobiles, Golden/Death Cross, Bandes de Bollinger
- **Graphiques interactifs** : Plotly (cours, volume, indicateurs)
- **Infos société** : fiche + actualités Yahoo Finance en bas de page

## Architecture

```
streamlit_sp500_demo.py   # Application principale
requirements.txt          # Dépendances Python
version.txt               # Version courante
```

### Persistance des ISIN — MySQL (VPS Hostinger)

Les ISIN personnalisés par utilisateur sont stockés dans une base MySQL hébergée sur le VPS Hostinger (`76.13.49.53`), dans un conteneur Docker.

**Table :**
```sql
CREATE TABLE isin_utilisateurs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    utilisateur VARCHAR(50) NOT NULL,
    ticker VARCHAR(20) NOT NULL,
    isin VARCHAR(14) NOT NULL,
    categorie VARCHAR(20) NOT NULL DEFAULT 'PEA',
    date_modif TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY unique_user_ticker (utilisateur, ticker)
);
```

**Fonctions dans le code :**
- `charger_isin_mysql(utilisateur)` — lecture au démarrage
- `sauvegarder_isin_mysql(utilisateur, ticker, isin, categorie)` — écriture
- `supprimer_isin_mysql(utilisateur, ticker)` — suppression

**Fallback :** si MySQL est inaccessible, les ISIN par défaut hardcodés sont utilisés sans erreur.

## Configuration Streamlit Cloud

Les credentials MySQL doivent être dans **Streamlit Secrets** (Settings → Secrets) :

```toml
[mysql]
host = "76.13.49.53"
port = 3306
database = "bourse_isin"
user = "bourse_user"
password = "..."
```

⚠️ Ne jamais mettre les credentials dans le code source.

## Installation locale

```bash
# Créer un environnement virtuel
python3 -m venv .venv
source .venv/bin/activate

# Installer les dépendances
pip install -r requirements.txt
```

Pour tester en local sans MySQL, créer un fichier `.streamlit/secrets.toml` avec les credentials.

## Lancement local

```bash
streamlit run streamlit_sp500_demo.py
```

L'application s'ouvre à l'adresse http://localhost:8501

## Déploiement

L'app est déployée sur **Streamlit Community Cloud** depuis la branche `main`.
Chaque push sur `main` déclenche un redéploiement automatique.

## Dépendances principales

| Package | Usage |
|---------|-------|
| `streamlit` | Framework web |
| `yfinance` | Données boursières Yahoo Finance |
| `plotly` | Graphiques interactifs |
| `pandas` | Manipulation des données |
| `pymysql` | Connexion MySQL (persistance ISIN) |
