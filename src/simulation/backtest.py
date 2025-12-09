import pandas as pd
import sqlite3
import joblib
import os
import matplotlib.pyplot as plt
import seaborn as sns
import xgboost as xgb
from src.database import BettingDB
from src.models.predictor_v3 import PredictorV3
from src.models.rl_agent import RLAgent

class Backtester:
    def __init__(self):
        self.db = BettingDB()
        self.predictor = PredictorV3()
        # Reset RL Agent
        if os.path.exists("data/q_table.json"):
            os.remove("data/q_table.json")
        self.rl_agent = RLAgent() 
        self.fixed_stake = 100.0

    def run_backtest(self):
        print("⏳ Chargement de l'historique...")
        X_all, y_all = self.predictor.load_and_prepare_data()
        
        conn = self.db.get_connection()
        raw_df = pd.read_sql_query("SELECT * FROM matches WHERE status = 'FINISHED' ORDER BY date ASC", conn)
        conn.close()
        
        min_len = min(len(raw_df), len(X_all))
        raw_df = raw_df.iloc[:min_len]
        X_all = X_all.iloc[:min_len]
        y_all = y_all.iloc[:min_len]

        split_index = 400 

        # --- BOOTCAMP ---
        print(f"🏋️ Entraînement sur {split_index} matchs...")
        X_train = X_all.iloc[:split_index]
        y_train = y_all.iloc[:split_index]
        
        self.predictor.model = xgb.XGBClassifier(
            n_estimators=200, learning_rate=0.05, max_depth=5,
            objective='multi:softprob', num_class=3, eval_metric='mlogloss', random_state=42
        )
        self.predictor.model.fit(X_train, y_train)

        # --- SIMULATION ---
        print(f"🚀 Simulation (Mise Fixe 100€)...")
        history = []
        bankroll = 0
        bets = 0
        
        test_indices = range(split_index, len(raw_df))
        
        for i in test_indices:
            row = raw_df.iloc[i]
            features = X_all.iloc[[i]]
            
            pred_idx = self.predictor.model.predict(features)[0]
            probs = self.predictor.model.predict_proba(features)[0]
            confidence = probs[pred_idx]
            mapping = {0: '1', 1: 'N', 2: '2'}
            pred_code = mapping[pred_idx]
            
            odds = 0.0
            if pred_code == '1': odds = row['home_odds']
            elif pred_code == 'N': odds = row['draw_odds']
            elif pred_code == '2': odds = row['away_odds']
            
            if odds <= 1.0: continue

            # VALUE FILTER
            if confidence < (1/odds + 0.05): continue

            # RL AGENT
            action = self.rl_agent.decide_action(confidence)
            if action == 0: continue
            
            # MISE FIXE
            stake = self.fixed_stake
            bets += 1
            
            actual = 'N'
            if row['home_score'] > row['away_score']: actual = '1'
            elif row['away_score'] > row['home_score']: actual = '2'
            
            profit = -stake
            if pred_code == actual: profit = (stake * odds) - stake
            
            bankroll += profit
            self.rl_agent.learn(confidence, 1, profit)
            history.append(bankroll)

        print(f"🏁 PROFIT FINAL : {bankroll:.2f} € ({bets} paris)")
        return history

    def plot_results(self, history):
        if not history: return
        plt.figure(figsize=(12, 6))
        sns.set_theme(style="darkgrid")
        sns.lineplot(data=history, color='#00ff00')
        plt.axhline(0, color='red', linestyle='--')
        plt.title(f"Backtest V3 Champion : {len(history)} paris", fontsize=16)
        plt.fill_between(range(len(history)), history, alpha=0.1, color='green')
        plt.savefig("backtest_champion.png")
        print("📈 Graphique généré.")

if __name__ == "__main__":
    bt = Backtester()
    h = bt.run_backtest()
    bt.plot_results(h)