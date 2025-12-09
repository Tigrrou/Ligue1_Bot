import sqlite3
import os
import psycopg2
from urllib.parse import urlparse
from dotenv import load_dotenv  # <--- AJOUTER CECI

load_dotenv()

class BettingDB:
    def __init__(self):
        self.db_url = os.getenv("DATABASE_URL") # Récupère l'URL secrète (si elle existe)
        self.is_postgres = bool(self.db_url)
        
        if not self.is_postgres:
            # Mode Local (SQLite)
            self.db_folder = "data"
            if not os.path.exists(self.db_folder):
                os.makedirs(self.db_folder)
            self.db_path = os.path.join(self.db_folder, "betting.db")
            print(f"📂 Mode LOCAL : Utilisation de SQLite ({self.db_path})")
        else:
            print("☁️ Mode CLOUD : Utilisation de PostgreSQL")

    def get_connection(self):
        """Crée et retourne une connexion (SQLite ou Postgres)."""
        if self.is_postgres:
            return psycopg2.connect(self.db_url)
        else:
            return sqlite3.connect(self.db_path)

    def get_placeholder(self):
        """Retourne %s pour Postgres et ? pour SQLite."""
        return "%s" if self.is_postgres else "?"

    def initialize_tables(self):
        """Crée les tables en s'adaptant à la base de données."""
        conn = self.get_connection()
        cursor = conn.cursor()

        # Syntaxe adaptée pour l'auto-incrément
        if self.is_postgres:
            auto_inc = "SERIAL PRIMARY KEY"
        else:
            auto_inc = "INTEGER PRIMARY KEY AUTOINCREMENT"

        # 1. Table MATCHS
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS matches (
                id TEXT PRIMARY KEY,
                date TEXT,
                home_team TEXT,
                away_team TEXT,
                home_odds REAL,
                draw_odds REAL,
                away_odds REAL,
                home_score INTEGER,
                away_score INTEGER,
                status TEXT DEFAULT 'SCHEDULED'
            )
        ''')

        # 2. Table SENTIMENTS
        cursor.execute(f'''
            CREATE TABLE IF NOT EXISTS sentiments (
                id {auto_inc},
                date TEXT,
                team TEXT,
                sentiment_score REAL,
                source_text TEXT
            )
        ''')

        # 3. Table PARIS (Bets)
        cursor.execute(f'''
            CREATE TABLE IF NOT EXISTS bets (
                id {auto_inc},
                match_id TEXT,
                prediction TEXT,
                confidence REAL,
                stake REAL,
                odds_taken REAL,
                result TEXT,
                profit REAL,
                bet_date TEXT,
                model_version TEXT,
                FOREIGN KEY(match_id) REFERENCES matches(id)
            )
        ''')

        conn.commit()
        conn.close()
        print("✅ Tables initialisées (ou déjà existantes).")

if __name__ == "__main__":
    db = BettingDB()
    db.initialize_tables()