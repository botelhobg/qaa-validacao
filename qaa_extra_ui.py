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
    st.subheader("Ensaios de adição-recuperação")
    st.caption(
        "Escolha o desenho experimental antes de informar as concentrações. "
        "As duas abordagens avaliam aspectos distintos da recuperação."
    )

    options = {
        "Matriz branca — concentração conhecida": "matriz_branca",
        "Amostra com analito nativo — adição incremental": "amostra_nativa",
    }
    choice = st.radio(
        "Tipo de ensaio",
        list(options),
        index=1,
        key="tipo_ensaio_recuperacao",
        horizontal=True,
    )
    mode = options[choice]
    is_blank = mode == "matriz_branca"

    if is_blank:
        st.info(
            "**Matriz branca:** o analito nativo é ausente ou desprezível. "
            "Compare diretamente a concentração encontrada com a concentração conhecida "
            "introduzida antes das etapas que deseja avaliar."
        )
        st.latex(r"R(\\%)=100\\,\\frac{C_{\\mathrm{encontrada}}}{C_{\\mathrm{adicionada}}}")
        st.caption(
            "Se a matriz já contém analito, esta fórmula não se aplica sem uma "
            "correção/avaliação apropriada do teor inicial."
        )
        columns = ["adicionado", "encontrada"]
    else:
        st.info(
            "**Amostra com analito nativo:** compare a medida após fortificação com "
            "a mesma amostra sem fortificação. Cada linha deve corresponder a "
            "medições emparelhadas ou a uma estimativa basal analiticamente justificada."
        )
        st.latex(
            r"R(\\%)=100\\,\\frac{C_{\\mathrm{fortificada}}"
            r"-C_{\\mathrm{sem\\,fortificacao}}}{C_{\\mathrm{adicionada}}}"
        )
        st.caption(
            "A recuperação da quantidade adicionada pode ser 100% mesmo quando "
            "há um viés constante na concentração originalmente presente."
        )
        columns = ["adicionado", "sem_fortificacao", "fortificada"]

    st.caption(
        "Todas as concentrações devem estar na mesma unidade, corrigidas "
        "pelas diluições introduzidas na fortificação quando necessário."
    )

    a, b = st.columns(2)
    with a:
        levels = st.number_input(
            "Níveis de fortificação", min_value=1, max_value=30, value=3,
            key=f"rec_levels_{mode}",
        )
    with b:
        reps = st.number_input(
            "Réplicas inicialmente por nível", min_value=1, max_value=50, value=3,
            key=f"rec_reps_{mode}",
        )

    plan = pd.DataFrame({
        "adicionado": np.arange(1, int(levels) + 1, dtype=float),
        "replicas": [int(reps)] * int(levels),
    })
    edited = st.data_editor(
        plan, num_rows="fixed", hide_index=True, use_container_width=True,
        key=f"rec_plan_{mode}_{levels}_{reps}",
        column_config={
            "adicionado": st.column_config.NumberColumn(
                "Concentração adicionada", required=True, min_value=0.00000001,
            ),
            "replicas": st.column_config.NumberColumn(
                "Réplicas", required=True, min_value=1, max_value=50, step=1,
            ),
        },
    )

    if st.button("Gerar tabela para o ensaio", key=f"gen_rec_{mode}"):
        numeric_plan = edited.copy()
        for col in ["adicionado", "replicas"]:
            numeric_plan[col] = pd.to_numeric(numeric_plan[col], errors="coerce")
        invalid = (
            numeric_plan.isna().any().any()
            or (numeric_plan["adicionado"] <= 0).any()
            or (numeric_plan["replicas"] < 1).any()
            or (numeric_plan["replicas"] > 50).any()
            or (numeric_plan["replicas"] % 1 != 0).any()
            or numeric_plan["adicionado"].nunique() != len(numeric_plan)
            or numeric_plan["replicas"].sum() > 1000
        )
        if invalid:
            st.error(
                "Informe concentrações positivas e distintas; réplicas inteiras "
                "entre 1 e 50; máximo de 1000 medições."
            )
        else:
            rows = []
            for level, nrep in numeric_plan[["adicionado", "replicas"]].itertuples(
                index=False, name=None
            ):
                rows.extend([{
                    "adicionado": float(level),
                    **{col: np.nan for col in columns if col != "adicionado"},
                }] * int(nrep))
            st.session_state[f"rec_blank_{mode}"] = pd.DataFrame(rows, columns=columns)
            st.session_state[f"rev_rec_{mode}"] = (
                st.session_state.get(f"rev_rec_{mode}", 0) + 1
            )
            st.session_state.pop(f"rec_result_{mode}", None)

    if is_blank:
        example = pd.DataFrame({
            "adicionado": [10, 10, 10, 20, 20, 20],
            "encontrada": [11.8, 12.0, 12.2, 23.8, 24.0, 24.2],
        })
    else:
        example = pd.DataFrame({
            "adicionado": [5, 5, 5, 10, 10, 10],
            "sem_fortificacao": [12.0, 12.1, 11.9, 12.0, 12.1, 11.9],
            "fortificada": [17.0, 17.2, 16.9, 22.0, 22.1, 21.9],
        })

    blank = st.session_state.get(
        f"rec_blank_{mode}", pd.DataFrame(columns=columns)
    )
    data = editor(f"rec_{mode}", blank, example)

    left, right = st.columns(2)
    with left:
        lower = st.number_input(
            "Critério mínimo de recuperação (%)", min_value=0.0, value=80.0,
            key=f"rec_lower_{mode}",
        )
    with right:
        upper = st.number_input(
            "Critério máximo de recuperação (%)", min_value=0.0, value=120.0,
            key=f"rec_upper_{mode}",
        )

    if st.button(
        "Calcular recuperação", type="primary", key=f"calculate_recovery_{mode}"
    ):
        try:
            individual, summary = recovery(
                data, alpha=alpha, lower=lower, upper=upper, mode=mode
            )
            st.session_state[f"rec_result_{mode}"] = {
                "individual": individual,
                "summary": summary,
                "lower": lower, "upper": upper, "alpha": alpha,
            }
        except (ValueError, KeyError) as exc:
            st.error(str(exc))
            st.session_state.pop(f"rec_result_{mode}", None)

    result = st.session_state.get(f"rec_result_{mode}")
    if result is not None:
        if (
            result["lower"] != lower or result["upper"] != upper
            or result["alpha"] != alpha
        ):
            st.warning("Critério ou α alterado: clique em Calcular recuperação novamente.")

        st.markdown("**Resumo por nível de adição**")
        st.dataframe(
            result["summary"], hide_index=True, use_container_width=True
        )
        st.caption(
            "IC: intervalo de confiança da recuperação média. Para n = 1, "
            "não é possível estimar desvio-padrão, CV ou IC."
        )
        with st.expander("Recuperações individuais"):
            st.dataframe(
                result["individual"], hide_index=True, use_container_width=True
            )
        export = result["individual"].copy()
        export.insert(0, "tipo_ensaio", mode)
        st.download_button(
            "Exportar leituras e recuperações (CSV)",
            export.to_csv(index=False).encode("utf-8-sig"),
            file_name=f"recuperacao_{mode}.csv",
            mime="text/csv",
            key=f"download_rec_{mode}",
        )

        if is_blank:
            st.info(
                "**Interpretação:** resultados próximos de 100% sustentam boa "
                "recuperação da concentração conhecida na matriz branca estudada. "
                "A representatividade do material e a inclusão de todas as etapas "
                "do preparo determinam o alcance da avaliação de veracidade."
            )
        else:
            st.warning(
                "**Interpretação:** o ensaio avalia o incremento provocado "
                "pela fortificação. Um erro aditivo constante pode se cancelar "
                "na subtração; 100% de recuperação não prova que a concentração "
                "nativa esteja livre de viés."
            )
        st.caption(
            "Os limites mostrados são critérios definidos pelo usuário, "
            "não critérios regulatórios universais. A recuperação média dentro "
            "da faixa, isoladamente, não comprova adequação do método."
        )

def render_validation_page(alpha=.05):
    st.header("Precisão, veracidade e recuperação")
    st.info("Novos módulos com entrada configurável. Exemplos são opcionais; critérios e desenho experimental são definidos pelo usuário.")
    a,b,c=st.tabs(["Precisão","Veracidade / MRC","Recuperação"])
    with a:precision_ui(alpha)
    with b:trueness_ui(alpha)
    with c:recovery_ui(alpha)
