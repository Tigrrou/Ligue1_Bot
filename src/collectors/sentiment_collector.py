import requests
from bs4 import BeautifulSoup
import datetime
from src.database import BettingDB

class SentimentCollector:
    def __init__(self):
        self.db = BettingDB()
        self.teams = [
            "PSG", "Marseille", "Lyon", "Monaco", "Lille", "Lens", "Rennes", "Nice",
            "Strasbourg", "Reims", "Montpellier", "Toulouse", "Nantes", "Le Havre",
            "Brest", "Lorient", "Metz", "Saint-Etienne", "Auxerre", "Angers" # J'ai mis à jour pour 2024/2025 ;)
        ]
        self.lexicon = {
            "victoire": 0.8, "gagne": 0.7, "exploit": 0.9, "confiance": 0.6,
            "but": 0.3, "champions": 0.5, "incroyable": 0.6, "solide": 0.5,
            "retour": 0.3, "forme": 0.4, "ambition": 0.3, "leader": 0.5,
            "défaite": -0.8, "perd": -0.7, "crise": -0.9, "blessure": -0.6,
            "forfait": -0.5, "doute": -0.4, "tensions": -0.6, "battu": -0.7,
            "catastrophe": -0.9, "honte": -0.8, "problème": -0.4, "absent": -0.3,
            "danger": -0.5, "relégation": -0.8
        }

    def analyze_sentiment(self, text):
        text = text.lower()
        score = 0.0
        word_count = 0
        for word, weight in self.lexicon.items():
            if word in text:
                score += weight
                word_count += 1
        if word_count > 0:
            final_score = score / word_count
            return max(-1.0, min(1.0, final_score))
        return 0.0

    def fetch_news(self):
        conn = self.db.get_connection()
        cursor = conn.cursor()
        ph = self.db.get_placeholder() # Récupère ? ou %s
        
        total_news = 0
        today = datetime.datetime.now().strftime("%Y-%m-%d")

        print(f"📰 Récupération des actualités pour {len(self.teams)} équipes...")

        for team in self.teams:
            url = f"https://news.google.com/rss/search?q={team}+football+ligue+1&hl=fr&gl=FR&ceid=FR:fr"
            try:
                response = requests.get(url, timeout=5)
                if response.status_code == 200:
                    soup = BeautifulSoup(response.content, features="xml")
                    items = soup.find_all("item")
                    for item in items[:5]:
                        title = item.title.text
                        score = self.analyze_sentiment(title)
                        
                        # Requête dynamique
                        query = f'''
                            INSERT INTO sentiments (date, team, sentiment_score, source_text)
                            VALUES ({ph}, {ph}, {ph}, {ph})
                        '''
                        cursor.execute(query, (today, team, score, title))
                        total_news += 1
            except Exception as e:
                print(f"⚠️ Erreur pour {team}: {e}")

        conn.commit()
        conn.close()
        print(f"🧠 Analyse terminée. {total_news} articles stockés.")

if __name__ == "__main__":
    SentimentCollector().fetch_news()