# ⚽ Ligue 1 AI Betting Bot (V3)

Un bot de prédiction de paris sportifs pour la Ligue 1 (France), utilisant le Machine Learning (XGBoost) et l'Apprentissage par Renforcement (RL).

![Python](https://img.shields.io/badge/Python-3.9%2B-blue)
![Status](https://img.shields.io/badge/Status-Production-green)

## 📈 Performance (Backtest 2021-2025)
* **Modèle :** XGBoost Classifier (Optimisé manuellement) + Value Bet Filter
* **Stratégie :** Mise Fixe (Flat Betting)
* **Profit Net :** ~+1000€ (sur une bankroll fictive)
* **ROI :** Positif
* **Discipline :** ~60% des paris "tentants" sont filtrés par l'algorithme "Value Bet".

## 🧠 Architecture Technique

1.  **Ingestion des données (`collectors/`)**
    * Scraping des résultats et cotes historiques (Football-Data.co.uk).
    * Scraping des actualités et analyse de sentiment (Google News RSS).

2.  **Feature Engineering**
    * Calcul de la "Forme" des équipes (5 derniers matchs).
    * Moyennes mobiles Attaque/Défense.

3.  **Cerveau V1 : Le Predictor (`models/predictor_v3.py`)**
    * Algorithme : **XGBoost**.
    * Entraînement sur historique complet (Walk-Forward).
    * Sortie : Probabilités de victoire (1, N, 2).

4.  **Cerveau V2 : Le Manager (`models/rl_agent.py`)**
    * Algorithme : **Q-Learning**.
    * Rôle : Apprend des erreurs passées pour valider ou bloquer les paris du Predictor.

5.  **Exécution & Alertes (`simulation/paper_trader.py`)**
    * Filtre mathématique "Value Bet" (Confiance > 1/Cote + 5%).
    * Notification en temps réel via **Telegram**.

## 🚀 Comment l'utiliser

### 1. Installation
```bash
git clone [https://github.com/ton-pseudo/ligue1-bot.git](https://github.com/ton-pseudo/ligue1-bot.git)
cd ligue1-bot
pip install -r requirements.txt