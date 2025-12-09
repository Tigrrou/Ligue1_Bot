import pandas as pd
import joblib
import xgboost as xgb
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score
from sklearn.preprocessing import LabelEncoder
from src.database import BettingDB
from src.models.feature_engineering import FeatureEngineer

class PredictorV3:
    def __init__(self):
        self.db = BettingDB()
        self.fe = FeatureEngineer()
        self.model = None
        self.encoder = LabelEncoder()
        self.model_path = "data/model_v3_xgb.json"
        self.encoder_path = "data/encoder.pkl"

    def load_and_prepare_data(self):
        conn = self.db.get_connection()
        query = "SELECT * FROM matches WHERE status = 'FINISHED' ORDER BY date ASC"
        df = pd.read_sql_query(query, conn)
        conn.close()

        # Feature Engineering (Stats de forme)
        df = self.fe.enrich_matches(df)
        
        all_teams = pd.concat([df['home_team'], df['away_team']]).unique()
        self.encoder.fit(all_teams)
        joblib.dump(self.encoder, self.encoder_path)

        df['home_team_id'] = df['home_team'].apply(lambda x: self.encoder.transform([x])[0])
        df['away_team_id'] = df['away_team'].apply(lambda x: self.encoder.transform([x])[0])

        features = [
            'home_team_id', 'away_team_id', 
            'home_odds', 'draw_odds', 'away_odds',
            'home_form', 'home_att', 'home_def', 
            'away_form', 'away_att', 'away_def'
        ]
        
        X = df[features]
        
        y_list = []
        for _, row in df.iterrows():
            if row['home_score'] > row['away_score']: y_list.append(0)
            elif row['home_score'] == row['away_score']: y_list.append(1)
            else: y_list.append(2)
        y = pd.Series(y_list)

        return X, y

    def train(self):
        print("🚀 Entraînement V3 (Version CHAMPION : Manuelle)...")
        X, y = self.load_and_prepare_data()

        split = int(len(X) * 0.8)
        X_train, X_test = X.iloc[:split], X.iloc[split:]
        y_train, y_test = y.iloc[:split], y.iloc[split:]

        # PARAMÈTRES GAGNANTS (+1023€)
        self.model = xgb.XGBClassifier(
            n_estimators=200,      
            learning_rate=0.05,    
            max_depth=5,           
            objective='multi:softprob',
            num_class=3,
            eval_metric='mlogloss',
            random_state=42
        )

        self.model.fit(X_train, y_train)

        preds = self.model.predict(X_test)
        acc = accuracy_score(y_test, preds)
        print(f"✅ Précision XGBoost : {acc:.2%}")

        self.model.save_model(self.model_path)
        print("💾 Modèle V3 Champion sauvegardé.")

    def predict_match(self, home, away, odds_h, odds_d, odds_a):
        if self.model is None:
            self.model = xgb.XGBClassifier()
            try:
                self.model.load_model(self.model_path)
                self.encoder = joblib.load(self.encoder_path)
            except:
                print("❌ Modèle non trouvé. Lance .train()")
                return "N (Erreur)", 0.0

        try:
            h_id = self.encoder.transform([home])[0]
            a_id = self.encoder.transform([away])[0]
        except:
            print(f"⚠️ Équipe inconnue : {home} ou {away}")
            return "N (Inconnu)", 0.0

        # Récupération des stats réelles
        h_form, h_att, h_def = self.fe.get_team_latest_stats(home)
        a_form, a_att, a_def = self.fe.get_team_latest_stats(away)

        input_data = pd.DataFrame([[
            h_id, a_id, odds_h, odds_d, odds_a, 
            h_form, h_att, h_def, 
            a_form, a_att, a_def
        ]], columns=[
            'home_team_id', 'away_team_id', 'home_odds', 'draw_odds', 'away_odds',
            'home_form', 'home_att', 'home_def', 'away_form', 'away_att', 'away_def'
        ])

        pred_idx = self.model.predict(input_data)[0]
        probs = self.model.predict_proba(input_data)[0]
        
        mapping = {0: '1 (Dom)', 1: 'N (Nul)', 2: '2 (Ext)'}
        return mapping[pred_idx], probs[pred_idx]