import pandas as pd
import sqlite3
import joblib
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report
from sklearn.preprocessing import LabelEncoder
from src.database import BettingDB

class PredictorV1:
    def __init__(self):
        self.db = BettingDB()
        self.model = None
        self.encoder = LabelEncoder()
        self.model_path = "data/model_v1.pkl"
        self.encoder_path = "data/encoder.pkl"

    def load_data(self):
        """Charge les données d'entraînement depuis la BDD."""
        conn = self.db.get_connection()
        # On ne charge que les matchs terminés pour l'entraînement
        query = '''
            SELECT home_team, away_team, home_odds, draw_odds, away_odds, home_score, away_score 
            FROM matches 
            WHERE status = 'FINISHED'
        '''
        df = pd.read_sql_query(query, conn)
        conn.close()
        return df

    def prepare_features(self, df, training=True):
        """Transforme les données brutes en Features utilisables par le modèle."""
        
        # 1. Feature Engineering : On encode les noms des équipes en nombres
        # Note : Dans une V2, on utilisera des stats plus fines (forme, buts, etc.)
        # Pour la V1, les cotes (Odds) contiennent déjà implicitement l'info de forme.
        
        # Concaténer toutes les équipes pour fitter l'encodeur
        all_teams = pd.concat([df['home_team'], df['away_team']]).unique()
        
        if training:
            self.encoder.fit(all_teams)
            joblib.dump(self.encoder, self.encoder_path)
        else:
            # En mode prédiction, on charge l'encodeur existant
            try:
                self.encoder = joblib.load(self.encoder_path)
            except:
                self.encoder.fit(all_teams) # Fallback

        # Transformation des noms en ID numériques
        # On utilise .map pour éviter les erreurs si une équipe est inconnue (on met -1)
        # (Astuce robuste pour la prod)
        df['home_team_id'] = df['home_team'].apply(lambda x: self.encoder.transform([x])[0] if x in self.encoder.classes_ else -1)
        df['away_team_id'] = df['away_team'].apply(lambda x: self.encoder.transform([x])[0] if x in self.encoder.classes_ else -1)

        # Sélection des Features (X)
        features = ['home_team_id', 'away_team_id', 'home_odds', 'draw_odds', 'away_odds']
        
        # Ajout fictif du Sentiment (sera 0 pour l'historique, mais prêt pour le futur)
        # Dans la V2, on fera une jointure SQL réelle ici.
        df['sentiment_home'] = 0.0 
        df['sentiment_away'] = 0.0
        features.extend(['sentiment_home', 'sentiment_away'])

        X = df[features]

        if training:
            # Définition de la Target (Y) : 0 = Home, 1 = Draw, 2 = Away
            # Logique : Si Home > Away -> 0, Si Draw -> 1, Si Away > Home -> 2
            conditions = [
                (df['home_score'] > df['away_score']),
                (df['home_score'] == df['away_score']),
                (df['home_score'] < df['away_score'])
            ]
            choices = [0, 1, 2]
            df['result'] = pd.Series(pd.NA) # Init
            
            # Utilisation de numpy select ou boucle simple. Ici boucle simple pour lisibilité.
            y_list = []
            for idx, row in df.iterrows():
                if row['home_score'] > row['away_score']: y_list.append(0)
                elif row['home_score'] == row['away_score']: y_list.append(1)
                else: y_list.append(2)
            
            y = pd.Series(y_list)
            return X, y
        
        return X

    def train(self):
        """Entraîne le modèle et affiche les performances."""
        print("🧠 Chargement des données et entraînement du modèle...")
        df = self.load_data()
        
        if df.empty:
            print("❌ Pas assez de données pour entraîner le modèle. Lance le stats_collector d'abord !")
            return

        X, y = self.prepare_features(df, training=True)
        
        # Split Train/Test (80% pour apprendre, 20% pour vérifier)
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

        # Initialisation du Random Forest
        self.model = RandomForestClassifier(n_estimators=100, random_state=42)
        self.model.fit(X_train, y_train)

        # Évaluation
        predictions = self.model.predict(X_test)
        accuracy = accuracy_score(y_test, predictions)
        
        print(f"✅ Modèle entraîné ! Précision sur le test set : {accuracy:.2%}")
        print("Rapport détaillé :")
        print(classification_report(y_test, predictions, target_names=['Home', 'Draw', 'Away']))

        # Sauvegarde
        joblib.dump(self.model, self.model_path)
        print(f"💾 Modèle sauvegardé dans {self.model_path}")

    def predict_match(self, home_team, away_team, home_odds, draw_odds, away_odds):
        """Fait une prédiction pour un match spécifique."""
        if self.model is None:
            try:
                self.model = joblib.load(self.model_path)
            except:
                print("❌ Modèle non trouvé. Lance .train() d'abord.")
                return None

        # Création d'un DataFrame d'une seule ligne
        data = {
            'home_team': [home_team], 'away_team': [away_team],
            'home_odds': [home_odds], 'draw_odds': [draw_odds], 'away_odds': [away_odds],
            'home_score': [None], 'away_score': [None] # Dummy
        }
        df_single = pd.DataFrame(data)
        
        X = self.prepare_features(df_single, training=False)
        
        # Prédiction (0, 1, 2)
        prediction = self.model.predict(X)[0]
        # Probabilités (ex: [0.60, 0.30, 0.10])
        probs = self.model.predict_proba(X)[0]
        
        mapping = {0: '1 (Domicile)', 1: 'N (Nul)', 2: '2 (Extérieur)'}
        
        return mapping[prediction], probs[prediction]

# --- Bloc de test ---
if __name__ == "__main__":
    bot = PredictorV1()
    
    # 1. Entraînement
    bot.train()
    
    # 2. Test de prédiction fictive
    print("\n🔮 Test de prédiction : PSG vs Marseille (Cotes fictives)")
    pred, conf = bot.predict_match("PSG", "Marseille", 1.5, 4.0, 6.0)
    print(f"Résultat prédit : {pred} avec {conf:.2%} de confiance.")