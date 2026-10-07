from __future__ import annotations

import io
import json
from pathlib import Path
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from validation_core import analyze_linearity, compare_matrix_effect, result_to_serializable

st.set_page_config(page_title="QAA — Validação Analítica", page_icon="🧪", layout="wide")

st.markdown("""
<style>
:root { --teal:#0B4F45; --mint:#E8F4F0; --soft:#F7FBF9; }
.block-container {padding-top: 1.2rem; padding-bottom: 3rem;}
h1,h2,h3 {color: var(--teal);}
div[data-testid="stMetric"] {background:#F3F8F6; border:1px solid #D2E8E1; padding:10px 14px; border-radius:12px;}
.qaa-box {background:#F3F8F6; border-left:5px solid #0B4F45; padding:14px 16px; border-radius:8px; margin:8px 0 16px 0;}
.ok {background:#E8F7EE; border-left-color:#2E7D32;}
.bad {background:#FDEEEE; border-left-color:#B42318;}
.small {font-size:0.92rem; color:#526A64;}
</style>
""", unsafe_allow_html=True)

st.title("QAA — Validação Analítica")
st.caption("v0.2 • Linearidade + Efeito de Matriz • cálculos executados em Python")

with st.sidebar:
    st.header("Configurações")
    alpha = st.select_slider("α principal", options=[0.01, 0.05, 0.10], value=0.05)
    alpha_dw = st.select_slider("α — Durbin–Watson", options=[0.01, 0.05, 0.10], value=0.10)
    remove_outliers = st.toggle("Aplicar Jackknife iterativo", value=True)
    max_del_pct = st.slider("Máximo de exclusões (%)", 0, 30, 22, 1)
    dw_nsim = st.select_slider("Simulações para p(DW)", options=[2000, 5000, 8000, 15000], value=8000)
    st.divider()
    st.markdown("**Fluxo da versão 0.2**")
    st.caption("MQO → Jackknife → Ryan–Joiner → Brown–Forsythe → Durbin–Watson → ANOVA/falta de ajuste → comparação solvente × matriz.")


def read_uploaded(file):
    if file is None:
        return None
    name = file.name.lower()
    if name.endswith(".csv"):
        raw = file.getvalue()
        for sep in [",", ";", "\t"]:
            try:
                df = pd.read_csv(io.BytesIO(raw), sep=sep)
                if df.shape[1] >= 2:
                    return {"CSV": df}
            except Exception:
                pass
        raise ValueError("Não foi possível interpretar o CSV.")
    if name.endswith((".xlsx", ".xlsm", ".xls")):
        engine = "xlrd" if name.endswith(".xls") else "openpyxl"
        xls = pd.ExcelFile(file, engine=engine)
        return {sheet: pd.read_excel(file, sheet_name=sheet, engine=engine, header=None) for sheet in xls.sheet_names}
    raise ValueError("Formato não suportado. Use CSV, XLSX, XLSM ou XLS.")


def normalize_two_columns(df, x_col, y_col):
    out = df[[x_col, y_col]].copy()
    out.columns = ["concentracao", "resposta"]
    out["concentracao"] = pd.to_numeric(out["concentracao"], errors="coerce")
    out["resposta"] = pd.to_numeric(out["resposta"], errors="coerce")
    return out.dropna().reset_index(drop=True)


def excel_col_name(idx: int) -> str:
    n = idx + 1
    out = ""
    while n:
        n, rem = divmod(n - 1, 26)
        out = chr(65 + rem) + out
    return out


