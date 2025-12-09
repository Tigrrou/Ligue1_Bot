import requests
from bs4 import BeautifulSoup
import sqlite3
import datetime
from src.database import BettingDB

class SentimentCollector:
    def __init__(self):
        self.db = BettingDB()
        # Liste des équipes (noms utilisés dans les requêtes de recherche)
        self.teams = [
            "PSG", "Marseille", "Lyon", "Monaco", "Lille", "Lens", "Rennes", "Nice",
            "Strasbourg", "Reims", "Montpellier", "Toulouse", "Nantes", "Le Havre",
            "Brest", "Lorient", "Metz", "Clermont"
        ]
        
        # Dictionnaire de sentiment "Maison" adapté au Foot Français
        self.lexicon = {
            # Positif
            "victoire": 0.8, "gagne": 0.7, "exploit": 0.9, "confiance": 0.6,
            "but": 0.3, "champions": 0.5, "incroyable": 0.6, "solide": 0.5,
            "retour": 0.3, "forme": 0.4, "ambition": 0.3, "leader": 0.5,
            
            # Négatif
            "défaite": -0.8, "perd": -0.7, "crise": -0.9, "blessure": -0.6,
            "forfait": -0.5, "doute": -0.4, "tensions": -0.6, "battu": -0.7,
            "catastrophe": -0.9, "honte": -0.8, "problème": -0.4, "absent": -0.3,
            "danger": -0.5, "relégation": -0.8
        }

    def analyze_sentiment(self, text):
        """Calcule un score de sentiment simple basé sur le lexique (-1 à 1)."""
        text = text.lower()
        score = 0.0
        word_count = 0
        
        for word, weight in self.lexicon.items():
            if word in text:
                score += weight
                word_count += 1
        
        # Normalisation sommaire
        if word_count > 0:
            final_score = score / word_count
            # On cap le score entre -1 et 1
            return max(-1.0, min(1.0, final_score))
        return 0.0

    def fetch_news(self):
        """Récupère les news via Google RSS et analyse le sentiment."""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        total_news = 0
        today = datetime.datetime.now().strftime("%Y-%m-%d")

        print(f"📰 Récupération des actualités pour {len(self.teams)} équipes...")

        for team in self.teams:
            # URL Google News RSS pour l'équipe spécifique
            url = f"https://news.google.com/rss/search?q={team}+football+ligue+1&hl=fr&gl=FR&ceid=FR:fr"
            
            try:
                response = requests.get(url, timeout=5)
                if response.status_code == 200:
                    soup = BeautifulSoup(response.content, features="xml")
                    items = soup.find_all("item")
                    
                    # On prend les 5 dernières news max par équipe pour ne pas spammer la DB
                    for item in items[:5]:
                        title = item.title.text
                        
                        # Calcul du sentiment
                        score = self.analyze_sentiment(title)
                        
                        # On ne stocke que si le sentiment n'est pas neutre (Optionnel, mais économise de la place)
                        # Ou on stocke tout. Ici je stocke tout pour l'historique.
                        
                        cursor.execute('''
                            INSERT INTO sentiments (date, team, sentiment_score, source_text)
                            VALUES (?, ?, ?, ?)
                        ''', (today, team, score, title))
                        
                        total_news += 1
            except Exception as e:
                print(f"⚠️ Erreur pour {team}: {e}")

        conn.commit()
        conn.close()
        print(f"🧠 Analyse terminée. {total_news} articles analysés et stockés.")

# --- Bloc de test ---
if __name__ == "__main__":
    collector = SentimentCollector()
    # Test unitaire rapide du sentiment
    test_phrase = "Victoire incroyable du PSG malgré la blessure de la star"
    print(f"Test phrase: '{test_phrase}' -> Score: {collector.analyze_sentiment(test_phrase)}")
    
    # Lancement réel
    collector.fetch_news()