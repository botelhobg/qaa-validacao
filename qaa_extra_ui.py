"""Interface didática de precisão, veracidade e recuperação."""
import numpy as np
import pandas as pd
import streamlit as st
from qaa_extra_core import intermediate_precision,bias_mrc,recovery

def editor(key,blank,example):
    mode=st.radio("Dados",["Meus dados","Exemplo didático"],horizontal=True,key=f"src_{key}")
    df=blank if mode=="Meus dados" else example
    rev=st.session_state.get(f"rev_{key}",0)
    return st.data_editor(df,num_rows="dynamic",hide_index=True,use_container_width=True,
                          key=f"editor_{key}_{mode}_{rev}")

def precision_ui(alpha):
    st.subheader("Repetibilidade e precisão intermediária")
    st.caption("ANOVA por dia/série, com quantidades iguais ou diferentes de réplicas.")
    c1,c2=st.columns(2)
    with c1:days=st.number_input("Número de dias/séries",1,40,3,key="num_days")
    with c2:reps=st.number_input("Réplicas por dia (inicial)",1,50,3,key="num_reps_day")
    plan=pd.DataFrame({"dia":[f"Dia {i+1}" for i in range(int(days))],"replicas":[int(reps)]*int(days)})
    custom=st.data_editor(plan,hide_index=True,num_rows="fixed",use_container_width=True,key=f"plan_days_{days}_{reps}")
    if st.button("Gerar tabela para os meus dados",key="generate_precision"):
        if custom.replicas.isna().any() or (custom.replicas<1).any() or (custom.replicas>50).any() or custom.replicas.sum()>1000:
            st.error("Informe 1 a 50 réplicas por dia; máximo de 1000 observações.")
        else:
            st.session_state["precision_blank"]=pd.DataFrame([
                {"dia":r.dia,"resultado":np.nan} for r in custom.itertuples(index=False)
                for _ in range(int(r.replicas))])
            st.session_state["rev_precision"]=st.session_state.get("rev_precision",0)+1
            st.session_state.pop("precision_result",None)
    sample=pd.DataFrame({"dia":["Dia 1"]*3+["Dia 2"]*3+["Dia 3"]*3,
        "resultado":[9.83,9.89,9.86,9.99,10.05,10.01,9.90,9.95,9.94]})
    blank=st.session_state.get("precision_blank",pd.DataFrame({"dia":[],"resultado":[]}))
    df=editor("precision",blank,sample)
    if st.button("Calcular precisão",type="primary",key="calculate_precision"):
        try:st.session_state["precision_result"]=intermediate_precision(df,alpha)
        except ValueError as exc:st.error(str(exc))
    if "precision_result" in st.session_state:
        r=st.session_state["precision_result"]
        a,b,c=st.columns(3)
        a.metric("Média",f'{r["media"]:.5g}')
        b.metric("sᵣ (repetibilidade)",f'{r["sr"]:.5g}')
        c.metric("sIP (intermediária)",f'{r["s_IP"]:.5g}' if r["s_IP"] is not None else "—")
        st.write("RSDᵣ:",f'{r["rms_r_percent"]:.2f}%' if r["rms_r_percent"] is not None else "—")
        if r.get("p_entre") is not None:
            st.write(f'F entre dias = {r["f"]:.4f}; p = {r["p_entre"]:.4g}; n₀ = {r["n0"]:.3f}')
        st.info(r["mensagem"])
        with st.expander("Modelo estatístico"):
            st.latex(r"s_r^2=MS_{dentro}")
            st.latex(r"s_{dia}^2=\\max\\left[\\frac{MS_{entre}-MS_{dentro}}{n_0},0\\right]")
            st.latex(r"s_{IP}=\\sqrt{s_r^2+s_{dia}^2}")
            st.caption("Modelo ANOVA de um fator aleatório; a validade depende da independência e do desenho experimental.")

