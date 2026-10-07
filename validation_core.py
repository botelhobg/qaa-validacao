from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional, Tuple
import math
import numpy as np
import pandas as pd
from scipy import stats


@dataclass
class OLSResult:
    n: int
    intercept: float
    slope: float
    r2: float
    sse: float
    mse: float
    s_res: float
    df_res: int
    xbar: float
    sxx: float
    syy: float
    yhat: np.ndarray
    residuals: np.ndarray
    leverage: np.ndarray
    studentized_internal: np.ndarray
    jackknife: np.ndarray
    jackknife_critical: float
    se_intercept: float
    se_slope: float
    t_intercept: float
    t_slope: float
    p_intercept: float
    p_slope: float


@dataclass
class TestResult:
    statistic: Optional[float]
    p_value: Optional[float]
    conclusion: str
    details: Dict[str, Any]


def _clean_xy(x, y):
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    mask = np.isfinite(x) & np.isfinite(y)
    return x[mask], y[mask], mask


def ols_fit(x, y, alpha_outlier: float = 0.05) -> OLSResult:
    x, y, _ = _clean_xy(x, y)
    n = len(x)
    if n < 4:
        raise ValueError("São necessárias pelo menos 4 observações para a regressão e diagnóstico de resíduos.")
    if np.ptp(x) == 0:
        raise ValueError("A concentração deve assumir pelo menos dois valores diferentes.")

    X = np.column_stack([np.ones(n), x])
    xtx_inv = np.linalg.inv(X.T @ X)
    beta = xtx_inv @ X.T @ y
    yhat = X @ beta
    e = y - yhat
    sse = float(np.sum(e**2))
    df_res = n - 2
    mse = sse / df_res
    s_res = math.sqrt(max(mse, 0.0))
    h = np.diag(X @ xtx_inv @ X.T)

    if mse <= 0:
        r_int = np.zeros(n)
        jack = np.zeros(n)
    else:
        denom = np.sqrt(mse * np.maximum(1.0 - h, np.finfo(float).eps))
        r_int = e / denom
        den = np.maximum(n - 2 - r_int**2, np.finfo(float).eps)
        jack = r_int * np.sqrt((n - 3) / den)

    jcrit = float(stats.t.ppf(1 - alpha_outlier / 2, n - 3))
    xbar = float(np.mean(x))
    sxx = float(np.sum((x - xbar) ** 2))
    syy = float(np.sum((y - np.mean(y)) ** 2))
    r2 = 1.0 - sse / syy if syy > 0 else float("nan")

    cov_beta = mse * xtx_inv
    se_a = math.sqrt(max(cov_beta[0, 0], 0.0))
    se_b = math.sqrt(max(cov_beta[1, 1], 0.0))
    t_a = beta[0] / se_a if se_a > 0 else float("inf")
    t_b = beta[1] / se_b if se_b > 0 else float("inf")
    p_a = float(2 * stats.t.sf(abs(t_a), df_res)) if np.isfinite(t_a) else 0.0
    p_b = float(2 * stats.t.sf(abs(t_b), df_res)) if np.isfinite(t_b) else 0.0

    return OLSResult(
        n=n, intercept=float(beta[0]), slope=float(beta[1]), r2=float(r2),
        sse=sse, mse=float(mse), s_res=float(s_res), df_res=df_res,
        xbar=xbar, sxx=sxx, syy=syy, yhat=yhat, residuals=e, leverage=h,
        studentized_internal=r_int, jackknife=jack, jackknife_critical=jcrit,
        se_intercept=se_a, se_slope=se_b, t_intercept=float(t_a),
        t_slope=float(t_b), p_intercept=p_a, p_slope=p_b,
    )


