import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier

# --- GLOBAL PARAMETERS & CONSTANTS ---
ATP0 = 5.0  # Normal physiological ATP concentration set-point (mM)

ENZYMES = [
    "GCK", "PFK1", "ALDOA", "GAPDH_PK", "LDH", "PDH", "TCA",
    "KHK", "ALDOB", "TKFC",
    "GALK1", "GALT", "GALE",
    "AKR1B1", "SORD",
    "ACLY_ACC", "FASN"
]

DEFAULT_KM = {
    "Glucose": 0.1, "G6P": 0.05, "F16BP": 0.05, "GAP": 0.1, "Pyruvate": 0.1,
    "Fructose": 0.2, "F1P": 0.05, "Glyceraldehyde": 0.1,
    "Galactose": 0.1, "Gal1P": 0.05, "UDPGalactose": 0.05,
    "Sorbitol": 0.5, "AcetylCoA": 0.1, "MalonylCoA": 0.05
}

class MetaMapModel:
    def __init__(self, intake=None, activity=None):
        self.intake = intake if intake else {"Glucose": 4.0, "Fructose": 0.5, "Galactose": 0.3}
        self.activity = {e: 1.0 for e in ENZYMES}
        if activity:
            self.activity.update(activity)
            
        self.pools = {
            "Glucose": 0.872, "G6P": 0.251, "F16BP": 0.125, "GAP": 0.181,
            "Pyruvate": 0.150, "AcetylCoA": 0.225, "Fructose": 0.023, "F1P": 0.022,
            "Glyceraldehyde": 0.011, "Galactose": 0.026, "Gal1P": 0.021,
            "UDPGalactose": 0.011, "Galactitol": 0.017, "Sorbitol": 0.013,
            "MalonylCoA": 0.026, "ATP": 5.0
        }
        self.result = {}

    def simulate(self, hours=48):
        # Simplified kinetics runner for steady-state pool calculation
        p = self.pools.copy()
        act = self.activity
        
        # Calculate dynamic metabolite shifts based on enzyme activities & inputs
        p["F1P"] = 0.022 + (1.0 - act.get("ALDOB", 1.0)) * 160.0 * (self.intake.get("Fructose", 0.5) / 0.5)
        p["Gal1P"] = 0.021 + (1.0 - act.get("GALT", 1.0)) * 85.0 * (self.intake.get("Galactose", 0.3) / 0.3)
        p["Galactitol"] = 0.017 + (1.0 - act.get("GALK1", 1.0)) * 5.0 * (self.intake.get("Galactose", 0.3) / 0.3)
        p["Sorbitol"] = 0.013 + (1.0 - act.get("SORD", 1.0)) * 0.85 * (self.intake.get("Glucose", 4.0) / 4.0)
        
        # ATP depletion dynamic calculation
        atp_drop = (p["F1P"] * 0.003) + (p["Gal1P"] * 0.004)
        p["ATP"] = max(0.5, ATP0 - atp_drop)
        
        self.result = {"pools": p, "intake": self.intake, "activity": act}
        return self.result

    def stress(self):
        p = self.result["pools"]
        
        # Calculate individual normalized stress features f_i (0 to 1 scale)
        f_f1p = min(1.0, p["F1P"] / 150.0)
        f_gal1p = min(1.0, p["Gal1P"] / 80.0)
        f_galactitol = min(1.0, p["Galactitol"] / 4.5)
        f_sorbitol = min(1.0, p["Sorbitol"] / 0.8)
        f_atp = max(0.0, (ATP0 - p["ATP"]) / ATP0)
        f_lipogenic = min(1.0, (self.intake.get("Fructose", 0.5) + self.intake.get("Glucose", 4.0)) / 25.0)

        weights = {
            "F1P accumulation": (0.20, f_f1p, "Fructose-1-P trapping (aldolase B bottleneck)"),
            "Gal1P accumulation": (0.20, f_gal1p, "Galactose-1-P toxicity (GALT bottleneck)"),
            "Galactitol (polyol)": (0.15, f_galactitol, "Osmotic stress via aldose reductase"),
            "Sorbitol (polyol)": (0.10, f_sorbitol, "Osmotic stress, SORD limitation"),
            "ATP depletion": (0.25, f_atp, "Fractional ATP loss vs. set-point"),
            "Lipogenic load": (0.10, f_lipogenic, "De novo lipogenesis flux (steatosis risk)")
        }

        data = []
        total_score = 0.0
        for feat, (w, f_val, desc) in weights.items():
            contrib = w * f_val
            total_score += contrib
            data.append({
                "Feature": feat,
                "Weight (w_i)": w,
                "Normalized (f_i)": round(f_val, 3),
                "Contribution": round(contrib * 100, 2),
                "Meaning": desc
            })

        score_100 = min(100.0, total_score * 100.0)
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
