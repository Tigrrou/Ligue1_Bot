import sqlite3
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from src.database import BettingDB

class Visualizer:
    def __init__(self):
        self.db = BettingDB()
        # Configuration du style des graphiques
        sns.set_theme(style="darkgrid")

    def generate_report(self):
        """Génère les stats et le graphique de performance."""
        conn = self.db.get_connection()
        
        # --- CORRECTION ICI ---
        # On fait une jointure (JOIN) pour récupérer les noms des équipes
        # depuis la table 'matches' en utilisant 'match_id'
        query = '''
            SELECT b.bet_date, m.home_team, m.away_team, b.prediction, b.result, b.profit, b.stake
            FROM bets b
            JOIN matches m ON b.match_id = m.id
            WHERE b.result IN ('WIN', 'LOSE')
            ORDER BY b.id ASC
        '''
        
        try:
            df = pd.read_sql_query(query, conn)
        except Exception as e:
            print(f"❌ Erreur SQL : {e}")
            conn.close()
            return

        conn.close()

        if df.empty:
            print("⚠️ Pas encore de paris terminés pour générer un rapport.")
            return

        # --- 1. Calcul des KPIs ---
        total_bets = len(df)
        total_wins = len(df[df['result'] == 'WIN'])
        win_rate = (total_wins / total_bets) * 100
        
        total_profit = df['profit'].sum()
        total_stake = df['stake'].sum()
        roi = (total_profit / total_stake) * 100

        print("\n" + "="*40)
        print(f"📊 RAPPORT DE PERFORMANCE")
        print("="*40)
        print(f"Nombre de paris : {total_bets}")
        print(f"Taux de réussite : {win_rate:.2f}%")
        print(f"Profit Net       : {total_profit:+.2f} €")
        print(f"ROI (Yield)      : {roi:+.2f}%")
        print("="*40)

        # --- 2. Génération du Graphique (Courbe de gains) ---
        
        # On calcule le cumul des profits ligne par ligne
        df['cumulative_profit'] = df['profit'].cumsum()
        
        # Création de la figure
        plt.figure(figsize=(10, 6))
        
        # La courbe principale
        sns.lineplot(data=df, x=df.index, y='cumulative_profit', marker='o', color='#00ff00')
        
        # Ligne zéro (Breakeven) en rouge pointillé
        plt.axhline(0, color='red', linestyle='--', alpha=0.5)
        
        plt.title('Évolution de la Bankroll (Profits Cumulés)', fontsize=16)
        plt.xlabel('Nombre de Paris', fontsize=12)
        plt.ylabel('Profit Net (€)', fontsize=12)
        
        # Remplissage sous la courbe (Vert si positif, Rouge si négatif)
        plt.fill_between(df.index, df['cumulative_profit'], alpha=0.1, color='green')

        # Sauvegarde
        filename = "performance_report.png"
        plt.savefig(filename)
        print(f"\n📈 Graphique sauvegardé sous : {filename}")

# --- Bloc de test ---
if __name__ == "__main__":
    viz = Visualizer()
    viz.generate_report()