def iterative_jackknife(
    df: pd.DataFrame,
    x_col: str = "concentracao",
    y_col: str = "resposta",
    alpha: float = 0.05,
    max_delete_fraction: float = 2 / 9,
    enable: bool = True,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    work = df[[x_col, y_col]].copy().dropna()
    work[x_col] = pd.to_numeric(work[x_col], errors="coerce")
    work[y_col] = pd.to_numeric(work[y_col], errors="coerce")
    work = work.dropna().copy()
    work["_orig_index"] = work.index.astype(str)
    work = work.reset_index(drop=True)

    if not enable:
        return work, pd.DataFrame(columns=["etapa", "indice_original", "concentracao", "resposta", "J", "Jcrit"])

    n0 = len(work)
    max_delete = max(0, int(math.floor(n0 * max_delete_fraction + 1e-12)))
    if abs(max_delete_fraction - 2 / 9) < 1e-9:
        max_delete = int(math.floor(2 * n0 / 9 + 1e-12))

    deleted: List[Dict[str, Any]] = []
    for step in range(max_delete):
        if len(work) < 5 or work[x_col].nunique() < 3:
            break
        fit = ols_fit(work[x_col].to_numpy(), work[y_col].to_numpy(), alpha_outlier=alpha)
        idx = int(np.argmax(np.abs(fit.jackknife)))
        j = float(fit.jackknife[idx])
        if abs(j) <= fit.jackknife_critical:
            break
        row = work.iloc[idx]
        deleted.append({
            "etapa": step + 1,
            "indice_original": row["_orig_index"],
            "concentracao": float(row[x_col]),
            "resposta": float(row[y_col]),
            "J": j,
            "Jcrit": float(fit.jackknife_critical),
        })
        work = work.drop(index=idx).reset_index(drop=True)

    return work, pd.DataFrame(deleted)


def ryan_joiner(residuals: np.ndarray) -> TestResult:
    e = np.asarray(residuals, dtype=float)
    e = e[np.isfinite(e)]
    n = len(e)
    if n < 4:
        return TestResult(None, None, "Não disponível", {"motivo": "n < 4"})
    es = np.sort(e)
    i = np.arange(1, n + 1)
    p = (i - 0.375) / (n + 0.25)
    q = stats.norm.ppf(p)
    R = float(np.corrcoef(es, q)[0, 1])

    def critical(alpha):
        if alpha == 0.10:
            return 1.0071 - 0.1371 / math.sqrt(n) - 0.3682 / n + 0.7780 / (n**2)
        if alpha == 0.05:
            return 1.0063 - 0.1288 / math.sqrt(n) - 0.6118 / n + 1.3505 / (n**2)
        if alpha == 0.01:
            return 0.9963 - 0.0211 / math.sqrt(n) - 1.4106 / n + 3.1791 / (n**2)
        raise ValueError(alpha)

    c10, c05, c01 = critical(0.10), critical(0.05), critical(0.01)
    if R >= c10:
        pval = 0.1000001
        plabel = "p > 0,10"
    elif R >= c05:
        pval = float(np.interp(R, [c05, c10], [0.05, 0.10]))
        plabel = f"p ≈ {pval:.3f}"
    elif R >= c01:
        pval = float(np.interp(R, [c01, c05], [0.01, 0.05]))
        plabel = f"p ≈ {pval:.3f}"
    else:
        pval = 0.0099999
        plabel = "p < 0,01"

    conclusion = "Resíduos compatíveis com normalidade" if R >= c05 else "Há evidência de desvio da normalidade"
    return TestResult(R, pval, conclusion, {
        "Rcrit_0.10": c10, "Rcrit_0.05": c05, "Rcrit_0.01": c01,
        "p_label": plabel, "normal_scores": q, "ordered_residuals": es,
    })


def brown_forsythe_two_groups(x: np.ndarray, residuals: np.ndarray, alpha: float = 0.05) -> TestResult:
    x = np.asarray(x, dtype=float)
    e = np.asarray(residuals, dtype=float)
    levels = np.unique(x)
    if len(levels) < 4:
        return TestResult(None, None, "Não disponível", {"motivo": "menos de 4 níveis"})
    groups = np.array_split(levels, 2)
    g1 = e[np.isin(x, groups[0])]
    g2 = e[np.isin(x, groups[1])]
    if len(g1) < 2 or len(g2) < 2:
        return TestResult(None, None, "Não disponível", {"motivo": "grupos insuficientes"})

    z1 = np.abs(g1 - np.median(g1))
    z2 = np.abs(g2 - np.median(g2))
    n1, n2 = len(z1), len(z2)
    v1, v2 = np.var(z1, ddof=1), np.var(z2, ddof=1)
    sp2 = ((n1 - 1) * v1 + (n2 - 1) * v2) / (n1 + n2 - 2)
    se = math.sqrt(max(sp2 * (1 / n1 + 1 / n2), np.finfo(float).eps))
    t = float((np.mean(z1) - np.mean(z2)) / se)
    df = n1 + n2 - 2
    p = float(2 * stats.t.sf(abs(t), df))
    conclusion = "Homoscedasticidade compatível" if p >= alpha else "Há evidência de heteroscedasticidade"
    return TestResult(t, p, conclusion, {
        "df": df, "n_grupo_1": n1, "n_grupo_2": n2,
        "mediana_1": float(np.median(g1)), "mediana_2": float(np.median(g2)),
        "media_d_1": float(np.mean(z1)), "media_d_2": float(np.mean(z2)),
        "s2_pooled": float(sp2), "niveis_grupo_1": groups[0].tolist(),
        "niveis_grupo_2": groups[1].tolist(),
    })


def durbin_watson_mc(x: np.ndarray, residuals: np.ndarray, alpha: float = 0.10, nsim: int = 8000, seed: int = 2026) -> TestResult:
    x = np.asarray(x, dtype=float)
    e = np.asarray(residuals, dtype=float)
    den = float(np.sum(e**2))
    if len(e) < 5 or den <= 0:
        return TestResult(None, None, "Não disponível", {"motivo": "dados insuficientes"})
    d_obs = float(np.sum(np.diff(e) ** 2) / den)

    n = len(x)
    X = np.column_stack([np.ones(n), x])
    H = X @ np.linalg.inv(X.T @ X) @ X.T
    M = np.eye(n) - H
    rng = np.random.default_rng(seed)
    chunk = 2000
    less = greater = total = 0
    while total < nsim:
        b = min(chunk, nsim - total)
        z = rng.normal(size=(b, n))
        er = z @ M
        denr = np.sum(er**2, axis=1)
        dr = np.sum(np.diff(er, axis=1) ** 2, axis=1) / denr
        less += int(np.sum(dr <= d_obs))
        greater += int(np.sum(dr >= d_obs))
        total += b
    p = min(1.0, 2 * min(less / total, greater / total))
    conclusion = "Independência compatível" if p >= alpha else "Há evidência de autocorrelação"
    return TestResult(d_obs, float(p), conclusion, {
        "alpha_recomendado": alpha, "nsim": nsim,
        "metodo_p": "Monte Carlo bicaudal condicionado ao desenho x",
    })


def regression_anova_and_lof(x: np.ndarray, y: np.ndarray, fit: OLSResult, alpha: float = 0.05) -> Dict[str, Any]:
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    levels = np.unique(x)
    u = len(levels)
    ss_reg = float(np.sum((fit.yhat - np.mean(y)) ** 2))
    ms_reg = ss_reg
    f_reg = ms_reg / fit.mse if fit.mse > 0 else float("inf")
    p_reg = float(stats.f.sf(f_reg, 1, fit.df_res)) if np.isfinite(f_reg) else 0.0

    ss_pe = 0.0
    df_pe = 0
    for lev in levels:
        vals = y[x == lev]
        if len(vals) >= 1:
            ss_pe += float(np.sum((vals - np.mean(vals)) ** 2))
            df_pe += len(vals) - 1
    ss_lof = float(fit.sse - ss_pe)
    df_lof = u - 2

    if df_pe > 0 and df_lof > 0:
        ms_pe = ss_pe / df_pe
        ms_lof = max(ss_lof, 0.0) / df_lof
        f_lof = ms_lof / ms_pe if ms_pe > 0 else float("inf")
        p_lof = float(stats.f.sf(f_lof, df_lof, df_pe)) if np.isfinite(f_lof) else 0.0
        lof_conclusion = "Não há evidência de falta de ajuste" if p_lof >= alpha else "Há evidência de falta de ajuste"
    else:
        ms_pe = ms_lof = f_lof = p_lof = None
        lof_conclusion = "Não disponível: são necessárias replicatas independentes nos níveis"

    return {
        "ss_reg": ss_reg, "df_reg": 1, "ms_reg": ms_reg,
        "f_reg": f_reg, "p_reg": p_reg,
        "regression_conclusion": "Regressão significativa" if p_reg < alpha else "Regressão não significativa",
        "ss_res": fit.sse, "df_res": fit.df_res, "ms_res": fit.mse,
        "ss_pe": ss_pe, "df_pe": df_pe, "ms_pe": ms_pe,
        "ss_lof": ss_lof, "df_lof": df_lof, "ms_lof": ms_lof,
        "f_lof": f_lof, "p_lof": p_lof, "lof_conclusion": lof_conclusion,
    }


def analyze_linearity(
    df: pd.DataFrame,
    x_col: str = "concentracao",
    y_col: str = "resposta",
    alpha: float = 0.05,
    alpha_dw: float = 0.10,
    remove_outliers: bool = True,
    max_delete_fraction: float = 2 / 9,
    dw_nsim: int = 8000,
) -> Dict[str, Any]:
    raw = df[[x_col, y_col]].copy()
    cleaned, deleted = iterative_jackknife(raw, x_col, y_col, alpha, max_delete_fraction, remove_outliers)
    x = cleaned[x_col].to_numpy(float)
    y = cleaned[y_col].to_numpy(float)
    fit = ols_fit(x, y, alpha_outlier=alpha)
    rj = ryan_joiner(fit.residuals)
    bf = brown_forsythe_two_groups(x, fit.residuals, alpha=alpha)
    dw = durbin_watson_mc(x, fit.residuals, alpha=alpha_dw, nsim=dw_nsim)
    anova = regression_anova_and_lof(x, y, fit, alpha=alpha)

    points = cleaned.copy()
    points["y_ajustado"] = fit.yhat
    points["residuo"] = fit.residuals
    points["leverage"] = fit.leverage
    points["residuo_studentizado"] = fit.studentized_internal
    points["jackknife"] = fit.jackknife

    premise_ok = (
        (rj.p_value is not None and rj.p_value >= alpha)
        and (bf.p_value is not None and bf.p_value >= alpha)
        and (dw.p_value is not None and dw.p_value >= alpha_dw)
    )
    linear_ok = premise_ok and (anova["p_reg"] < alpha) and (anova["p_lof"] is None or anova["p_lof"] >= alpha)

    return {
        "fit": fit, "deleted": deleted, "points": points,
        "ryan_joiner": rj, "brown_forsythe": bf, "durbin_watson": dw,
        "anova": anova, "premises_ok": premise_ok, "linear_ok": linear_ok,
        "n_original": len(raw.dropna()), "n_final": len(cleaned),
    }


def _parameter_variances(fit: OLSResult) -> Tuple[float, float]:
    var_b = fit.mse / fit.sxx
    var_a = fit.mse * (1 / fit.n + fit.xbar**2 / fit.sxx)
    return float(var_a), float(var_b)


def compare_matrix_effect(solvent: Dict[str, Any], matrix: Dict[str, Any], alpha: float = 0.05) -> Dict[str, Any]:
    f1: OLSResult = solvent["fit"]
    f2: OLSResult = matrix["fit"]

    s1, s2 = f1.mse, f2.mse
    if s1 >= s2:
        F = s1 / s2 if s2 > 0 else float("inf")
        df_num, df_den = f1.df_res, f2.df_res
    else:
        F = s2 / s1 if s1 > 0 else float("inf")
        df_num, df_den = f2.df_res, f1.df_res
    pF = min(1.0, float(2 * stats.f.sf(F, df_num, df_den))) if np.isfinite(F) else 0.0
    equal_var = pF >= alpha

    if equal_var:
        sp2 = ((f1.df_res * f1.mse) + (f2.df_res * f2.mse)) / (f1.df_res + f2.df_res)
        se_b = math.sqrt(sp2 * (1 / f1.sxx + 1 / f2.sxx))
        se_a = math.sqrt(sp2 * (1 / f1.n + 1 / f2.n + f1.xbar**2 / f1.sxx + f2.xbar**2 / f2.sxx))
        df_b = df_a = f1.df_res + f2.df_res
        method = "t com variâncias residuais combinadas"
    else:
        vb1 = f1.mse / f1.sxx
        vb2 = f2.mse / f2.sxx
        va1 = f1.mse * (1 / f1.n + f1.xbar**2 / f1.sxx)
        va2 = f2.mse * (1 / f2.n + f2.xbar**2 / f2.sxx)
        se_b = math.sqrt(vb1 + vb2)
        se_a = math.sqrt(va1 + va2)
        df_b = (vb1 + vb2) ** 2 / ((vb1**2 / f1.df_res) + (vb2**2 / f2.df_res))
        df_a = (va1 + va2) ** 2 / ((va1**2 / f1.df_res) + (va2**2 / f2.df_res))
        method = "t de Welch/Satterthwaite (variâncias residuais diferentes)"

    t_b = (f1.slope - f2.slope) / se_b if se_b > 0 else float("inf")
    t_a = (f1.intercept - f2.intercept) / se_a if se_a > 0 else float("inf")
    p_b = float(2 * stats.t.sf(abs(t_b), df_b)) if np.isfinite(t_b) else 0.0
    p_a = float(2 * stats.t.sf(abs(t_a), df_a)) if np.isfinite(t_a) else 0.0

    prop = p_b < alpha
    const = p_a < alpha
    if prop and const:
        classification = "Efeito de matriz proporcional e constante"
    elif prop:
        classification = "Efeito de matriz proporcional"
    elif const:
        classification = "Efeito de matriz constante"
    else:
        classification = "Sem evidência de efeito de matriz"

    matrix_effect_percent = 100 * (f2.slope / f1.slope - 1) if f1.slope != 0 else float("nan")

    return {
        "F": float(F), "df_F_num": int(df_num), "df_F_den": int(df_den),
        "p_F": pF, "equal_residual_variances": equal_var,
        "comparison_method": method, "t_slope": float(t_b), "df_slope": float(df_b),
        "p_slope": p_b, "t_intercept": float(t_a), "df_intercept": float(df_a),
        "p_intercept": p_a, "matrix_effect_percent_slope": float(matrix_effect_percent),
        "classification": classification,
        "calibration_in_solvent_recommended": not (prop or const),
    }


def result_to_serializable(result: Dict[str, Any]) -> Dict[str, Any]:
    def conv(v):
        if isinstance(v, OLSResult):
            d = asdict(v)
            return {k: conv(x) for k, x in d.items()}
        if isinstance(v, TestResult):
            return {"statistic": v.statistic, "p_value": v.p_value, "conclusion": v.conclusion, "details": conv(v.details)}
        if isinstance(v, pd.DataFrame):
            return v.to_dict(orient="records")
        if isinstance(v, np.ndarray):
            return v.tolist()
        if isinstance(v, (np.floating, np.integer)):
            return v.item()
        if isinstance(v, dict):
            return {k: conv(x) for k, x in v.items()}
        if isinstance(v, list):
            return [conv(x) for x in v]
        return v
    return conv(result)
