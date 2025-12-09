import os
import requests
from dotenv import load_dotenv

# On charge les variables du fichier .env
load_dotenv()

class TelegramNotifier:
    def __init__(self):
        self.token = os.getenv("TELEGRAM_TOKEN")
        self.chat_id = os.getenv("TELEGRAM_CHAT_ID")
        
        if not self.token or not self.chat_id:
            print("⚠️ Attention : Identifiants Telegram non trouvés dans le fichier .env")

    def send_message(self, message):
        """Envoie un message texte sur Telegram."""
        if not self.token or not self.chat_id:
            return

        url = f"https://api.telegram.org/bot{self.token}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": message,
            "parse_mode": "Markdown" # Permet de mettre du gras avec **texte**
        }
        
        try:
            response = requests.post(url, data=payload)
            if response.status_code == 200:
                print("📩 Notification Telegram envoyée !")
            else:
                print(f"❌ Erreur Telegram : {response.text}")
        except Exception as e:
            print(f"❌ Erreur connexion Telegram : {e}")

# --- Test rapide ---
if __name__ == "__main__":
    bot = TelegramNotifier()
    bot.send_message("👋 Salut ! Ceci est un test depuis ton **Ligue 1 Bot** ⚽")