def detect_qaa_original_table(raw: pd.DataFrame):
    """Detecta a seção 'Pontos | Conc. | Resposta' das planilhas históricas."""
    for r in range(min(len(raw), 100)):
        vals = [str(v).strip().lower() if pd.notna(v) else "" for v in raw.iloc[r].tolist()]
        conc_idx = next((i for i,v in enumerate(vals) if v.startswith("conc")), None)
        resp_idx = next((i for i,v in enumerate(vals) if "resposta" in v), None)
        if conc_idx is not None and resp_idx is not None:
            start = r + 1
            end = start
            blanks = 0
            while end < len(raw):
                xv = pd.to_numeric(pd.Series([raw.iloc[end, conc_idx]]), errors="coerce").iloc[0]
                yv = pd.to_numeric(pd.Series([raw.iloc[end, resp_idx]]), errors="coerce").iloc[0]
                if pd.isna(xv) or pd.isna(yv):
                    blanks += 1
                    if blanks >= 1:
                        break
                else:
                    blanks = 0
                    end += 1
                    continue
                end += 1
            block = raw.iloc[start:end, [conc_idx, resp_idx]].copy()
            block.columns = ["concentracao", "resposta"]
            block["concentracao"] = pd.to_numeric(block["concentracao"], errors="coerce")
            block["resposta"] = pd.to_numeric(block["resposta"], errors="coerce")
            block = block.dropna().reset_index(drop=True)
            if len(block) >= 4:
                return block, r + 1, conc_idx, resp_idx
    return None


def curve_plot(points, fit, title, color="#0B4F45"):
    x = points["concentracao"].to_numpy(float)
    y = points["resposta"].to_numpy(float)
    xs = np.linspace(x.min(), x.max(), 120)
    ys = fit.intercept + fit.slope * xs
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=x, y=y, mode="markers", name="dados", marker=dict(size=9, color=color)))
    fig.add_trace(go.Scatter(x=xs, y=ys, mode="lines", name="MQO", line=dict(color=color, width=2)))
    fig.update_layout(title=title, xaxis_title="Concentração", yaxis_title="Resposta", height=420, margin=dict(l=20,r=20,t=50,b=20))
    return fig


def residual_plot(points, title):
    fig = go.Figure()
    fig.add_hline(y=0, line_dash="dash", line_color="#666")
    fig.add_trace(go.Scatter(x=points["concentracao"], y=points["residuo"], mode="markers", marker=dict(size=9, color="#0B4F45"), text=points.index.astype(str)))
    fig.update_layout(title=title, xaxis_title="Concentração", yaxis_title="Resíduo", height=380, margin=dict(l=20,r=20,t=50,b=20))
    return fig


def show_linearity_result(res, label="Curva"):
    fit = res["fit"]
    c1,c2,c3,c4 = st.columns(4)
    c1.metric("Inclinação", f"{fit.slope:.6g}")
    c2.metric("Intercepto", f"{fit.intercept:.6g}")
    c3.metric("R²", f"{fit.r2:.6f}")
    c4.metric("s(res)", f"{fit.s_res:.5g}")

    col1,col2 = st.columns(2)
    with col1:
        st.plotly_chart(curve_plot(res["points"], fit, f"{label} — curva"), use_container_width=True)
    with col2:
        st.plotly_chart(residual_plot(res["points"], f"{label} — resíduos"), use_container_width=True)

    if len(res["deleted"]):
        st.warning(f"Jackknife removeu {len(res['deleted'])} ponto(s). Veja a sequência abaixo.")
        st.dataframe(res["deleted"], use_container_width=True, hide_index=True)
    else:
        st.success("Jackknife: nenhum ponto excedeu o valor crítico.")

    rj=res["ryan_joiner"]; bf=res["brown_forsythe"]; dw=res["durbin_watson"]; av=res["anova"]
    tests = pd.DataFrame([
        ["Ryan–Joiner", rj.statistic, rj.p_value, rj.conclusion],
        ["Brown–Forsythe", bf.statistic, bf.p_value, bf.conclusion],
        ["Durbin–Watson", dw.statistic, dw.p_value, dw.conclusion],
        ["Regressão (F)", av["f_reg"], av["p_reg"], av["regression_conclusion"]],
        ["Falta de ajuste (F)", av["f_lof"], av["p_lof"], av["lof_conclusion"]],
    ], columns=["Diagnóstico","Estatística","p","Conclusão"])
    st.dataframe(tests, use_container_width=True, hide_index=True, column_config={"p": st.column_config.NumberColumn(format="%.5f")})

    with st.expander("Detalhes dos pontos e diagnósticos"):
        st.dataframe(res["points"], use_container_width=True, hide_index=True)
        st.markdown(f"**Ryan–Joiner:** Rcrit(10%)={rj.details.get('Rcrit_0.10',np.nan):.6f}; Rcrit(5%)={rj.details.get('Rcrit_0.05',np.nan):.6f}; Rcrit(1%)={rj.details.get('Rcrit_0.01',np.nan):.6f}")
        st.markdown(f"**Durbin–Watson:** p aproximado por {dw.details.get('nsim','—')} simulações Monte Carlo, condicionado às concentrações observadas.")

    if res["linear_ok"]:
        st.markdown('<div class="qaa-box ok"><b>Conclusão:</b> os dados são compatíveis com o modelo linear dentro dos critérios selecionados.</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="qaa-box bad"><b>Conclusão:</b> pelo menos um diagnóstico não sustenta a adequação completa do modelo linear. Revise os resultados antes de prosseguir.</div>', unsafe_allow_html=True)


