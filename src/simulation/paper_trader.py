import sqlite3
import pandas as pd
from datetime import datetime
from src.database import BettingDB
from src.models.predictor_v3 import PredictorV3
from src.models.rl_agent import RLAgent
from src.utils.notifier import TelegramNotifier

class PaperTrader:
    def __init__(self):
        self.db = BettingDB()
        self.predictor = PredictorV3()
        self.rl_agent = RLAgent()
        self.notifier = TelegramNotifier()
        self.fixed_stake = 100.0

    def place_new_bets(self):
        conn = self.db.get_connection()
        cursor = conn.cursor()
        ph = self.db.get_placeholder()

        # Lecture sans paramètre -> Pas besoin de ph
        query = '''
            SELECT m.id, m.home_team, m.away_team, m.home_odds, m.draw_odds, m.away_odds
            FROM matches m
            LEFT JOIN bets b ON m.id = b.match_id
            WHERE m.status = 'SCHEDULED' AND b.id IS NULL
        '''
        rows = cursor.execute(query).fetchall()

        if not rows:
            print("💤 Aucun nouveau match à parier.")
            conn.close()
            return

        print(f"💰 Analyse de {len(rows)} matchs...")

        for row in rows:
            match_id, home, away, odd_h, odd_d, odd_a = row
            if odd_h == 0: continue

            pred_label, confidence = self.predictor.predict_match(home, away, odd_h, odd_d, odd_a)
            pred_code = pred_label.split(' ')[0] 
            
            odds_taken = 0.0
            if pred_code == '1': odds_taken = odd_h
            elif pred_code == 'N': odds_taken = odd_d
            elif pred_code == '2': odds_taken = odd_a

            implied_proba = 1 / odds_taken
            margin = 0.05 
            if confidence < (implied_proba + margin):
                print(f"📉 [NO VALUE] {home}-{away}")
                continue 

            action = self.rl_agent.decide_action(confidence)
            if action == 0:
                print(f"🛑 [RL SKIP] {home}-{away} (Conf: {confidence:.2f})")
                continue 

            stake = self.fixed_stake

            # INSERTION DYNAMIQUE
            insert_query = f'''
                INSERT INTO bets (match_id, prediction, confidence, stake, odds_taken, result, bet_date, model_version)
                VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, 'PENDING', {ph}, 'V3-Champion')
            '''
            cursor.execute(insert_query, (match_id, pred_code, confidence, stake, odds_taken, datetime.now().strftime("%Y-%m-%d")))
            
            print(f"✅ [BET] {home}-{away} : {pred_code} (@{odds_taken})")

            try:
                msg = f"🚨 **NOUVEAU PARI**\n⚽ {home} vs {away}\n📊 {pred_code} @ {odds_taken}\n🧠 Conf: {confidence:.2f}"
                self.notifier.send_message(msg)
            except Exception as e:
                print(f"⚠️ Erreur Telegram: {e}")

        conn.commit()
        conn.close()

    def check_results(self):
        conn = self.db.get_connection()
        cursor = conn.cursor()
        ph = self.db.get_placeholder()

        query = '''
            SELECT b.id, b.prediction, b.stake, b.odds_taken, m.home_score, m.away_score, b.confidence, m.home_team, m.away_team
            FROM bets b
            JOIN matches m ON b.match_id = m.id
            WHERE b.result = 'PENDING' AND m.status = 'FINISHED'
        '''
        rows = cursor.execute(query).fetchall()

        if not rows:
            print("⏳ Pas de résultats à traiter.")
            conn.close()
            return

        print(f"📊 Traitement de {len(rows)} paris...")
        telegram_report = "📊 **BILAN** 📊\n\n"
        
        for row in rows:
            bet_id, prediction, stake, odds, h_score, a_score, confidence, home, away = row
            
            actual = 'N'
            if h_score > a_score: actual = '1'
            elif a_score > h_score: actual = '2'

            status = 'WIN' if prediction == actual else 'LOSE'
            profit = (stake * odds) - stake if status == 'WIN' else -stake

            # UPDATE DYNAMIQUE
            update_query = f'UPDATE bets SET result = {ph}, profit = {ph} WHERE id = {ph}'
            cursor.execute(update_query, (status, profit, bet_id))
            
            self.rl_agent.learn(confidence, action=1, reward=profit)
            
            icon = "✅" if status == 'WIN' else "❌"
            telegram_report += f"{icon} {home}-{away} ({prediction})\n💰 {profit:+.2f}€\n\n"

        conn.commit()
        conn.close()
        
        try:
            self.notifier.send_message(telegram_report)
        except Exception as e:
            print(f"⚠️ Erreur Telegram: {e}")

if __name__ == "__main__":
    trader = PaperTrader()
    trader.place_new_bets()
    trader.check_results()