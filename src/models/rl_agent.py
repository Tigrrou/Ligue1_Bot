import json
import os
import numpy as np

class RLAgent:
    def __init__(self, alpha=0.1, gamma=0.9, epsilon=0.1):
        self.q_table_path = "data/q_table.json"
        self.alpha = alpha      # Taux d'apprentissage (vitesse d'oubli)
        self.gamma = gamma      # Importance du futur (peu utile ici car "one-step")
        self.epsilon = epsilon  # Taux d'exploration (parfois on tente un pari risqué pour voir)
        self.q_table = self.load_q_table()

    def load_q_table(self):
        """Charge la Q-Table ou l'initialise."""
        if os.path.exists(self.q_table_path):
            with open(self.q_table_path, 'r') as f:
                return json.load(f)
        else:
            # On initialise vide. Les clés seront les états (ex: "0.6").
            return {}

    def save_q_table(self):
        with open(self.q_table_path, 'w') as f:
            json.dump(self.q_table, f, indent=4)

    def get_state(self, confidence):
        """Discrétise la confiance pour réduire le nombre d'états."""
        # On arrondit à la décimale (ex: 0.53 -> "0.5", 0.89 -> "0.9")
        return str(round(confidence, 1))

    def get_q_values(self, state):
        """Récupère les valeurs pour un état (Action 0: Skip, Action 1: Bet)."""
        if state not in self.q_table:
            # [Q(Skip), Q(Bet)] initialisés à 0
            self.q_table[state] = [0.0, 0.0]
        return self.q_table[state]

    def decide_action(self, confidence):
        """Décide si on parie (1) ou non (0)."""
        state = self.get_state(confidence)
        
        # Exploration (Epsilon-Greedy) : Parfois on agit au hasard pour découvrir
        if np.random.uniform(0, 1) < self.epsilon:
            return np.random.choice([0, 1]) # 0 = Skip, 1 = Bet

        # Exploitation : On prend la meilleure action connue
        q_values = self.get_q_values(state)
        # Si Q(Bet) > Q(Skip), on parie.
        if q_values[1] >= q_values[0]:
            return 1
        else:
            return 0

    def learn(self, confidence, action, reward):
        """Met à jour la Q-Table en fonction du résultat."""
        state = self.get_state(confidence)
        q_values = self.get_q_values(state)
        
        current_q = q_values[action]
        
        # Formule du Q-Learning :
        # Nouveau Q = Ancien Q + Alpha * (Récompense - Ancien Q)
        # Note : On simplifie ici car il n'y a pas d'état "futur" dans un pari simple (one-step)
        new_q = current_q + self.alpha * (reward - current_q)
        
        self.q_table[state][action] = new_q
        self.save_q_table()
        
        print(f"🤖 [RL Learn] État {state} | Action {action} | Reward {reward} -> Q-Val mise à jour : {new_q:.2f}")

# --- Bloc de test ---
if __name__ == "__main__":
    agent = RLAgent()
    # Simulation : L'agent apprend qu'une confiance de 0.9 rapporte gros
    print("Avant apprentissage (0.9) :", agent.get_q_values("0.9"))
    agent.learn(0.9, 1, 50.0) # Il parie (1) avec conf 0.9 et gagne 50€
    print("Après apprentissage (0.9) :", agent.get_q_values("0.9"))