import numpy as np
import pandas as pd
from sklearn.neural_network import MLPRegressor
from sklearn.preprocessing import StandardScaler

# --- GLOBAL PARAMETERS & CONSTANTS ---
ATP0 = 5.0  # Normal physiological ATP concentration set-point (mM)

ENZYMES = [
    "GCK", "PFK1", "ALDOA", "GAPDH_PK", "LDH", "PDH", "TCA",
    "KHK", "ALDOB", "TKFC",
    "GALK1", "GALT", "GALE",
    "AKR1B1", "SORD",
    "ACLY_ACC", "FASN"
]

class MetaMapModel:
    def __init__(self, intake=None, activity=None):
        self.intake = intake if intake else {"Glucose": 4.0, "Fructose": 0.5, "Galactose": 0.3}
        self.activity = {e: 1.0 for e in ENZYMES}
        if activity:
            self.activity.update(activity)
            
        # Initialize and train the Neural Network surrogate model
        self._train_neural_network_surrogate()
        
    def _train_neural_network_surrogate(self):
        """Trains a multi-layer perceptron (MLP) mapping enzyme nodes and nutrient inflow to systemic stress."""
        np.random.seed(42)
        n_samples = 600
        
        X_train = []
        y_train = []
        
        for _ in range(n_samples):
            g_in = np.random.uniform(0.5, 20.0)
            f_in = np.random.uniform(0.0, 10.0)
            gal_in = np.random.uniform(0.0, 5.0)
            
            acts = [np.random.uniform(0.0, 1.5) for _ in ENZYMES]
            
            aldob_act = acts[7]
            galt_act = acts[10]
            sord_act = acts[13]
            
            f1p = 0.022 + (1.0 - aldob_act) * 160.0 * (f_in / 0.5)
            gal1p = 0.021 + (1.0 - galt_act) * 85.0 * (gal_in / 0.3)
            galactitol = 0.017 + (1.0 - acts[10]) * 5.0 * (gal_in / 0.3)
            sorbitol = 0.013 + (1.0 - sord_act) * 0.85 * (g_in / 4.0)
            atp = max(0.5, ATP0 - (f1p * 0.003 + gal1p * 0.004))
            
            # Ground-truth biochemical target score
            score = min(100.0, (
                (f1p / 150.0) * 20 +
                (gal1p / 80.0) * 20 +
                (galactitol / 4.5) * 15 +
                (sorbitol / 0.8) * 10 +
                ((ATP0 - atp) / ATP0) * 25 +
                ((f_in + g_in) / 25.0) * 10
            ) * 100.0)
            
            X_train.append([g_in, f_in, gal_in] + acts)
            y_train.append(score)
            
        self.scaler = StandardScaler()
        X_scaled = self.scaler.fit_transform(X_train)
        
        # Neural Network: Multi-Layer Perceptron with 2 hidden layers (32 and 16 nodes)
        self.nn_model = MLPRegressor(
            hidden_layer_sizes=(32, 16),
            activation='relu',
            solver='adam',
            max_iter=600,
            random_state=42
        )
        self.nn_model.fit(X_scaled, y_train)

    def simulate(self, hours=48):
        g_in = self.intake.get("Glucose", 4.0)
        f_in = self.intake.get("Fructose", 0.5)
        gal_in = self.intake.get("Galactose", 0.3)
        
        p = {
            "Glucose": 0.872 * (g_in / 4.0),
            "G6P": 0.251,
            "F16BP": 0.125,
            "GAP": 0.181,
            "Pyruvate": 0.150,
            "AcetylCoA": 0.225,
            "Fructose": f_in * 0.046,
            "F1P": 0.022 + (1.0 - self.activity.get("ALDOB", 1.0)) * 160.0 * (f_in / 0.5),
            "Glyceraldehyde": 0.011,
            "Galactose": gal_in * 0.086,
            "Gal1P": 0.021 + (1.0 - self.activity.get("GALT", 1.0)) * 85.0 * (gal_in / 0.3),
            "UDPGalactose": 0.011,
            "Galactitol": 0.017 + (1.0 - self.activity.get("GALK1", 1.0)) * 5.0 * (gal_in / 0.3),
            "Sorbitol": 0.013 + (1.0 - self.activity.get("SORD", 1.0)) * 0.85 * (g_in / 4.0),
            "MalonylCoA": 0.026,
            "ATP": max(0.5, ATP0 - ((0.022 + (1.0 - self.activity.get("ALDOB", 1.0)) * 160.0 * (f_in / 0.5)) * 0.003))
        }
        
        self.result = {"pools": p, "intake": self.intake, "activity": self.activity}
        return self.result

    def stress(self):
        # Predict cellular stress score using the trained Neural Network
        g_in = self.intake.get("Glucose", 4.0)
        f_in = self.intake.get("Fructose", 0.5)
        gal_in = self.intake.get("Galactose", 0.3)
        acts_list = [self.activity[e] for e in ENZYMES]
        
        input_vector = np.array([[g_in, f_in, gal_in] + acts_list])
        input_scaled = self.scaler.transform(input_vector)
        predicted_score = float(self.nn_model.predict(input_scaled)[0])
        score_100 = np.clip(predicted_score, 0.0, 100.0)
        
        p = self.result["pools"]
        f_f1p = min(1.0, p["F1P"] / 150.0)
        f_gal1p = min(1.0, p["Gal1P"] / 80.0)
        f_galactitol = min(1.0, p["Galactitol"] / 4.5)
        f_sorbitol = min(1.0, p["Sorbitol"] / 0.8)
        f_atp = max(0.0, (ATP0 - p["ATP"]) / ATP0)
        f_lipogenic = min(1.0, (f_in + g_in) / 25.0)

        weights = {
            "F1P accumulation": (0.20, f_f1p, "Fructose-1-P trapping (aldolase B bottleneck)"),
            "Gal1P accumulation": (0.20, f_gal1p, "Galactose-1-P toxicity (GALT bottleneck)"),
            "Galactitol (polyol)": (0.15, f_galactitol, "Osmotic stress via aldose reductase"),
            "Sorbitol (polyol)": (0.10, f_sorbitol, "Osmotic stress, SORD limitation"),
            "ATP depletion": (0.25, f_atp, "Fractional ATP loss vs. set-point"),
            "Lipogenic load": (0.10, f_lipogenic, "De novo lipogenesis flux (steatosis risk)")
        }

        data = []
        for feat, (w, f_val, desc) in weights.items():
            contrib = w * f_val * 100.0
            data.append({
                "Feature": feat,
                "Weight (w_i)": w,
                "Normalized (f_i)": round(f_val, 3),
                "Contribution": round(contrib, 2),
                "Meaning": desc
            })

        return score_100, pd.DataFrame(data)

    def pathway_table(self):
        p = self.result["pools"]
        act = self.activity

        reactions = [
            ("R01_GCK", "Glycolysis", "GCK", act["GCK"], "Glucose", p["Glucose"], "OK"),
            ("R02_PFK1", "Glycolysis", "PFK1", act["PFK1"], "G6P", p["G6P"], "OK"),
            ("R03_ALDOA", "Glycolysis", "ALDOA", act["ALDOA"], "F16BP", p["F16BP"], "OK"),
            ("R04_LOWER", "Glycolysis", "GAPDH_PK", act["GAPDH_PK"], "GAP", p["GAP"], "OK"),
            ("R05_LDH", "Glycolysis", "LDH", act["LDH"], "Pyruvate", p["Pyruvate"], "OK"),
            ("R06_PDH", "TCA entry", "PDH", act["PDH"], "Pyruvate", p["Pyruvate"], "OK"),
            ("R07_TCA", "TCA entry", "TCA", act["TCA"], "AcetylCoA", p["AcetylCoA"], "OK"),
            ("R08_KHK", "Fructolysis", "KHK", act["KHK"], "Fructose", p["Fructose"], "OK"),
            ("R09_ALDOB", "Fructolysis", "ALDOB", act["ALDOB"], "F1P", p["F1P"], 
             "BOTTLENECK (deficient)" if act["ALDOB"] < 0.2 else "OK"),
            ("R10_TKFC", "Fructolysis", "TKFC", act["TKFC"], "Glyceraldehyde", p["Glyceraldehyde"], "OK"),
            ("R11_GALK1", "Leloir", "GALK1", act["GALK1"], "Galactose", p["Galactose"], 
             "BOTTLENECK (deficient)" if act["GALK1"] < 0.2 else "OK"),
            ("R12_GALT", "Leloir", "GALT", act["GALT"], "Gal1P", p["Gal1P"], 
             "BOTTLENECK (deficient)" if act["GALT"] < 0.2 else "OK"),
            ("R13_GALE", "Leloir", "GALE", act["GALE"], "UDPGalactose", p["UDPGalactose"], "OK"),
            ("R14_AR_GLC", "Polyol", "AKR1B1", act["AKR1B1"], "Glucose", p["Glucose"], "OK"),
            ("R15_AR_GAL", "Polyol", "AKR1B1", act["AKR1B1"], "Galactose", p["Galactose"], "OK"),
            ("R16_SORD", "Polyol", "SORD", act["SORD"], "Sorbitol", p["Sorbitol"], 
             "BOTTLENECK (deficient)" if act["SORD"] < 0.2 else "OK"),
            ("R17_ACLY_ACC", "Lipogenesis", "ACLY_ACC", act["ACLY_ACC"], "AcetylCoA", p["AcetylCoA"], "OK"),
            ("R18_FASN", "Lipogenesis", "FASN", act["FASN"], "MalonylCoA", p["MalonylCoA"], "OK")
        ]

        df = pd.DataFrame(reactions, columns=["Reaction", "Pathway", "Enzyme", "Activity", "Substrate", "Pool_mM", "Status"])
        return df
