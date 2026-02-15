# -*- coding: utf-8 -*-
"""
Application Flask pour déploiement sur Render/Heroku
"""

from flask import Flask, render_template_string, request, jsonify
import yfinance as yf
import pandas as pd
import json
from datetime import datetime, timedelta

app = Flask(__name__)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>S&P 500 Demo</title>
    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; background: white; padding: 20px; border-radius: 10px; }
        .header { text-align: center; margin-bottom: 30px; }
        .metrics { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin-bottom: 30px; }
        .metric { background: #f8f9fa; padding: 15px; border-radius: 8px; text-align: center; }
        .metric-value { font-size: 24px; font-weight: bold; color: #007bff; }
        .metric-label { font-size: 14px; color: #666; }
        .chart { margin-bottom: 30px; }
        .controls { margin-bottom: 20px; }
        select { padding: 8px; border-radius: 4px; border: 1px solid #ddd; }
        .loading { text-align: center; padding: 20px; }
        .error { color: red; text-align: center; padding: 20px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📈 S&P 500 Demo</h1>
            <p>Visualisation de l'indice S&P 500</p>
        </div>

        <div class="controls">
            <label for="periode">Période :</label>
            <select id="periode" onchange="loadData()">
                <option value="1mo">1 mois</option>
                <option value="3mo" selected>3 mois</option>
                <option value="6mo">6 mois</option>
                <option value="1y">1 an</option>
                <option value="2y">2 ans</option>
                <option value="5y">5 ans</option>
            </select>
        </div>

        <div id="loading" class="loading" style="display: none;">Chargement...</div>
        <div id="error" class="error" style="display: none;"></div>

        <div id="metrics" class="metrics"></div>
        <div id="price-chart" class="chart"></div>
        <div id="volume-chart" class="chart"></div>
        <div id="ma-chart" class="chart"></div>
        <div id="stats"></div>
    </div>

    <script>
        async function loadData() {
            const periode = document.getElementById('periode').value;
            const loading = document.getElementById('loading');
            const error = document.getElementById('error');

            loading.style.display = 'block';
            error.style.display = 'none';

            try {
                const response = await fetch(`/data?period=${periode}`);
                const data = await response.json();

                if (data.error) {
                    throw new Error(data.error);
                }

                updateMetrics(data.metrics);
                drawCharts(data);
                updateStats(data.stats);

            } catch (err) {
                error.textContent = err.message;
                error.style.display = 'block';
            } finally {
                loading.style.display = 'none';
            }
        }

        function updateMetrics(metrics) {
            const container = document.getElementById('metrics');
            container.innerHTML = `
                <div class="metric">
                    <div class="metric-value">${metrics.prix_actuel} $</div>
                    <div class="metric-label">Prix Actuel</div>
                </div>
                <div class="metric">
                    <div class="metric-value" style="color: ${metrics.variation > 0 ? 'green' : 'red'}">
                        ${metrics.variation > 0 ? '+' : ''}${metrics.variation}%
                    </div>
                    <div class="metric-label">Variation</div>
                </div>
                <div class="metric">
                    <div class="metric-value">${metrics.plus_haut} $</div>
                    <div class="metric-label">Plus Haut</div>
                </div>
                <div class="metric">
                    <div class="metric-value">${metrics.plus_bas} $</div>
                    <div class="metric-label">Plus Bas</div>
                </div>
            `;
        }

        function drawCharts(data) {
            // Graphique prix
            const priceTrace = {
                x: data.dates,
                y: data.prices,
                type: 'scatter',
                mode: 'lines',
                name: 'Prix S&P 500',
                line: {color: '#007bff'}
            };

            Plotly.newPlot('price-chart', [priceTrace], {
                title: `S&P 500 - ${data.periode}`,
                xaxis: {title: 'Date'},
                yaxis: {title: 'Prix ($)'}
            });

            // Graphique volume
            const volumeTrace = {
                x: data.dates,
                y: data.volumes,
                type: 'bar',
                name: 'Volume',
                marker: {color: '#28a745'}
            };

            Plotly.newPlot('volume-chart', [volumeTrace], {
                title: 'Volume de transactions',
                xaxis: {title: 'Date'},
                yaxis: {title: 'Volume'}
            });

            // Moyennes mobiles
            const maTraces = [
                {
                    x: data.ma_dates,
                    y: data.ma_prices,
                    type: 'scatter',
                    mode: 'lines',
                    name: 'Prix',
                    line: {color: '#007bff'}
                },
                {
                    x: data.ma_dates,
                    y: data.ma20,
                    type: 'scatter',
                    mode: 'lines',
                    name: 'MA20',
                    line: {color: '#ffc107'}
                },
                {
                    x: data.ma_dates,
                    y: data.ma50,
                    type: 'scatter',
                    mode: 'lines',
                    name: 'MA50',
                    line: {color: '#dc3545'}
                }
            ];

            Plotly.newPlot('ma-chart', maTraces, {
                title: 'Prix et moyennes mobiles',
                xaxis: {title: 'Date'},
                yaxis: {title: 'Prix ($)'}
            });
        }

        function updateStats(stats) {
            const container = document.getElementById('stats');
            container.innerHTML = `
                <h3>📈 Statistiques</h3>
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px;">
                    <div>
                        <h4>Informations</h4>
                        <ul>
                            <li>Période: ${stats.periode}</li>
                            <li>Nombre de jours: ${stats.nb_jours}</li>
                            <li>Volatilité: ${stats.volatilite}%</li>
                            <li>Rendement total: ${stats.rendement}%</li>
                        </ul>
                    </div>
                </div>
            `;
        }

        // Charger les données au démarrage
        loadData();
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/data')
def get_data():
    try:
        period = request.args.get('period', '3mo')

        # Récupération des données
        sp500 = yf.Ticker("^GSPC")
        data = sp500.history(period=period)

        if data.empty:
            return jsonify({'error': 'Impossible de charger les données'})

        # Métriques
        prix_actuel = data['Close'].iloc[-1]
        prix_precedent = data['Close'].iloc[-2] if len(data) > 1 else prix_actuel
        variation = ((prix_actuel - prix_precedent) / prix_precedent) * 100

        # Moyennes mobiles
        data['MA20'] = data['Close'].rolling(window=20).mean()
        data['MA50'] = data['Close'].rolling(window=50).mean()

        # Données pour les graphiques
        ma_data = data.tail(100).dropna()

        response = {
            'metrics': {
                'prix_actuel': f"{prix_actuel:.2f}",
                'variation': f"{variation:+.2f}",
                'plus_haut': f"{data['High'].max():.2f}",
                'plus_bas': f"{data['Low'].min():.2f}"
            },
            'dates': [date.strftime('%Y-%m-%d') for date in data.index],
            'prices': data['Close'].tolist(),
            'volumes': data['Volume'].tolist(),
            'ma_dates': [date.strftime('%Y-%m-%d') for date in ma_data.index],
            'ma_prices': ma_data['Close'].tolist(),
            'ma20': ma_data['MA20'].tolist(),
            'ma50': ma_data['MA50'].tolist(),
            'stats': {
                'periode': period,
                'nb_jours': len(data),
                'volatilite': f"{data['Close'].pct_change().std() * 100:.2f}",
                'rendement': f"{((data['Close'].iloc[-1] / data['Close'].iloc[0]) - 1) * 100:+.2f}"
            }
        }

        return jsonify(response)

    except Exception as e:
        return jsonify({'error': str(e)})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
"""

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
