import optuna
import xgboost as xgb
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.metrics import log_loss
from src.models.predictor_v3 import PredictorV3

def objective(trial):
    # 1. Chargement des données (Une seule fois idéalement, mais ici on recharge pour être safe)
    # Dans une version prod, on sortirait ça de la fonction pour la vitesse.
    bot = PredictorV3()
    X, y = bot.load_and_prepare_data()
    
    # Split Train/Val (80/20)
    # On utilise un random_state fixe pour que la comparaison soit juste
    X_train, X_val, y_train, y_val = train_test_split(X, y, test_size=0.2, random_state=42)

    # 2. L'espace de recherche (C'est ici qu'Optuna teste des valeurs)
    param = {
        'verbosity': 0,
        'objective': 'multi:softprob',
        'num_class': 3,
        'eval_metric': 'mlogloss',
        'n_jobs': -1,
        
        # Paramètres à optimiser :
        'n_estimators': trial.suggest_int('n_estimators', 100, 1000),
        'max_depth': trial.suggest_int('max_depth', 3, 10),
        'learning_rate': trial.suggest_float('learning_rate', 0.01, 0.3),
        'subsample': trial.suggest_float('subsample', 0.6, 1.0),
        'colsample_bytree': trial.suggest_float('colsample_bytree', 0.6, 1.0),
        'gamma': trial.suggest_float('gamma', 0, 5),
        'min_child_weight': trial.suggest_int('min_child_weight', 1, 10),
    }

    # 3. Entraînement avec ces paramètres
    model = xgb.XGBClassifier(**param)
    model.fit(X_train, y_train)

    # 4. Évaluation (On veut minimiser le Log Loss pour avoir des probas précises)
    preds = model.predict_proba(X_val)
    loss = log_loss(y_val, preds)
    
    return loss

if __name__ == "__main__":
    print("🏎️ Démarrage de l'optimisation des hyperparamètres...")
    
    # On crée l'étude (On veut MINIMISER l'erreur LogLoss)
    study = optuna.create_study(direction='minimize')
    
    # On lance 50 essais (Tu peux mettre 100 si tu as le temps)
    study.optimize(objective, n_trials=50)

    print("\n" + "="*40)
    print("🏆 RÉSULTATS OPTIMISÉS")
    print("="*40)
    print(f"Meilleure erreur (LogLoss) : {study.best_value:.4f}")
    print("Meilleurs paramètres trouvés :")
    for key, value in study.best_params.items():
        print(f"   '{key}': {value},")
    print("="*40)
    print("👉 Copie ces paramètres dans ton fichier src/models/predictor_v3.py !")