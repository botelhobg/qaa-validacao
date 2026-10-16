"""Testes rápidos de desenho flexível e dos módulos de validação."""
import math
import numpy as np
import pandas as pd
from qaa_design import make_template, normalize_calibration
from qaa_extra_core import intermediate_precision, bias_mrc, recovery
from validation_core import analyze_linearity

def run():
    plan=pd.DataFrame({"concentracao":[0.2,0.6,1.4],"replicas":[2,1,3]})
    base=make_template(plan)
    assert len(base)==6
    assert base.concentracao.tolist()==[.2,.2,.6,1.4,1.4,1.4]
    base["resposta"]=["0,2","0,21","0,59","1,4","1,41","1,42"]
    out,missing=normalize_calibration(base)
    assert len(out)==6 and missing==0 and abs(out.resposta.iloc[0]-.2)<1e-10
    try:
        make_template(pd.DataFrame({"concentracao":[1,1],"replicas":[2,3]}))
    except ValueError:pass
    else:raise AssertionError("Níveis duplicados deveriam ser rejeitados.")

    series=pd.DataFrame({"dia":["A"]*3+["B"]*2+["C"]*4,
      "resultado":[9.9,10.1,10,10.5,10.4,9.8,9.9,9.8,9.7]})
    r=intermediate_precision(series)
    assert abs(r["sr"]-math.sqrt(.0075))<1e-10
    assert abs(r["n0"]-(26/9))<1e-10
    assert r["s_IP"]>r["sr"] and r["p_entre"]<.01

    b=bias_mrc([9.8,9.9,9.7,10,9.8],10,.1)
    assert abs(b["bias"]+.16)<1e-10
    assert b["p_t_exploratorio"]<.05 and b["compatibilidade_expandida"]

    rec=pd.DataFrame({"adicionado":[1,1,3,3],"sem_fortificacao":[.3]*4,
      "fortificada":[1.2,1.25,3.2,3.25]})
    pts,summary=recovery(rec)
    assert len(pts)==4 and len(summary)==2
    assert abs(summary.iloc[0]["media_recuperacao"]-92.5)<1e-10

    # Matriz branca: o valor nominal é conhecido, R = C_encontrada/C_adicionada.
    blank_matrix=pd.DataFrame({
        "adicionado":[10,10,10,20,20,20],
        "encontrada":[11.8,12.,12.2,23.8,24.,24.2],
    })
    vals_blank,by_level_blank=recovery(blank_matrix,mode="matriz_branca")
    assert len(vals_blank)==6 and len(by_level_blank)==2
    assert np.allclose(by_level_blank["media_recuperacao"],[120.,120.])
    assert by_level_blank["dentro_faixa_definida"].all()
    assert np.all(np.isfinite(by_level_blank["IC_inferior"]))

    # Amostra nativa: R = (fortificada-sem_fortificacao)/adicionada.
    # Um viés aditivo de +2 mg/L se cancela, e a recuperação ainda é 100%.
    native=pd.DataFrame({
        "adicionado":[5.,5.,5.],
        "sem_fortificacao":[12.,12.,12.],
        "fortificada":[17.,17.,17.],
    })
    vals_native,by_level_native=recovery(native,mode="amostra_nativa")
    assert np.allclose(vals_native["recuperacao_percent"],100.)
    assert abs(by_level_native.iloc[0]["media_recuperacao"]-100)<1e-10
    blank_example=pd.DataFrame({"adicionado":[10.],"encontrada":[12.]})
    _,blank_one=recovery(blank_example,mode="matriz_branca")
    assert blank_one.iloc[0]["media_recuperacao"]==120.
    assert np.isnan(blank_one.iloc[0]["IC_inferior"])

    try:
        recovery(native,mode="matriz_branca")
    except ValueError:pass
    else:raise AssertionError("Matriz branca exige coluna encontrada.")
    try:
        recovery(native,mode="tipo_inexistente")
    except ValueError:pass
    else:raise AssertionError("Tipo de ensaio inválido deveria ser rejeitado.")
    try:
        recovery(pd.DataFrame({"adicionado":[0.],"encontrada":[2.]}),mode="matriz_branca")
    except ValueError:pass
    else:raise AssertionError("Adição nula deveria ser rejeitada.")

    no_reps=pd.DataFrame({"concentracao":[1,2,3,4,5,6],
                          "resposta":[.12,.23,.35,.46,.58,.69]})
    result=analyze_linearity(no_reps,remove_outliers=False,dw_nsim=200)
    assert result["anova"]["p_lof"] is None
    assert not result["linear_ok"]
    print("OK — entrada desbalanceada, precisão, viés, recuperação, erro puro")

if __name__=="__main__":
    run()