def trueness_ui(alpha):
    st.subheader("Veracidade / viés frente a MR ou MRC")
    a,b,c=st.columns(3)
    with a:ref=st.number_input("Valor de referência",value=10.0,format="%.5f")
    with b:uref=st.number_input("Incerteza padrão u do MRC",min_value=0.,value=0.,format="%.5f")
    with c:n=st.number_input("Determinações iniciais",2,100,6,key="trueness_n")
    blank=pd.DataFrame({"resultado":[np.nan]*int(n)})
    sample=pd.DataFrame({"resultado":[9.81,9.95,9.91,9.88,9.89,9.96]})
    df=editor("trueness",blank,sample)
    if st.button("Calcular viés",type="primary",key="calculate_bias"):
        try:st.session_state["bias_result"]=bias_mrc(df.resultado,ref,uref,alpha)
        except ValueError as exc:st.error(str(exc))
    if "bias_result" in st.session_state:
        r=st.session_state["bias_result"]
        a,b,c=st.columns(3)
        a.metric("Média",f'{r["media"]:.5g}')
        b.metric("Viés",f'{r["bias"]:+.5g}')
        c.metric("Viés relativo",f'{r["bias_percent"]:+.2f}%' if r["bias_percent"] is not None else "—")
        st.write(f'IC da média: [{r["ic_media"][0]:.5g}, {r["ic_media"][1]:.5g}]')
        st.write(f'Teste t exploratório contra valor fixo: t = {r["t_exploratorio"]:.4f}; p = {r["p_t_exploratorio"]:.4g}.')
        st.write(f'Compatibilidade aproximada considerando u(MRC): |viés| ≤ {r["U_diferenca_aprox"]:.5g}?',
                 "Sim" if r["compatibilidade_expandida"] else "Não")
        st.caption("O teste t ignora u(MRC). A compatibilidade com incerteza expandida é aproximada e não comprova ausência de viés.")

def recovery_ui(alpha):
    st.subheader("Recuperação por fortificação")
    st.caption("Cada linha: concentração medida sem fortificação, concentração medida após fortificação e quantidade efetivamente adicionada.")
    a,b=st.columns(2)
    with a:lev=st.number_input("Níveis de fortificação",1,30,3,key="rec_levels")
    with b:reps=st.number_input("Réplicas iniciais por nível",1,50,3,key="rec_reps")
    plan=pd.DataFrame({"adicionado":np.arange(1,int(lev)+1,dtype=float),"replicas":[int(reps)]*int(lev)})
    ed=st.data_editor(plan,num_rows="fixed",hide_index=True,use_container_width=True,key=f"rec_plan_{lev}_{reps}")
    if st.button("Gerar tabela de recuperação",key="gen_rec"):
        if ed.adicionado.isna().any() or (ed.adicionado<=0).any() or ed.adicionado.nunique()!=len(ed) or ed.replicas.isna().any() or (ed.replicas<1).any() or ed.replicas.sum()>1000:
            st.error("Defina níveis de adição positivos e distintos e réplicas inteiras.")
        else:
            st.session_state["rec_blank"]=pd.DataFrame([
                {"adicionado":float(r.adicionado),"sem_fortificacao":np.nan,"fortificada":np.nan}
                for r in ed.itertuples(index=False) for _ in range(int(r.replicas))])
            st.session_state["rev_rec"]=st.session_state.get("rev_rec",0)+1
            st.session_state.pop("rec_result",None)
    sample=pd.DataFrame({"adicionado":[1]*3+[3]*3+[5]*3,"sem_fortificacao":[1]*9,
        "fortificada":[1.94,1.98,1.95,3.93,3.88,3.95,5.80,5.88,5.90]})
    blank=st.session_state.get("rec_blank",pd.DataFrame({"adicionado":[],"sem_fortificacao":[],"fortificada":[]}))
    df=editor("rec",blank,sample)
    a,b=st.columns(2)
    with a:lo=st.number_input("Critério mínimo (%)",min_value=0.,value=80.)
    with b:hi=st.number_input("Critério máximo (%)",min_value=0.,value=120.)
    if st.button("Calcular recuperações",type="primary",key="calculate_recovery"):
        try:
            if lo>hi:raise ValueError("Limite mínimo excede o máximo.")
            st.session_state["rec_result"]=recovery(df,alpha,lo,hi)
        except ValueError as exc:st.error(str(exc))
    if "rec_result" in st.session_state:
        raw,summary=st.session_state["rec_result"]
        st.dataframe(summary,use_container_width=True,hide_index=True)
        st.download_button("Exportar leituras e recuperações (CSV)",
            raw.to_csv(index=False).encode("utf-8-sig"),
            file_name="recuperacoes.csv",mime="text/csv")
        st.latex(r"R(\\%)=100\\,\\frac{C_{fortificada}-C_{sem\\ fortificacao}}{C_{adicionada}}")
        st.caption("Os limites são apenas critérios configurados pelo usuário; observe IC, dispersão e requisitos do método.")

def render_validation_page(alpha=.05):
    st.header("Precisão, veracidade e recuperação")
    st.info("Novos módulos com entrada configurável. Exemplos são opcionais; critérios e desenho experimental são definidos pelo usuário.")
    a,b,c=st.tabs(["Precisão","Veracidade / MRC","Recuperação"])
    with a:precision_ui(alpha)
    with b:trueness_ui(alpha)
    with c:recovery_ui(alpha)
