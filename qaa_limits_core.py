"""Limites analíticos e capacidade de decisão — rotinas independentes da UI.

Os métodos de LoB/LoD e CCα/CCβ são aproximações didáticas
explicitamente identificadas, não substituem protocolos completos.
"""
from __future__ import annotations

from math import isfinite
import numpy as np
import pandas as pd
from scipy import stats


def _data_numeric(values, name: str, min_n: int = 3):
    """Remove células vazias; rejeita valores não numéricos informados."""
    raw = pd.Series(values)
    text = raw.astype("string").str.strip().str.replace(",", ".", regex=False)
    blank = text.isna() | text.eq("")
    nums = pd.to_numeric(text[~blank], errors="coerce")
    if nums.isna().any() or not np.isfinite(nums.to_numpy(float)).all():
        raise ValueError(f"{name}: há respostas preenchidas que não são números válidos.")
    x = nums.to_numpy(float)
    if len(x) < min_n:
        raise ValueError(f"{name}: informe pelo menos {min_n} medições válidas.")
    return x


def lob_lod(blank, low, alpha: float = .05, beta: float = .05,
            finite_sample: bool = True):
    """LoB/LoD paramétricos no domínio de concentração aparente.

    LoB = média_branco + cα * s_branco
    LoD = LoB + cβ * s_amostra_baixa

    Quando finite_sample, usa correção cp = z/(1-1/[4(n-1)])
    para cada conjunto individual (aproximação inspirada no EP17-A2).
    """
    if not (0 < alpha < .5 and 0 < beta < .5):
        raise ValueError("α e β devem estar entre 0 e 0,5.")
    b = _data_numeric(blank, "Branco", min_n=3)
    l = _data_numeric(low, "Amostra de baixa concentração", min_n=3)
    mb = float(np.mean(b))
    ml = float(np.mean(l))
    sb = float(np.std(b, ddof=1))
    sl = float(np.std(l, ddof=1))
    za, zb = float(stats.norm.ppf(1-alpha)), float(stats.norm.ppf(1-beta))

    ca = za / (1 - 1 / (4 * (len(b)-1))) if finite_sample else za
    cb = zb / (1 - 1 / (4 * (len(l)-1))) if finite_sample else zb
    lob = mb + ca*sb
    lod = lob + cb*sl
    detectable = int(np.sum(l > lob))
    return {
        "n_blank": len(b), "n_low": len(l),
        "mean_blank": mb, "sd_blank": sb, "mean_low": ml, "sd_low": sl,
        "alpha": alpha, "beta": beta, "c_blank": ca, "c_low": cb,
        "lob": lob, "lod": lod,
        "n_low_above_lob": detectable,
        "observed_detection_rate": detectable / len(l),
        "small_sample_correction": bool(finite_sample),
        "low_concentration_measured": (ml >= lod),
        "note": ("Estimativa simplificada de uma única série por tipo; "
                 "planejamentos completos devem avaliar diferentes brancos, lotes e dias.")
    }


def ich_limits(slope: float, sigma_response: float):
    """Estimativas ICH Q2(R2): DL = 3.3σ/S, QL = 10σ/S."""
    if not isfinite(float(slope)) or float(slope) == 0:
        raise ValueError("A inclinação deve ser um número finito diferente de zero.")
    if not isfinite(float(sigma_response)) or float(sigma_response) <= 0:
        raise ValueError("σ da resposta deve ser um valor finito positivo.")
    s = abs(float(slope))
    sig = float(sigma_response)
    return {"slope": float(slope), "sigma_response": sig,
            "lod": 3.3*sig/s, "loq": 10*sig/s, "method": "ICH Q2(R2) — σ/S"}


