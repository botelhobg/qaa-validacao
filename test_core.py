import pandas as pd
from validation_core import analyze_linearity, compare_matrix_effect

def test_linearidade_basica():
    df = pd.read_csv("examples/linearidade_exemplo.csv")
    r = analyze_linearity(df, dw_nsim=1000)
    assert r["fit"].n >= 10
    assert r["fit"].r2 > 0.99

def test_efeito_matriz():
    raw = pd.read_csv("examples/efeito_matriz_exemplo.csv")
    s = raw[["concentracao","solvente"]].rename(columns={"solvente":"resposta"})
    m = raw[["concentracao","matriz"]].rename(columns={"matriz":"resposta"})
    rs = analyze_linearity(s, remove_outliers=False, dw_nsim=1000)
    rm = analyze_linearity(m, remove_outliers=False, dw_nsim=1000)
    c = compare_matrix_effect(rs, rm)
    assert rs["fit"].slope > rm["fit"].slope
    assert "Efeito de matriz" in c["classification"]

if __name__ == "__main__":
    test_linearidade_basica()
    test_efeito_matriz()
    print("OK — testes básicos aprovados")
