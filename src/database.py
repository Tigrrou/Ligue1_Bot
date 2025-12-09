import sqlite3
import os
from datetime import datetime

class BettingDB:
    def __init__(self, db_name="betting.db"):
        # On s'assure que le dossier 'data' existe
        self.db_folder = "data"
        if not os.path.exists(self.db_folder):
            os.makedirs(self.db_folder)
            print(f"📁 Dossier '{self.db_folder}' créé.")

        self.db_path = os.path.join(self.db_folder, db_name)

    def get_connection(self):
        """Crée et retourne une connexion à la base de données."""
        return sqlite3.connect(self.db_path)

    def initialize_tables(self):
        """Crée les tables si elles n'existent pas déjà."""
        conn = self.get_connection()
        cursor = conn.cursor()

        # 1. Table MATCHS : Stocke les données brutes des matchs (passés et à venir)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS matches (
                id TEXT PRIMARY KEY,           -- ID unique (ex: "2023-10-22_PSG_OM")
                date TEXT,                     -- Date du match ISO
                home_team TEXT,
                away_team TEXT,
                home_odds REAL,                -- Cote Victoire Domicile (1)
                draw_odds REAL,                -- Cote Match Nul (N)
                away_odds REAL,                -- Cote Victoire Extérieur (2)
                home_score INTEGER,            -- Score Domicile (NULL si pas encore joué)
                away_score INTEGER,            -- Score Extérieur (NULL si pas encore joué)
                status TEXT DEFAULT 'SCHEDULED' -- 'SCHEDULED', 'FINISHED'
            )
        ''')

        # 2. Table SENTIMENTS : Stocke l'analyse "Molle" (NLP)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sentiments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT,
                team TEXT,
                sentiment_score REAL,          -- Score entre -1 (Négatif) et 1 (Positif)
                source_text TEXT               -- Titre de l'article ou snippet analysé
            )
        ''')

        # 3. Table PREDICTIONS & PARIS (Paper Trading) : L'historique des actions du bot
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS bets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                match_id TEXT,
                prediction TEXT,               -- '1', 'N', ou '2'
                confidence REAL,               -- Confiance du modèle (proba)
                stake REAL,                    -- Mise (fictive)
                odds_taken REAL,               -- Cote au moment du pari
                result TEXT,                   -- 'WIN', 'LOSE', 'PENDING'
                profit REAL,                   -- Gain ou Perte nette
                bet_date TEXT,
                model_version TEXT,            -- Pour comparer V1 vs V2
                FOREIGN KEY(match_id) REFERENCES matches(id)
            )
        ''')

        conn.commit()
        conn.close()
        print(f"✅ Base de données initialisée avec succès dans : {self.db_path}")

# --- Bloc de test rapide ---
if __name__ == "__main__":
    db = BettingDB()
    db.initialize_tables()