def experimental_loq(table: pd.DataFrame, cv_max: float = 20.,
                     bias_max: float = 15., min_reps: int = 3):
    """Menor nível ensaiado que atende simultaneamente aos critérios de CV e viés.

    Cada observação é uma determinação independente da amostra com valor nominal
    conhecido, na unidade de concentração. Não interpola entre níveis testados.
    """
    needed = ["nominal", "encontrado"]
    if not all(c in table.columns for c in needed):
        raise ValueError("A tabela deve conter colunas nominal e encontrado.")
    if not (isfinite(float(cv_max)) and cv_max >= 0 and
            isfinite(float(bias_max)) and bias_max >= 0):
        raise ValueError("Critérios de CV e viés devem ser não negativos e finitos.")
    if min_reps < 2:
        raise ValueError("A exigência de réplicas deve ser de pelo menos duas.")

    df = table[needed].copy()
    for name in needed:
        raw = df[name].astype("string").str.strip().str.replace(",", ".", regex=False)
        has_value = raw.notna() & raw.ne("")
        converted = pd.to_numeric(raw, errors="coerce")
        if converted.isna().any() and has_value[converted.isna()].any():
            raise ValueError(f"Coluna {name}: foram informados valores não numéricos.")
        df[name] = converted
    df = df.replace([np.inf,-np.inf],np.nan).dropna()
    if len(df) == 0:
        raise ValueError("Preencha os dados experimentais de pelo menos um nível.")
    if (df["nominal"] <= 0).any():
        raise ValueError("A concentração nominal deve ser maior que zero.")

    summary = []
    for nominal, group in df.groupby("nominal",sort=True):
        yy = group["encontrado"].to_numpy(float)
        n = len(yy)
        mean = float(yy.mean())
        sd = float(np.std(yy,ddof=1)) if n>=2 else float("nan")
        cv = 100*sd/abs(mean) if n>=2 and mean != 0 else float("nan")
        bias = 100*(mean-nominal)/nominal
        enough = n>=min_reps
        passed = bool(enough and np.isfinite(cv) and cv<=cv_max and abs(bias)<=bias_max)
        summary.append({
            "nominal": float(nominal), "n": int(n),
            "media": mean, "desvio": sd, "cv_percent": cv,
            "vies_percent": bias, "n_suficiente": bool(enough),
            "cumpre_cv": bool(np.isfinite(cv) and cv<=cv_max),
            "cumpre_vies": bool(abs(bias)<=bias_max), "aprovado": passed
        })
    result = pd.DataFrame(summary)
    passing = result.loc[result["aprovado"],"nominal"]
    candidate = float(passing.min()) if len(passing)>0 else None
    higher_failures = (result["nominal"] > candidate) & ~result["aprovado"] if candidate is not None else pd.Series(False,index=result.index)
    return {
        "summary": result, "individual": df,
        "loq_candidate": candidate,
        "cv_max": float(cv_max), "bias_max":float(bias_max),
        "min_reps": int(min_reps),
        "inconsistent_higher_levels": bool(higher_failures.any()),
        "warning": ("LoQ candidato apenas entre os níveis efetivamente ensaiados; "
                    "é necessário confirmar a aptidão para uso e a faixa de trabalho.")
    }


def gaussian_decision_limit(permitted_limit: float, sd_at_limit: float,
                            alpha: float = .05, beta: float = .05,
                            measured_value=None):
    """Demonstração gaussiana unilateral de limite de decisão para resultados ACIMA de L.

    Para Y|C ~ N(C, s²) com s constante perto do limite:
        CCα = L + z_(1-α) s
        CCβ = CCα + z_(1-β) s
    CCβ representa o teor verdadeiro detectado como 'acima do limite'
    com probabilidade 1-β. Não implementa os protocolos legais específicos.
    """
    L, sigma = float(permitted_limit), float(sd_at_limit)
    if not (np.isfinite(L) and L>=0):
        raise ValueError("O limite permitido deve ser não negativo e finito.")
    if not (np.isfinite(sigma) and sigma>0):
        raise ValueError("O desvio-padrão perto do limite deve ser positivo e finito.")
    if not (0<alpha<.5 and 0<beta<.5):
        raise ValueError("α e β devem estar entre 0 e 0,5.")
    z_a,z_b = float(stats.norm.ppf(1-alpha)),float(stats.norm.ppf(1-beta))
    cc_a = L + z_a*sigma
    cc_b = cc_a + z_b*sigma
    out = {
        "limite":L,"sigma":sigma,"alpha":alpha,"beta":beta,
        "z_alpha":z_a,"z_beta":z_b,"cc_alpha":cc_a,"cc_beta":cc_b,
        "false_positive_at_limit":float(stats.norm.sf((cc_a-L)/sigma)),
        "probability_detection_at_cc_beta":float(stats.norm.sf((cc_a-cc_b)/sigma)),
        "model": "Gaussiano unilateral, variância constante — demonstrativo"
    }
    if measured_value is not None:
        y=float(measured_value)
        if not np.isfinite(y):
            raise ValueError("O resultado medido deve ser finito.")
        out["measured_value"] = y
        out["noncompliant"] = bool(y>cc_a)
        out["difference_to_threshold"] = y-cc_a
    return out
