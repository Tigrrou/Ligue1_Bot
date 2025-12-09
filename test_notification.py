from src.utils.notifier import TelegramNotifier

def test_fake_match_notification():
    print("🚀 Démarrage du test de notification Telegram...")
    
    # 1. On initialise le notificateur
    notifier = TelegramNotifier()
    
    # 2. On invente des données de match fictif (Scénario de rêve)
    home_team = "FC Test Domicile"
    away_team = "FC Test Extérieur"
    pred_code = "1"     # Le bot prédit une victoire domicile
    odds_taken = 2.45   # Belle cote
    confidence = 0.88   # Très confiant (88%)
    
    # 3. On construit le message EXACTEMENT comme dans paper_trader.py
    msg = (
        f"🚨 **TEST - NOUVEAU PARI DÉTECTÉ !** 🚨\n\n"
        f"⚽ **Match :** {home_team} vs {away_team}\n"
        f"📊 **Prono :** {pred_code}\n"
        f"💰 **Cote :** {odds_taken}\n"
        f"🧠 **Confiance :** {confidence:.2f}\n"
        f"🤖 **Validé par :** XGBoost + RL Agent"
    )
    
    # 4. Envoi
    print(f"📨 Envoi du message pour : {home_team} vs {away_team}")
    notifier.send_message(msg)

if __name__ == "__main__":
    test_fake_match_notification()