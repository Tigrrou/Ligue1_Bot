import pandas as pd
import numpy as np
import sqlite3
from src.database import BettingDB

class FeatureEngineer:
    def __init__(self):
        self.db = BettingDB()

    def calculate_rolling_stats(self, df, window=5):
        """
        Calcule la forme des équipes sur les 'window' derniers matchs.
        window=5 signifie qu'on regarde les 5 derniers matchs.
        """
        # On sépare les matchs en deux lignes par match : une pour l'équipe domicile, une pour l'extérieur
        # Cela permet de calculer la forme d'une équipe qu'elle joue chez elle ou ailleurs.
        
        home_df = df[['date', 'home_team', 'home_score', 'away_score', 'result']].copy()
        home_df.columns = ['date', 'team', 'score_for', 'score_ag', 'res']
        home_df['points'] = home_df['res'].apply(lambda x: 3 if x == 'H' else (1 if x == 'D' else 0))
        home_df['at_home'] = 1

        away_df = df[['date', 'away_team', 'away_score', 'home_score', 'result']].copy()
        away_df.columns = ['date', 'team', 'score_for', 'score_ag', 'res']
        away_df['points'] = away_df['res'].apply(lambda x: 3 if x == 'A' else (1 if x == 'D' else 0))
        away_df['at_home'] = 0

        stats_df = pd.concat([home_df, away_df]).sort_values(['team', 'date'])

        stats_df['form_last_5'] = stats_df.groupby('team')['points'].transform(lambda x: x.rolling(window, closed='left').mean())
        stats_df['goals_for_last_5'] = stats_df.groupby('team')['score_for'].transform(lambda x: x.rolling(window, closed='left').mean())
        stats_df['goals_ag_last_5'] = stats_df.groupby('team')['score_ag'].transform(lambda x: x.rolling(window, closed='left').mean())
        stats_df = stats_df.fillna(0)
        return stats_df

    def enrich_matches(self, matches_df):
        """Ajoute les stats calculées au DataFrame principal des matchs."""
        
        # D'abord, on détermine le résultat (H, D, A) pour aider le calcul ci-dessus
        matches_df['result'] = 'D'
        matches_df.loc[matches_df['home_score'] > matches_df['away_score'], 'result'] = 'H'
        matches_df.loc[matches_df['away_score'] > matches_df['home_score'], 'result'] = 'A'

        stats = self.calculate_rolling_stats(matches_df)

        matches_df = pd.merge(matches_df, stats[['date', 'team', 'form_last_5', 'goals_for_last_5', 'goals_ag_last_5']], 
                              left_on=['date', 'home_team'], right_on=['date', 'team'], how='left')
        matches_df.rename(columns={'form_last_5': 'home_form', 'goals_for_last_5': 'home_att', 'goals_ag_last_5': 'home_def'}, inplace=True)
        matches_df.drop(columns=['team'], inplace=True)

        matches_df = pd.merge(matches_df, stats[['date', 'team', 'form_last_5', 'goals_for_last_5', 'goals_ag_last_5']], 
                              left_on=['date', 'away_team'], right_on=['date', 'team'], how='left')
        matches_df.rename(columns={'form_last_5': 'away_form', 'goals_for_last_5': 'away_att', 'goals_ag_last_5': 'away_def'}, inplace=True)
        matches_df.drop(columns=['team'], inplace=True)
        matches_df.fillna(0, inplace=True)
        return matches_df
    
    def get_team_latest_stats(self, team_name, window=5):
        """Récupère les stats de forme actuelles d'une équipe depuis la BDD."""
        conn = self.db.get_connection()
        
        # On cherche les derniers matchs joués par l'équipe
        query = '''
            SELECT date, home_team, away_team, home_score, away_score 
            FROM matches 
            WHERE (home_team = ? OR away_team = ?) 
            AND status = 'FINISHED'
            ORDER BY date DESC 
            LIMIT ?
        '''
        # On en prend 20 pour être sûr d'avoir assez d'historique pour la moyenne
        df = pd.read_sql_query(query, conn, params=(team_name, team_name, 20))
        conn.close()

        if len(df) < window:
            # Pas assez de matchs (début de saison ou équipe promue) -> Valeurs neutres
            return 1.3, 1.2, 1.2 # Forme, Attaque, Défense moyens

        # On remet dans l'ordre chronologique pour le calcul
        df = df.sort_values('date', ascending=True)
        
        points = []
        goals_for = []
        goals_ag = []

        for _, row in df.iterrows():
            if row['home_team'] == team_name:
                h_score, a_score = row['home_score'], row['away_score']
                goals_for.append(h_score)
                goals_ag.append(a_score)
                if h_score > a_score: points.append(3)
                elif h_score == a_score: points.append(1)
                else: points.append(0)
            else: # L'équipe jouait à l'extérieur
                h_score, a_score = row['home_score'], row['away_score']
                goals_for.append(a_score)
                goals_ag.append(h_score)
                if a_score > h_score: points.append(3)
                elif a_score == h_score: points.append(1)
                else: points.append(0)

        # On prend les 5 derniers de la liste calculée
        avg_form = sum(points[-window:]) / window
        avg_att = sum(goals_for[-window:]) / window
        avg_def = sum(goals_ag[-window:]) / window

        return avg_form, avg_att, avg_def