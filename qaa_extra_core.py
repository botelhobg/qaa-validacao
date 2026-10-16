"""Núcleo estatístico: precisão, viés em MRC e recuperação por fortificação."""
import numpy as np
import pandas as pd
from scipy import stats

def number(s):
    return pd.to_numeric(pd.Series(s).astype(str).str.replace(",",".",regex=False),errors="coerce")

def intermediate_precision(table,alpha=.05):
    if not {"dia","resultado"}.issubset(table.columns):
        raise ValueError("Informe dia e resultado.")
    x=table[["dia","resultado"]].copy()
    x["resultado"]=number(x["resultado"]).to_numpy()
    x=x.dropna()
    groups=[g["resultado"].to_numpy(float) for _,g in x.groupby("dia",sort=False)]
    k=len(groups); n=sum(len(g) for g in groups)
    if n<2 or not any(len(g)>=2 for g in groups):
        raise ValueError("São necessárias ao menos duas medições no mesmo dia.")
    means=np.array([np.mean(g) for g in groups])
    ns=np.array([len(g) for g in groups])
    all_values=np.concatenate(groups)
    mean=float(np.mean(all_values))
    ss_within=sum(float(np.sum((g-np.mean(g))**2)) for g in groups)
    dfw=n-k; msw=ss_within/dfw
    sr=float(np.sqrt(msw))
    result={"n":n,"dias":k,"media":mean,"sr":sr,"ms_dentro":msw,
            "gl_dentro":dfw,"n_por_dia":ns.tolist(),
            "rms_r_percent":100*sr/abs(mean) if mean else None}
    if k==1:
        result.update({"s_entre":None,"s_IP":None,"p_entre":None,
                       "mensagem":"Apenas repetibilidade; não há comparação entre dias."})
        return result
    ss_between=float(np.sum(ns*(means-mean)**2))
    ms_between=ss_between/(k-1)
    n0=(n-float(np.sum(ns**2))/n)/(k-1)
    day_variance=max((ms_between-msw)/n0,0.0)
    s_day=float(np.sqrt(day_variance))
    sip=float(np.sqrt(msw+day_variance))
    F=ms_between/msw if msw>0 else np.inf
    p=float(stats.f.sf(F,k-1,dfw)) if np.isfinite(F) else 0.0
    result.update({"ss_entre":ss_between,"ms_entre":ms_between,
                   "s_entre":s_day,"s_IP":sip,"n0":float(n0),"f":float(F),
                   "p_entre":p,"rms_IP_percent":100*sip/abs(mean) if mean else None,
                   "mensagem":"Evidência de diferença entre dias." if p<alpha else
                               "Sem evidência de diferença entre dias."})
    return result

def bias_mrc(values,assigned_value,u_ref=0.,alpha=.05):
    y=number(values).dropna().to_numpy(float)
    if len(y)<2:raise ValueError("Informe pelo menos duas determinações independentes.")
    if u_ref<0:raise ValueError("A incerteza padrão do MRC não pode ser negativa.")
    n=len(y);mean=float(np.mean(y));sd=float(np.std(y,ddof=1))
    bias=mean-assigned_value
    se=sd/np.sqrt(n)
    t=bias/se if se>0 else (0.0 if bias==0 else np.inf)
    p=float(2*stats.t.sf(abs(t),n-1)) if np.isfinite(t) else 0.
    tc=float(stats.t.ppf(1-alpha/2,n-1))
    U=float(np.sqrt((tc*se)**2+(2*u_ref)**2))
    return {"n":n,"media":mean,"desvio":sd,"valor_ref":assigned_value,
            "u_ref":u_ref,"bias":float(bias),
            "bias_percent":100*bias/assigned_value if assigned_value else None,
            "se_media":float(se),"t_exploratorio":float(t),"p_t_exploratorio":p,
            "ic_media":(float(mean-tc*se),float(mean+tc*se)),
            "U_diferenca_aprox":U,"compatibilidade_expandida":abs(bias)<=U}


def recovery(table, alpha=.05, lower=80., upper=120., mode="amostra_nativa"):
    """Avalia dois desenhos distintos de adição-recuperação.

    mode="matriz_branca": R = 100*C_encontrada/C_adicionada.
      Requer matriz sem analito nativo e concentração nominal conhecida.
    mode="amostra_nativa": R = 100*(C_fortificada-C_sem_fortificacao)/C_adicionada.
      Cada linha representa uma medição pareada ou uma estimativa basal apropriada.

    Retorna (leituras individuais com recuperação, resumo por nível).
    A recuperação não constitui, sozinha, prova geral da veracidade.
    """
    if mode == "matriz_branca":
        cols = ["adicionado", "encontrada"]
    elif mode == "amostra_nativa":
        cols = ["adicionado", "sem_fortificacao", "fortificada"]
    else:
        raise ValueError("Tipo de ensaio inválido. Escolha matriz_branca ou amostra_nativa.")

    if not set(cols).issubset(table.columns):
        raise ValueError("Colunas necessárias para este tipo de ensaio: " + ", ".join(cols))

    x = table[cols].copy()
    for col in cols:
        x[col] = number(x[col]).to_numpy()
    x = x.replace([np.inf, -np.inf], np.nan).dropna().reset_index(drop=True)

    if x.empty:
        raise ValueError("Informe pelo menos uma medição completa.")
    if (x["adicionado"] <= 0).any():
        raise ValueError("A concentração adicionada precisa ser positiva.")
    if not 0 <= lower <= upper:
        raise ValueError("O intervalo de aceitação deve ter limites ordenados e não negativos.")
    if not 0 < alpha < 1:
        raise ValueError("α deve estar entre 0 e 1.")

    if mode == "matriz_branca":
        x["recuperacao_percent"] = 100.0 * x["encontrada"] / x["adicionado"]
    else:
        x["recuperacao_percent"] = (
            100.0 * (x["fortificada"] - x["sem_fortificacao"]) / x["adicionado"]
        )

    results = []
    for level, g in x.groupby("adicionado", sort=True):
        values = g["recuperacao_percent"].to_numpy(float)
        n = len(values)
        avg = float(np.mean(values))
        sd = float(np.std(values, ddof=1)) if n > 1 else np.nan
        if n > 1:
            tcrit = float(stats.t.ppf(1 - alpha / 2, n - 1))
            ci_low = float(avg - tcrit * sd / np.sqrt(n))
            ci_high = float(avg + tcrit * sd / np.sqrt(n))
        else:
            ci_low = ci_high = np.nan

        results.append({
            "adicionado": float(level),
            "n": n,
            "media_recuperacao": avg,
            "sd": sd,
            "CV_percent": 100.0 * sd / abs(avg) if n > 1 and avg != 0 else np.nan,
            "IC_inferior": ci_low,
            "IC_superior": ci_high,
            "dentro_faixa_definida": bool(lower <= avg <= upper),
        })

    return x, pd.DataFrame(results)
