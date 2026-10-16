"""Entrada configurável para calibrações com níveis e replicatas arbitrários."""
import numpy as np
import pandas as pd
import streamlit as st

def make_template(plan):
    x = pd.to_numeric(plan["concentracao"], errors="coerce")
    n = pd.to_numeric(plan["replicas"], errors="coerce")
    if len(plan)<2 or x.isna().any() or n.isna().any() or x.nunique()!=len(x):
        raise ValueError("Defina ao menos dois níveis com concentrações distintas.")
    if ((n<1)|(n>50)|(n!=np.floor(n))).any() or n.sum()>1000:
        raise ValueError("Informe 1 a 50 réplicas inteiras por nível (máximo de 1000 leituras).")
    return pd.DataFrame([(float(xi), np.nan) for xi,ni in zip(x,n) for _ in range(int(ni))],
                        columns=["concentracao","resposta"])

def normalize_calibration(df):
    out=df[["concentracao","resposta"]].copy()
    for c in out.columns:
        out[c]=pd.to_numeric(out[c].astype(str).str.replace(",",".",regex=False),errors="coerce")
    missing=int(out.isna().any(axis=1).sum())
    return out.dropna().reset_index(drop=True),missing

def calibration_design_widget(key):
    st.markdown("**1. Configure o seu plano de calibração**")
    left,right=st.columns(2)
    with left:
        n_levels=st.number_input("Níveis de concentração",2,40,6,key=f"levels_{key}")
    with right:
        n_reps=st.number_input("Réplicas inicialmente por nível",1,50,3,key=f"reps_{key}")
    plan=pd.DataFrame({"concentracao":np.arange(1,int(n_levels)+1,dtype=float),
                       "replicas":[int(n_reps)]*int(n_levels)})
    st.caption("Você pode alterar cada concentração e o número de réplicas por nível, inclusive de forma desbalanceada.")
    edited=st.data_editor(plan,hide_index=True,num_rows="fixed",use_container_width=True,
        column_config={"concentracao":st.column_config.NumberColumn("Concentração",required=True),
                       "replicas":st.column_config.NumberColumn("Réplicas",min_value=1,max_value=50,required=True)},
        key=f"plan_{key}_{n_levels}_{n_reps}")
    if st.button("Gerar / redefinir tabela vazia",key=f"generate_{key}"):
        try:
            st.session_state[f"table_{key}"]=make_template(edited)
            st.session_state[f"revision_{key}"]=st.session_state.get(f"revision_{key}",0)+1
        except ValueError as err:
            st.error(str(err))
    if f"table_{key}" not in st.session_state:
        st.info("Clique em **Gerar tabela** para preencher suas respostas experimentais.")
        return None
    st.markdown("**2. Cole ou digite as respostas experimentais**")
    blank=st.session_state[f"table_{key}"]
    table=st.data_editor(blank,hide_index=True,num_rows="dynamic",use_container_width=True,
        key=f"readings_{key}_{st.session_state.get(f'revision_{key}',0)}")
    st.download_button("Baixar modelo CSV",blank.to_csv(index=False).encode("utf-8-sig"),
        file_name=f"modelo_{key}.csv",mime="text/csv",key=f"download_{key}")
    valid,missing=normalize_calibration(table)
    if missing: st.caption(f"{missing} linhas sem resposta completa não serão incluídas.")
    if valid.empty: return None
    counts=valid.groupby("concentracao").size()
    st.caption(f"{len(counts)} níveis • {len(valid)} medições • "+", ".join(f"{x:g}: {n} rép." for x,n in counts.items()))
    if len(counts)<3:
        st.warning("O teste de falta de ajuste precisa de pelo menos três concentrações distintas.")
    if (counts==1).all():
        st.warning("Sem replicatas independentes não é possível estimar erro puro para testar falta de ajuste.")
    if len(counts)<4:
        st.info("O Brown–Forsythe do aplicativo requer quatro níveis ou mais.")
    return valid if len(valid)>=4 and len(counts)>=2 else None
