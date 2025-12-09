import pandas as pd
from src.database import BettingDB

class FeatureEngineer:
    def __init__(self):
        self.db = BettingDB()

    def calculate_rolling_stats(self, df, window=5):
        # ... (Le code de cette méthode ne change pas car pas de SQL direct) ...
        # Copie-colle ton code existant pour calculate_rolling_stats ici
        home_df = df[['date', 'home_team', 'home_score', 'away_score', 'result']].copy()
        home_df.columns = ['date', 'team', 'score_for', 'score_ag', 'res']
        home_df['points'] = home_df['res'].apply(lambda x: 3 if x == 'H' else (1 if x == 'D' else 0))
        home_df['at_home'] = 1
        away_df = df[['date', 'away_team', 'away_score', 'home_score', 'result']].copy()
        away_df.columns = ['date', 'team', 'score_for', 'score_ag', 'res']
        away_df['points'] = away_df['res'].apply(lambda x: 3 if x == 'A' else (1 if x == 'D' else 0))
        away_df['at_home'] = 0
        stats_df = pd.concat([home_df, away_df]).sort_values(['team', 'date'])
        
        # Amélioration EMA (Moyenne Exponentielle) intégrée
        stats_df['form_last_5'] = stats_df.groupby('team')['points'].transform(lambda x: x.ewm(span=window).mean())
        stats_df['goals_for_last_5'] = stats_df.groupby('team')['score_for'].transform(lambda x: x.ewm(span=window).mean())
        stats_df['goals_ag_last_5'] = stats_df.groupby('team')['score_ag'].transform(lambda x: x.ewm(span=window).mean())
        stats_df = stats_df.fillna(0)
        return stats_df

    def enrich_matches(self, matches_df):
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
        conn = self.db.get_connection()
        ph = self.db.get_placeholder()
        
        # Requête dynamique
        query = f'''
            SELECT date, home_team, away_team, home_score, away_score 
            FROM matches 
            WHERE (home_team = {ph} OR away_team = {ph}) 
            AND status = 'FINISHED'
            ORDER BY date DESC 
            LIMIT {ph}
        '''
        # Note: pandas read_sql_query gère les params comme execute
        df = pd.read_sql_query(query, conn, params=(team_name, team_name, 20))
        conn.close()

        if len(df) < window:
            return 1.3, 1.2, 1.2

        df = df.sort_values('date', ascending=True)
        points, goals_for, goals_ag = [], [], []

        for _, row in df.iterrows():
            if row['home_team'] == team_name:
                h, a = row['home_score'], row['away_score']
                goals_for.append(h); goals_ag.append(a)
                points.append(3 if h > a else (1 if h == a else 0))
            else:
                h, a = row['home_score'], row['away_score']
                goals_for.append(a); goals_ag.append(h)
                points.append(3 if a > h else (1 if a == h else 0))

        # Moyenne simple ici car on travaille sur une liste extraite
        avg_form = sum(points[-window:]) / window
        avg_att = sum(goals_for[-window:]) / window
        avg_def = sum(goals_ag[-window:]) / window

        return avg_form, avg_att, avg_def