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
        self.fixed_stake = 100.0  # RETOUR À LA MISE FIXE GAGNANTE

    def place_new_bets(self):
        conn = self.db.get_connection()
        cursor = conn.cursor()

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

            # 1. PRÉDICTION
            pred_label, confidence = self.predictor.predict_match(home, away, odd_h, odd_d, odd_a)
            pred_code = pred_label.split(' ')[0] 
            
            odds_taken = 0.0
            if pred_code == '1': odds_taken = odd_h
            elif pred_code == 'N': odds_taken = odd_d
            elif pred_code == '2': odds_taken = odd_a

            # 2. FILTRE VALUE BET
            implied_proba = 1 / odds_taken
            margin = 0.05 
            if confidence < (implied_proba + margin):
                print(f"📉 [NO VALUE] {home}-{away}")
                continue 

            # 3. DÉCISION RL
            action = self.rl_agent.decide_action(confidence)
            if action == 0:
                print(f"🛑 [RL SKIP] {home}-{away} (Conf: {confidence:.2f})")
                continue 

            # 4. MISE FIXE (La stratégie championne)
            stake = self.fixed_stake

            # 5. ENREGISTREMENT
            cursor.execute('''
                INSERT INTO bets (match_id, prediction, confidence, stake, odds_taken, result, bet_date, model_version)
                VALUES (?, ?, ?, ?, ?, 'PENDING', ?, 'V3-Champion')
            ''', (match_id, pred_code, confidence, stake, odds_taken, datetime.now().strftime("%Y-%m-%d")))
            
            print(f"✅ [BET] {home}-{away} : {pred_code} (@{odds_taken}) | Mise: {stake}€")

            # 6. TELEGRAM
            try:
                msg = (
                    f"🚨 **NOUVEAU PARI !** 🚨\n"
                    f"⚽ {home} vs {away}\n"
                    f"📊 Prono : {pred_code}\n"
                    f"💰 Cote : {odds_taken}\n"
                    f"🧠 Conf : {confidence:.2f}"
                )
                self.notifier.send_message(msg)
            except: pass

        conn.commit()
        conn.close()

    def check_results(self):
        """Vérifie les paris terminés, calcule les gains, entraîne l'Agent RL et notifie Telegram."""
        conn = self.db.get_connection()
        cursor = conn.cursor()

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

        print(f"📊 Mise à jour et APPRENTISSAGE sur {len(rows)} paris...")

        # Préparation du message Telegram
        telegram_report = "📊 **BILAN DU WEEK-END** 📊\n\n"
        total_profit = 0.0
        wins = 0
        losses = 0

        for row in rows:
            bet_id, prediction, stake, odds, h_score, a_score, confidence, home, away = row
            
            actual_result = 'N'
            if h_score > a_score: actual_result = '1'
            elif a_score > h_score: actual_result = '2'

            profit = 0.0
            status = 'LOSE'
            
            if prediction == actual_result:
                status = 'WIN'
                profit = (stake * odds) - stake
                wins += 1
            else:
                profit = -stake
                losses += 1

            cursor.execute('UPDATE bets SET result = ?, profit = ? WHERE id = ?', (status, profit, bet_id))
            
            # Mise à jour bankroll & Agent
            self.current_bankroll += profit
            self.rl_agent.learn(confidence, action=1, reward=profit)
            
            # Ajout au rapport Telegram
            icon = "✅" if status == 'WIN' else "❌"
            telegram_report += f"{icon} {home} vs {away}\n"
            telegram_report += f"   Prono: {prediction} | Résultat: {h_score}-{a_score}\n"
            telegram_report += f"   Profit: {profit:+.2f}€\n\n"
            
            print(f"   {icon} Pari #{bet_id} : {status} ({profit:+.2f}€)")

        # Fin du rapport
        telegram_report += f"----------------------\n"
        telegram_report += f"🏆 **Total Session :** {total_profit:+.2f}€\n"
        telegram_report += f"📈 **Win Rate :** {wins}/{wins+losses}"

        conn.commit()
        conn.close()
        
        # Envoi du bilan sur Telegram
        try:
            self.notifier.send_message(telegram_report)
        except Exception as e:
            print(f"⚠️ Erreur Telegram Bilan : {e}")

if __name__ == "__main__":
    trader = PaperTrader()
    trader.place_new_bets()
    trader.check_results()