def data_source_widget(key, demo_df):
    mode = st.radio("Entrada de dados", ["Exemplo", "Editar/colar tabela", "Enviar arquivo"], horizontal=True, key=f"mode_{key}")
    if mode == "Exemplo":
        return demo_df.copy()
    if mode == "Editar/colar tabela":
        return st.data_editor(demo_df.copy(), num_rows="dynamic", use_container_width=True, key=f"edit_{key}")

    uploaded = st.file_uploader("CSV, XLSX, XLSM ou XLS", type=["csv","xlsx","xlsm","xls"], key=f"up_{key}")
    if uploaded is None:
        st.info("Envie um arquivo para continuar.")
        return None
    try:
        sheets = read_uploaded(uploaded)
        sheet = st.selectbox("Planilha/aba", list(sheets), key=f"sheet_{key}")
        raw = sheets[sheet]
        if sheet == "CSV":
            st.dataframe(raw.head(15), use_container_width=True)
            cols = list(raw.columns)
            x_col = st.selectbox("Coluna de concentração", cols, key=f"x_{key}")
            y_col = st.selectbox("Coluna de resposta", cols, index=min(1,len(cols)-1), key=f"y_{key}")
            return normalize_two_columns(raw, x_col, y_col)

        detected = detect_qaa_original_table(raw)
        if detected is not None:
            block, header_row, cidx, ridx = detected
            st.success(f"Tabela QAA detectada automaticamente na linha {header_row}: concentração em {excel_col_name(cidx)} e resposta em {excel_col_name(ridx)}.")
            st.dataframe(block, use_container_width=True, hide_index=True)
            use_auto = st.toggle("Usar tabela detectada", value=True, key=f"auto_{key}")
            if use_auto:
                return block

        st.caption("Seleção manual: indique o intervalo de linhas e as colunas que contêm apenas os dados originais.")
        preview = raw.head(60).copy()
        preview.index = np.arange(1, len(preview) + 1)
        preview.columns = [excel_col_name(i) for i in range(preview.shape[1])]
        st.dataframe(preview, use_container_width=True, height=330)
        maxrow = len(raw)
        c1,c2 = st.columns(2)
        with c1:
            start_row = st.number_input("Primeira linha de dados (Excel)", min_value=1, max_value=maxrow, value=min(7,maxrow), key=f"start_{key}")
        with c2:
            end_row = st.number_input("Última linha de dados (Excel)", min_value=int(start_row), max_value=maxrow, value=min(int(start_row)+17,maxrow), key=f"end_{key}")
        labels = [f"{excel_col_name(i)} — coluna {i+1}" for i in range(raw.shape[1])]
        xlab = st.selectbox("Coluna de concentração", labels, index=min(1,len(labels)-1), key=f"xcol_{key}")
        ylab = st.selectbox("Coluna de resposta", labels, index=min(2,len(labels)-1), key=f"ycol_{key}")
        xi = labels.index(xlab); yi = labels.index(ylab)
        block = raw.iloc[int(start_row)-1:int(end_row), [xi, yi]].copy()
        block.columns = ["concentracao", "resposta"]
        block["concentracao"] = pd.to_numeric(block["concentracao"], errors="coerce")
        block["resposta"] = pd.to_numeric(block["resposta"], errors="coerce")
        return block.dropna().reset_index(drop=True)
    except Exception as e:
        st.error(f"Falha ao ler o arquivo: {e}")
        return None


