"""Interface Streamlit — limites analíticos e capacidade de decisão."""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from scipy import stats

from qaa_limits_core import (
    lob_lod, ich_limits, experimental_loq, gaussian_decision_limit
)


def _one_column(key, label, example, initial_n=12, minimum=3):
    mode=st.radio("Entrada de dados",["Meus dados","Exemplo didático"],
                  horizontal=True,key=f"source_{key}")
    if mode == "Exemplo didático":
        frame=pd.DataFrame({label:example})
    else:
        n=st.number_input("Número inicial de medições",min_value=minimum,
                          max_value=300,value=initial_n,key=f"n_{key}")
        frame=pd.DataFrame({label:[np.nan]*int(n)})
    return st.data_editor(
        frame,hide_index=True,num_rows="dynamic",use_container_width=True,
        key=f"data_{key}_{mode}_{len(frame)}",
        column_config={label:st.column_config.NumberColumn(label,format="%.5f")}
    )[label]


def _sample_plot(blank, low, lob, lod):
    fig=go.Figure()
    fig.add_trace(go.Histogram(
        x=blank,nbinsx=min(20,max(5,len(blank)//2)),name="Branco",
        opacity=.6,marker_color="#0B695A"
    ))
    fig.add_trace(go.Histogram(
        x=low,nbinsx=min(20,max(5,len(low)//2)),name="Baixa concentração",
        opacity=.5,marker_color="#CF8041"
    ))
    fig.add_vline(x=lob,line_dash="dash",line_color="#18585B",
                  annotation_text="LoB")
    fig.add_vline(x=lod,line_dash="dot",line_color="#AB5430",
                  annotation_text="LoD")
    fig.update_layout(
        barmode="overlay",height=355,margin=dict(t=15,b=45,l=30,r=15),
        xaxis_title="Resultado em concentração aparente",
        yaxis_title="Frequência",legend=dict(orientation="h",y=1.2)
    )
    return fig


def _lob_lod_tab():
    st.subheader("LoB e LoD por branco e amostra de baixa concentração")
    st.caption("A entrada deve estar em concentração aparente (mesma unidade nas duas séries), não em sinal bruto.")
    st.info(
        "Abordagem paramétrica simplificada, inspirada em CLSI EP17-A2: "
        "estima o percentil superior do branco e usa a dispersão das "
        "amostras de baixa concentração para obter o LoD. Não equivale a "
        "uma validação CLSI completa com múltiplos brancos/lotes."
    )
    a,b=st.columns(2)
    with a:
        risk_a=st.selectbox("Risco α — branco acima de LoB",[.01,.05,.10],
                            index=1,key="lob_alpha",
                            format_func=lambda x:f"{x:.0%}")
    with b:
        risk_b=st.selectbox("Risco β — amostra baixa abaixo de LoB",[.01,.05,.10],
                            index=1,key="lob_beta",
                            format_func=lambda x:f"{x:.0%}")
    correction=st.checkbox(
        "Usar correção para desvio-padrão amostral (uma série por grupo)",
        value=True,key="lob_correction"
    )
    col1,col2=st.columns(2)
    with col1:
        st.markdown("**Brancos**")
        blanks=_one_column(
            "lob_blank","concentracao_aparente",
            [.002,-.006,.011,.007,-.003,.009,.004,-.008,.010,.001,-.004,.005],
            initial_n=12
        )
    with col2:
        st.markdown("**Amostras com baixa concentração**")
        lows=_one_column(
            "lod_low","concentracao_aparente",
            [.068,.092,.087,.081,.098,.076,.086,.095,.073,.090,.082,.101],
            initial_n=12
        )

    if st.button("Estimar LoB e LoD",key="estimate_lob",type="primary"):
        try:
            result=lob_lod(blanks,lows,alpha=risk_a,beta=risk_b,
                           finite_sample=correction)
            st.session_state["lob_result"]=result
        except ValueError as exc:
            st.session_state.pop("lob_result",None)
            st.error(str(exc))

    r=st.session_state.get("lob_result")
    if r:
        if (r["alpha"]!=risk_a or r["beta"]!=risk_b or
            r["small_sample_correction"]!=correction):
            st.warning("Parâmetros modificados: execute a estimativa novamente.")
        a,b=st.columns(2)
        a.metric("LoB",f'{r["lob"]:.5g}')
        b.metric("LoD (estimado)",f'{r["lod"]:.5g}')
        st.latex(r"LoB=\bar C_B+c_\alpha s_B")
        st.latex(r"LoD=LoB+c_\beta s_L")
        st.caption(
            f"Branco: n={r['n_blank']}, média={r['mean_blank']:.4g}, "
            f"s={r['sd_blank']:.4g}, cα={r['c_blank']:.4g}."
        )
        st.caption(
            f"Baixo nível: n={r['n_low']}, média={r['mean_low']:.4g}, "
            f"s={r['sd_low']:.4g}, cβ={r['c_low']:.4g}. "
            f"Observações acima do LoB: {r['n_low_above_lob']}/{r['n_low']} "
            f"({r['observed_detection_rate']:.1%})."
        )
        if min(r["n_blank"],r["n_low"])<20:
            st.warning("Exemplo com poucas observações: use um desenho experimental mais amplo para validação formal.")
        st.plotly_chart(
            _sample_plot(
                pd.to_numeric(blanks,errors="coerce").dropna().to_numpy(),
                pd.to_numeric(lows,errors="coerce").dropna().to_numpy(),
                r["lob"],r["lod"]
            ),use_container_width=True
        )
        st.caption(
            "A fração observada acima do LoB é descritiva; uma série curta não "
            "garante a probabilidade β pretendida. LoD calculado não é equivalente "
            "à verificação experimental independente da detecção."
        )


def _ich_tab():
    st.subheader("DL e QL estimados pela razão σ/S")
    st.info(
        "**ICH Q2(R2)** — estimativa pelo desvio-padrão da resposta "
        "(σ) e pela inclinação da curva (S). Escolha e documente a origem de σ."
    )
    slope=st.number_input("Inclinação da curva S (sinal por unidade de concentração)",
                          min_value=-1e9,max_value=1e9,value=.050,
                          format="%.7f",key="ich_slope")
    source=st.radio("Origem de σ da resposta",
                    ["Informar σ diretamente","Estimar σ com réplicas do branco"],
                    horizontal=True,key="ich_source")
    if source=="Informar σ diretamente":
        sigma=st.number_input(
            "σ da resposta (unidades de sinal)",min_value=0.,max_value=1e9,
            value=.005,format="%.7f",key="ich_sigma"
        )
        st.caption(
            "O valor pode ser o desvio-padrão residual de curvas adequadas "
            "próximas dos limites, ou a estimativa de σ admitida pelo método."
        )
    else:
        readings=_one_column(
            "ich_blank","resposta_branco",
            [.002,-.003,.001,.004,-.001,.003,-.002,.002,.0,.005],
            initial_n=10
        )
        yy=pd.to_numeric(
            readings.astype(str).str.replace(",",".",regex=False),
            errors="coerce"
        ).dropna().to_numpy(float)
        sigma=float(np.std(yy,ddof=1)) if len(yy)>=3 else None
        if sigma is None:
            st.caption("Preencha pelo menos três respostas de branco.")
        else:
            st.metric("σ dos brancos",f"{sigma:.6g}")
    if st.button("Estimar DL e QL",key="ich_calc",type="primary"):
        try:
            if sigma is None:
                raise ValueError("Preencha pelo menos três respostas de branco.")
            result=ich_limits(slope,sigma)
            st.session_state["ich_result"]=result
        except ValueError as exc:
            st.session_state.pop("ich_result",None)
            st.error(str(exc))
    r=st.session_state.get("ich_result")
    if r:
        if r["slope"]!=slope or sigma is None or r["sigma_response"]!=sigma:
            st.warning("Entradas modificadas: execute o cálculo novamente.")
        a,b=st.columns(2)
        a.metric("DL estimado",f'{r["lod"]:.5g}')
        b.metric("QL estimado",f'{r["loq"]:.5g}')
        st.latex(r"DL=\frac{3{,}3\sigma}{|S|}")
        st.latex(r"QL=\frac{10\sigma}{|S|}")
        st.warning(
            "Valores estimados não substituem a verificação experimental "
            "da precisão, viés e desempenho no nível de quantificação pretendido."
        )


def _loq_tab():
    st.subheader("LoQ experimental por precisão e viés")
    st.caption(
        "Teste concentrações nominais conhecidas com determinações independentes. "
        "O candidato a LoQ é o menor nível ensaiado que cumpre todos os critérios definidos."
    )
    aa,bb,cc=st.columns(3)
    with aa:
        cv_max=st.number_input("CV máximo (%)",min_value=0.,value=20.,key="loq_cv")
    with bb:
        bias_max=st.number_input("|Viés| máximo (%)",min_value=0.,value=15.,key="loq_bias")
    with cc:
        min_reps=st.number_input("Mínimo de réplicas por nível",2,30,3,key="loq_min_reps")
    source=st.radio("Entrada",["Meus dados","Exemplo didático"],horizontal=True,key="loq_source")
    if source=="Exemplo didático":
        example=[
            (.10,.05),(.10,.15),(.10,.11),
            (.20,.17),(.20,.21),(.20,.18),
            (.50,.48),(.50,.51),(.50,.49),
            (1.0,.99),(1.0,1.03),(1.0,1.01)
        ]
        data=pd.DataFrame(example,columns=["nominal","encontrado"])
        data=st.data_editor(data,hide_index=True,num_rows="dynamic",
                            use_container_width=True,key="loq_example_editor")
    else:
        st.markdown("**Plano experimental configurável**")
        aa,bb=st.columns(2)
        with aa:
            levels=st.number_input("Níveis testados",1,30,4,key="loq_levels")
        with bb:
            repeats=st.number_input("Réplicas inicialmente por nível",1,50,3,key="loq_repeats")
        plan=pd.DataFrame({
            "nominal":np.arange(1,int(levels)+1,dtype=float),
            "replicas":[int(repeats)]*int(levels)
        })
        edited=st.data_editor(
            plan,hide_index=True,num_rows="fixed",use_container_width=True,
            key=f"loq_plan_{levels}_{repeats}",
            column_config={
                "nominal":st.column_config.NumberColumn("Concentração nominal",required=True),
                "replicas":st.column_config.NumberColumn("Réplicas",min_value=1,max_value=50,required=True)
            }
        )
        if st.button("Gerar tabela de concentrações",key="loq_generate"):
            pp=edited.copy()
            for col in ["nominal","replicas"]:
                pp[col]=pd.to_numeric(pp[col],errors="coerce")
            invalid=(
                pp.isna().any().any() or (pp["nominal"]<=0).any()
                or pp["nominal"].nunique()!=len(pp)
                or (pp["replicas"]<1).any() or (pp["replicas"]>50).any()
                or (pp["replicas"]%1!=0).any() or pp["replicas"].sum()>1000
            )
            if invalid:
                st.error("Concentrações devem ser positivas e distintas; 1 a 50 réplicas por nível.")
            else:
                df=pd.DataFrame(
                    [{"nominal":float(c),"encontrado":np.nan}
                     for c,n in pp[["nominal","replicas"]].itertuples(index=False,name=None)
                     for _ in range(int(n))],
                    columns=["nominal","encontrado"]
                )
                st.session_state["loq_blank"]=df
                st.session_state["loq_rev"]=st.session_state.get("loq_rev",0)+1
                st.session_state.pop("loq_result",None)
        blank=st.session_state.get("loq_blank",pd.DataFrame(columns=["nominal","encontrado"]))
        if blank.empty:
            st.info("Configure os níveis e clique em **Gerar tabela de concentrações**.")
        data=st.data_editor(
            blank,num_rows="dynamic",hide_index=True,use_container_width=True,
            key=f"loq_data_{st.session_state.get('loq_rev',0)}"
        )

    if st.button("Avaliar LoQ experimental",key="loq_evaluate",type="primary"):
        try:
            result=experimental_loq(data,cv_max,bias_max,int(min_reps))
            st.session_state["loq_result"]=result
        except ValueError as exc:
            st.session_state.pop("loq_result",None)
            st.error(str(exc))

    r=st.session_state.get("loq_result")
    if r:
        if (r["cv_max"]!=cv_max or r["bias_max"]!=bias_max or
            r["min_reps"]!=min_reps):
            st.warning("Critérios alterados: execute a avaliação novamente.")
        if r["loq_candidate"] is None:
            st.error("Nenhum nível ensaiado atendeu simultaneamente aos critérios.")
        else:
            st.metric("LoQ experimental candidato",f'{r["loq_candidate"]:.6g}')
        st.dataframe(r["summary"],hide_index=True,use_container_width=True)
        st.download_button(
            "Exportar resumo (CSV)",
            r["summary"].to_csv(index=False).encode("utf-8-sig"),
            file_name="loq_por_nivel.csv",mime="text/csv",key="loq_download"
        )
        if r["inconsistent_higher_levels"]:
            st.warning(
                "Há níveis MAIS ALTOS que falharam após o primeiro aprovado. "
                "O LoQ candidato não implica que toda a faixa esteja validada."
            )
        st.caption(r["warning"])
        st.caption(
            "CV calculado como s/|média|; viés relativo da média em relação "
            "à concentração nominal. A aprovação exige réplicas suficientes."
        )


def _cc_tab():
    st.subheader("CCα e CCβ — modelo gaussiano unilateral")
    st.warning(
        "**Atenção metodológica:** esta é uma demonstração de limite de decisão "
        "para declarar um resultado ACIMA de um limite permitido, assumindo "
        "desvio-padrão constante e distribuição normal. Não implementa "
        "automaticamente o Regulamento (UE) 2021/808, cujas definições e "
        "procedimentos diferem para substâncias autorizadas e proibidas."
    )
    col1,col2=st.columns(2)
    with col1:
        limit=st.number_input(
            "Limite permitido L (unidade de concentração)",
            value=10.,min_value=0.,format="%.5f",key="cc_limit"
        )
        alpha=st.selectbox("α — falso não conforme quando C = L",[.01,.05,.10],
            index=1,format_func=lambda x:f"{x:.0%}",key="cc_alpha")
    with col2:
        beta=st.selectbox("β — falha em detectar C = CCβ",[.01,.05,.10],
            index=1,format_func=lambda x:f"{x:.0%}",key="cc_beta")
        source=st.radio("Origem de s perto do limite",
            ["Informar s","Réplicas próximas do limite"],
            key="cc_source")
    if source=="Informar s":
        sd=st.number_input(
            "Desvio-padrão s perto do limite",
            min_value=0.,value=.50,format="%.5f",key="cc_sd"
        )
    else:
        st.caption(
            "Informe determinações independentes de um material próximo do limite "
            "L. O desvio-padrão representa a variabilidade próxima ao ponto de decisão."
        )
        series=_one_column(
            "cc_near_limit","resultado",
            [9.49,9.72,10.02,10.21,10.44,9.61,9.91,10.14,10.32,10.11],
            initial_n=10
        )
        yy=pd.to_numeric(series.astype(str).str.replace(",",".",regex=False),errors="coerce").dropna()
        sd=float(yy.std(ddof=1)) if len(yy)>=3 else None
        if sd is None:
            st.caption("São necessárias pelo menos três medições válidas.")
        else:
            st.metric("s estimado",f"{sd:.5g}")

    measured=st.number_input(
        "Resultado observado para decisão (opcional, exemplo)",
        value=10.90,format="%.5f",key="cc_observed"
    )
    if st.button("Calcular CCα e CCβ",type="primary",key="cc_run"):
        try:
            if sd is None:
                raise ValueError("Informe pelo menos três leituras para estimar s.")
            st.session_state["cc_result"]=gaussian_decision_limit(
                limit,sd,alpha,beta,measured
            )
        except ValueError as exc:
            st.session_state.pop("cc_result",None)
            st.error(str(exc))
    r=st.session_state.get("cc_result")
    if r:
        if any([r["limite"]!=limit,r["sigma"]!=sd,
                r["alpha"]!=alpha,r["beta"]!=beta,
                r["measured_value"]!=measured]):
            st.warning("Parâmetros alterados: recalcule CCα/CCβ.")
        a,b=st.columns(2)
        a.metric("CCα — limite de decisão",f'{r["cc_alpha"]:.5g}')
        b.metric("CCβ — teor verdadeiro detectado com 1−β",f'{r["cc_beta"]:.5g}')
        st.latex(r"CC_\alpha=L+z_{1-\alpha}\,s")
        st.latex(r"CC_\beta=CC_\alpha+z_{1-\beta}\,s")
        if r["noncompliant"]:
            st.error(
                f"Resultado {measured:.5g} > CCα {r['cc_alpha']:.5g}: "
                "**decisão de não conformidade** sob a regra assumida."
            )
        else:
            st.info(
                f"Resultado {measured:.5g} ≤ CCα {r['cc_alpha']:.5g}: "
                "**não foi demonstrada não conformidade** sob esta regra. "
                "Isso NÃO comprova a conformidade."
            )
        fig=go.Figure()
        xx=np.linspace(limit-3.3*sd,r["cc_beta"]+3.3*sd,400)
        for mu,name,color in [
            (limit,"Verdadeiro C = L","#0A6555"),
            (r["cc_beta"],"Verdadeiro C = CCβ","#C27B35")
        ]:
            yy=stats.norm.pdf(xx,loc=mu,scale=sd)
            fig.add_trace(go.Scatter(x=xx,y=yy,mode="lines",
                name=name,line=dict(color=color,width=3)))
        fig.add_vline(x=r["cc_alpha"],line_dash="dash",
                      line_color="#9B312A",annotation_text="CCα")
        fig.update_layout(
            xaxis_title="Resultado medido",yaxis_title="Densidade",
            height=370,margin=dict(t=20,b=35,l=25,r=15)
        )
        st.plotly_chart(fig,use_container_width=True)
        st.caption(
            f"Quando C=L, a chance de resultado >CCα é α={r['false_positive_at_limit']:.1%}. "
            f"Quando C=CCβ, a chance de resultado >CCα é "
            f"{r['probability_detection_at_cc_beta']:.1%}."
        )


def render_limits_page():
    st.header("Limites Analíticos e Capacidade de Decisão")
    st.caption(
        "LoB · LoD · LoQ · CCα · CCβ — métodos e critérios sempre identificados"
    )
    t1,t2,t3,t4=st.tabs([
        "LoB / LoD (branco)",
        "DL / QL (ICH)",
        "LoQ experimental",
        "CCα / CCβ"
    ])
    with t1:_lob_lod_tab()
    with t2:_ich_tab()
    with t3:_loq_tab()
    with t4:_cc_tab()
    with st.expander("Fontes e limitações metodológicas"):
        st.markdown(
            "**ICH Q2(R2):** DL = 3,3σ/S e QL = 10σ/S são estimativas "
            "que requerem confirmação adequada ao procedimento. "
            "[ICH Q2(R2)](https://database.ich.org/sites/default/files/ICH_Q2%28R2%29_Guideline_2023_1130_ErrorCorrection_2025.pdf)"
        )
        st.markdown(
            "**CLSI EP17-A2:** para LoB e LoD, a versão aqui usada é "
            "uma simplificação com séries únicas e correção opcional do "
            "desvio-padrão amostral. Projetos reais podem exigir "
            "múltiplos materiais, lotes e verificações experimentais."
        )
        st.markdown(
            "**CCα / CCβ:** o exemplo gaussiano adotado não substitui "
            "definições e protocolos aplicáveis a diferentes classes de "
            "substâncias do [Regulamento (UE) 2021/808]"
            "(https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX%3A32021R0808)."
        )
