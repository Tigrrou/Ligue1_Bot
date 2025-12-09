import pandas as pd
import datetime
from src.database import BettingDB

class StatsCollector:
    def __init__(self):
        self.db = BettingDB()
        self.urls = self._generate_urls()

    def _generate_urls(self):
        """Génère dynamiquement les URLs de 2021 jusqu'à la saison actuelle."""
        base_url = "https://www.football-data.co.uk/mmz4281/{}/F1.csv"
        urls = []
        
        current_date = datetime.datetime.now()
        # Si on est après juillet (mois 8), la nouvelle saison a commencé (ex: 2025 -> saison 2526)
        # Sinon on est dans la fin de la saison commencée l'année d'avant
        start_year_season = current_date.year if current_date.month >= 7 else current_date.year - 1
        
        # On commence en 2021 (comme dans ton code original)
        for year in range(2021, start_year_season + 1):
            season_str = f"{str(year)[-2:]}{str(year+1)[-2:]}" # Ex: 2021 -> "2122"
            urls.append(base_url.format(season_str))
            
        return urls

    def fetch_data(self):
        all_dfs = []
        for url in self.urls:
            print(f"📥 Téléchargement : {url.split('/')[-2]}...")
            try:
                df = pd.read_csv(url)
                df['Season_Source'] = url.split('/')[-2] 
                all_dfs.append(df)
            except Exception as e:
                print(f"⚠️ Pas encore disponible ou erreur : {url}")
        
        if all_dfs:
            final_df = pd.concat(all_dfs, ignore_index=True)
            print(f"✅ {len(final_df)} matchs récupérés.")
            return final_df
        return None

    def clean_and_save(self, df):
        if df is None: return

        conn = self.db.get_connection()
        cursor = conn.cursor()
        ph = self.db.get_placeholder() # Récupère "?" ou "%s"
        
        count = 0
        for index, row in df.iterrows():
            if pd.isna(row['HomeTeam']) or pd.isna(row['Date']): continue

            date_str = row['Date']
            try:
                if len(date_str) == 8: 
                     match_date = datetime.datetime.strptime(date_str, "%d/%m/%y").strftime("%Y-%m-%d")
                else: 
                     match_date = datetime.datetime.strptime(date_str, "%d/%m/%Y").strftime("%Y-%m-%d")
            except ValueError: continue

            home, away = row['HomeTeam'], row['AwayTeam']
            match_id = f"{match_date}_{home}_{away}".replace(" ", "")
            
            # Gestion des scores et cotes (inchangée)
            h_score = int(row['FTHG']) if not pd.isna(row['FTHG']) else None
            a_score = int(row['FTAG']) if not pd.isna(row['FTAG']) else None
            h_odds = row.get('B365H', row.get('BWH', 0.0))
            d_odds = row.get('B365D', row.get('BWD', 0.0))
            a_odds = row.get('B365A', row.get('BWA', 0.0))
            status = "FINISHED" if h_score is not None else "SCHEDULED"

            values = (match_id, match_date, home, away, h_odds, d_odds, a_odds, h_score, a_score, status)

            # --- LOGIQUE SQL HYBRIDE ---
            if self.db.is_postgres:
                # Syntaxe PostgreSQL (ON CONFLICT)
                query = f'''
                    INSERT INTO matches (id, date, home_team, away_team, home_odds, draw_odds, away_odds, home_score, away_score, status)
                    VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph})
                    ON CONFLICT (id) DO UPDATE SET 
                        home_score = EXCLUDED.home_score,
                        away_score = EXCLUDED.away_score,
                        status = EXCLUDED.status;
                '''
            else:
                # Syntaxe SQLite (INSERT OR REPLACE)
                query = f'''
                    INSERT OR REPLACE INTO matches 
                    (id, date, home_team, away_team, home_odds, draw_odds, away_odds, home_score, away_score, status)
                    VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph})
                '''
            
            cursor.execute(query, values)
            count += 1

        conn.commit()
        conn.close()
        print(f"💾 {count} matchs mis à jour en base.")

if __name__ == "__main__":
    c = StatsCollector()
    df = c.fetch_data()
    c.clean_and_save(df)