DEMO_LINEAR = pd.DataFrame({
    "concentracao": np.repeat([0.1,0.3,0.5,0.7,0.9,1.1],3),
    "resposta": [0.062,0.070,0.063,0.205,0.205,0.208,0.357,0.360,0.351,0.488,0.498,0.466,0.653,0.662,0.655,0.799,0.805,0.802]
})
DEMO_SOLV = pd.DataFrame({
    "concentracao": np.repeat([2,4,6,8,10,12],3),
    "resposta": [0.096,0.106,0.116,0.198,0.210,0.222,0.303,0.314,0.325,0.405,0.418,0.431,0.512,0.524,0.536,0.612,0.626,0.640]
})
DEMO_MAT = pd.DataFrame({
    "concentracao": np.repeat([2,4,6,8,10,12],3),
    "resposta": [0.087,0.098,0.109,0.182,0.192,0.202,0.274,0.286,0.298,0.368,0.380,0.392,0.461,0.474,0.487,0.555,0.568,0.581]
})

page = st.sidebar.radio("Módulo", ["Linearidade", "Efeito de matriz", "Sobre o método"])

if page == "Linearidade":
    st.header("Linearidade")
    st.markdown('<div class="qaa-box">Fluxo: MQO → resíduos → Jackknife → normalidade → homoscedasticidade → independência → ANOVA da regressão e falta de ajuste.</div>', unsafe_allow_html=True)
    df = data_source_widget("lin", DEMO_LINEAR)
    if df is not None and len(df) >= 4:
        if st.button("Executar avaliação de linearidade", type="primary"):
            try:
                res = analyze_linearity(df, alpha=alpha, alpha_dw=alpha_dw, remove_outliers=remove_outliers, max_delete_fraction=max_del_pct/100, dw_nsim=dw_nsim)
                st.session_state["lin_result"] = res
            except Exception as e:
                st.error(str(e))
        if "lin_result" in st.session_state:
            res=st.session_state["lin_result"]
            show_linearity_result(res, "Linearidade")
            payload=json.dumps(result_to_serializable(res), ensure_ascii=False, indent=2)
            st.download_button("Baixar resultados (JSON)", payload, file_name="resultado_linearidade.json", mime="application/json")

