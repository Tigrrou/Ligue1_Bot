import pandas as pd
import sqlite3
import datetime
from src.database import BettingDB

class StatsCollector:
    def __init__(self):
        self.db = BettingDB()
        # Liste des URLs des saisons passées (Ligue 1)
        # 2425 = Saison actuelle
        # 2324 = Saison passée, etc.
        self.urls = [
            "https://www.football-data.co.uk/mmz4281/2021/F1.csv",
            "https://www.football-data.co.uk/mmz4281/2122/F1.csv",
            "https://www.football-data.co.uk/mmz4281/2223/F1.csv",
            "https://www.football-data.co.uk/mmz4281/2324/F1.csv",
            "https://www.football-data.co.uk/mmz4281/2425/F1.csv"
        ]

    def fetch_data(self):
        """Récupère et combine les données de toutes les saisons."""
        all_dfs = []
        for url in self.urls:
            print(f"📥 Téléchargement de {url}...")
            try:
                df = pd.read_csv(url)
                # On ajoute une colonne saison pour s'y retrouver si besoin
                df['Season_Source'] = url.split('/')[-2] 
                all_dfs.append(df)
            except Exception as e:
                print(f"❌ Erreur sur {url} : {e}")
        
        if all_dfs:
            final_df = pd.concat(all_dfs, ignore_index=True)
            print(f"✅ Total récupéré : {len(final_df)} matchs.")
            return final_df
        return None

    def clean_and_save(self, df):
        """Nettoie les données et les sauvegarde en BDD"""
        if df is None: return

        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        count = 0
        for index, row in df.iterrows():
            if pd.isna(row['HomeTeam']) or pd.isna(row['Date']): continue

            # Gestion des formats de date multiples selon les années (ex: 21/08/2020 vs 21/08/20)
            date_str = row['Date']
            try:
                if len(date_str) == 8: # Format JJ/MM/YY
                     match_date = datetime.datetime.strptime(date_str, "%d/%m/%y").strftime("%Y-%m-%d")
                else: # Format JJ/MM/YYYY
                     match_date = datetime.datetime.strptime(date_str, "%d/%m/%Y").strftime("%Y-%m-%d")
            except ValueError:
                continue # On saute si format bizarre

            home_team = row['HomeTeam']
            away_team = row['AwayTeam']
            match_id = f"{match_date}_{home_team}_{away_team}".replace(" ", "")

            home_score = int(row['FTHG']) if not pd.isna(row['FTHG']) else None
            away_score = int(row['FTAG']) if not pd.isna(row['FTAG']) else None
            
            # Cotes (Parfois B365, parfois Bet&Win BW, on priorise B365)
            home_odds = row.get('B365H', row.get('BWH', 0.0))
            draw_odds = row.get('B365D', row.get('BWD', 0.0))
            away_odds = row.get('B365A', row.get('BWA', 0.0))

            status = "FINISHED" if home_score is not None else "SCHEDULED"

            cursor.execute('''
                INSERT OR REPLACE INTO matches 
                (id, date, home_team, away_team, home_odds, draw_odds, away_odds, home_score, away_score, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (match_id, match_date, home_team, away_team, home_odds, draw_odds, away_odds, home_score, away_score, status))
            
            count += 1

        conn.commit()
        conn.close()
        print(f"💾 {count} matchs historiques sauvegardés.")

if __name__ == "__main__":
    collector = StatsCollector()
    df = collector.fetch_data()
    collector.clean_and_save(df)