elif page == "Efeito de matriz":
    st.header("Efeito de matriz")
    st.markdown('<div class="qaa-box">Cada curva é validada primeiro. Depois: variâncias residuais (F) → escolha do teste t → comparação de inclinações e interceptos.</div>', unsafe_allow_html=True)
    t1,t2 = st.tabs(["Curva em solvente", "Curva em matriz"])
    with t1:
        df_s = data_source_widget("solv", DEMO_SOLV)
    with t2:
        df_m = data_source_widget("mat", DEMO_MAT)

    if df_s is not None and df_m is not None:
        if st.button("Executar efeito de matriz", type="primary"):
            try:
                rs = analyze_linearity(df_s, alpha=alpha, alpha_dw=alpha_dw, remove_outliers=remove_outliers, max_delete_fraction=max_del_pct/100, dw_nsim=dw_nsim)
                rm = analyze_linearity(df_m, alpha=alpha, alpha_dw=alpha_dw, remove_outliers=remove_outliers, max_delete_fraction=max_del_pct/100, dw_nsim=dw_nsim)
                comp = compare_matrix_effect(rs, rm, alpha=alpha)
                st.session_state["em_result"]=(rs,rm,comp)
            except Exception as e:
                st.error(str(e))

        if "em_result" in st.session_state:
            rs,rm,comp=st.session_state["em_result"]
            colA,colB=st.columns(2)
            with colA:
                st.subheader("Solvente")
                st.metric("Equação", f"y = {rs['fit'].intercept:.5g} + {rs['fit'].slope:.5g}x")
                st.metric("R²", f"{rs['fit'].r2:.6f}")
                st.metric("s² residual", f"{rs['fit'].mse:.5g}")
            with colB:
                st.subheader("Matriz")
                st.metric("Equação", f"y = {rm['fit'].intercept:.5g} + {rm['fit'].slope:.5g}x")
                st.metric("R²", f"{rm['fit'].r2:.6f}")
                st.metric("s² residual", f"{rm['fit'].mse:.5g}")

            fig=go.Figure()
            for name,res,color in [("Solvente",rs,"#0B4F45"),("Matriz",rm,"#C46B2B")]:
                p=res["points"]; fit=res["fit"]
                fig.add_trace(go.Scatter(x=p["concentracao"], y=p["resposta"], mode="markers", name=f"{name} — dados", marker=dict(size=8,color=color)))
                xs=np.linspace(p["concentracao"].min(),p["concentracao"].max(),100)
                fig.add_trace(go.Scatter(x=xs,y=fit.intercept+fit.slope*xs,mode="lines",name=f"{name} — MQO",line=dict(color=color,width=2)))
            fig.update_layout(title="Curvas em solvente e matriz",xaxis_title="Concentração",yaxis_title="Resposta",height=450)
            st.plotly_chart(fig,use_container_width=True)

            if not rs["linear_ok"] or not rm["linear_ok"]:
                st.warning("Pelo menos uma curva não passou por todos os diagnósticos de linearidade. A comparação de efeito de matriz deve ser interpretada com cautela.")

            st.subheader("Comparação estatística")
            rows=pd.DataFrame([
                ["Variâncias residuais — F", comp["F"], comp["p_F"], "homogêneas" if comp["equal_residual_variances"] else "diferentes"],
                ["Inclinações — t", comp["t_slope"], comp["p_slope"], "diferem" if comp["p_slope"]<alpha else "não diferem"],
                ["Interceptos — t", comp["t_intercept"], comp["p_intercept"], "diferem" if comp["p_intercept"]<alpha else "não diferem"],
            ],columns=["Comparação","Estatística","p","Decisão"])
            st.dataframe(rows,use_container_width=True,hide_index=True,column_config={"p":st.column_config.NumberColumn(format="%.5f")})
            st.caption(f"Teste dos parâmetros: {comp['comparison_method']}")
            st.metric("Diferença relativa de inclinação (matriz/solvente − 1)", f"{comp['matrix_effect_percent_slope']:+.2f}%")

            cls=comp["classification"]
            css="bad" if "Efeito" in cls else "ok"
            st.markdown(f'<div class="qaa-box {css}"><b>Conclusão:</b> {cls}.</div>',unsafe_allow_html=True)
            if comp["calibration_in_solvent_recommended"]:
                st.success("Não há evidência estatística, neste conjunto, contra o uso da curva em solvente.")
            else:
                st.error("A curva em solvente não é a estratégia mais defensável para esta matriz sem correção/compensação.")

            with st.expander("Ver linearidade completa das duas curvas"):
                st.markdown("### Solvente")
                show_linearity_result(rs,"Solvente")
                st.markdown("### Matriz")
                show_linearity_result(rm,"Matriz")

            payload=json.dumps({"solvente":result_to_serializable(rs),"matriz":result_to_serializable(rm),"efeito_matriz":comp},ensure_ascii=False,indent=2)
            st.download_button("Baixar resultados (JSON)",payload,file_name="resultado_efeito_matriz.json",mime="application/json")

else:
    st.header("Sobre o método")
    st.markdown("""
    Esta versão foi construída para reproduzir o **fluxo didático das planilhas usadas em QAA II**, com execução integral dos cálculos em Python.

    **Linearidade**
    - mínimos quadrados ordinários, sem forçar a origem;
    - exclusão sucessiva de outliers pelo resíduo studentizado externamente (Jackknife);
    - Ryan–Joiner para normalidade dos resíduos;
    - Brown–Forsythe/Levene modificado para homoscedasticidade;
    - Durbin–Watson para independência;
    - ANOVA da regressão e teste de falta de ajuste contra erro puro.

    **Efeito de matriz**
    - validação prévia das curvas em solvente e matriz;
    - teste F das variâncias residuais;
    - comparação das inclinações e interceptos por teste t com variância combinada ou Welch/Satterthwaite;
    - classificação em efeito proporcional, constante, ambos ou ausência de evidência.

    **Observação sobre Durbin–Watson**: a planilha histórica usa limites tabulados. Para permitir qualquer número de observações no aplicativo, o valor de *d* é calculado da mesma forma, enquanto o *p* é estimado por Monte Carlo condicionado ao desenho de concentrações.
    """)
    st.info("Esta é uma ferramenta didática e de apoio à validação. A decisão final deve respeitar o guia/protocolo adotado pelo laboratório.\n\n**Versão:** 0.2 • QAA II")
