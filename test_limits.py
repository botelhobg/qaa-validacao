"""Testes numéricos independentes do módulo de limites analíticos."""
import numpy as np
import pandas as pd
from scipy import stats

from qaa_limits_core import (
    lob_lod, ich_limits, experimental_loq, gaussian_decision_limit
)


def check_close(a,b,tol=1e-10):
    assert np.isclose(a,b,rtol=tol,atol=tol),f"{a} != {b}"


def run():
    blanks=np.array([-.01,.01,0.,.02,-.02])
    low=np.array([.05,.06,.09,.07,.08])
    r=lob_lod(blanks,low,alpha=.05,beta=.05,finite_sample=False)
    z=stats.norm.ppf(.95)
    expected_lob=blanks.mean()+z*blanks.std(ddof=1)
    expected_lod=expected_lob+z*low.std(ddof=1)
    check_close(r["lob"],expected_lob)
    check_close(r["lod"],expected_lod)
    assert r["observed_detection_rate"]==1
    corrected=lob_lod(blanks,low,finite_sample=True)
    assert corrected["lob"]>r["lob"]
    assert corrected["lod"]>r["lod"]

    ich=ich_limits(.05,.005)
    check_close(ich["lod"],.33)
    check_close(ich["loq"],1.)
    check_close(ich_limits(-.05,.005)["loq"],1.)
    for slope,sigma in [(0,.1),(.1,0),(.1,-1)]:
        try:ich_limits(slope,sigma)
        except ValueError:pass
        else:raise AssertionError("Parâmetros inválidos devem ser rejeitados.")

    measurements=pd.DataFrame({
      "nominal":[.1,.1,.1,.2,.2,.2,.5,.5,.5],
      "encontrado":[.02,.14,.05,.19,.20,.21,.49,.50,.51],
    })
    out=experimental_loq(measurements,cv_max=20,bias_max=15,min_reps=3)
    check_close(out["loq_candidate"],.2)
    assert not bool(out["summary"].iloc[0]["aprovado"])
    assert bool(out["summary"].iloc[1]["aprovado"])
    assert bool(out["summary"].iloc[2]["aprovado"])
    out2=experimental_loq(measurements,cv_max=1.,bias_max=1.,min_reps=3)
    assert out2["loq_candidate"] is None
    unbalanced=pd.DataFrame({
        "nominal":[.1,.1,.2,.2,.2,.5],
        "encontrado":[.1,.11,.2,.2,.2,.5]
    })
    u=experimental_loq(unbalanced,cv_max=10.,bias_max=10.,min_reps=3)
    check_close(u["loq_candidate"],.2)
    assert not u["summary"].iloc[0]["n_suficiente"]
    assert not u["summary"].iloc[2]["n_suficiente"]
    invalid=pd.DataFrame({"nominal":[0.,0.],"encontrado":[1.,2.]})
    try:experimental_loq(invalid)
    except ValueError:pass
    else:raise AssertionError("Concentração nominal zero deve ser rejeitada.")
    try:experimental_loq(pd.DataFrame({"nominal":[1.,1.],
                                       "encontrado":["abc","1"]}))
    except ValueError:pass
    else:raise AssertionError("Entrada não numérica deve ser rejeitada.")

    d=gaussian_decision_limit(10.,.5,.05,.05,10.9)
    check_close(d["cc_alpha"],10.+z*.5)
    check_close(d["cc_beta"],10.+2*z*.5)
    check_close(d["false_positive_at_limit"],.05)
    check_close(d["probability_detection_at_cc_beta"],.95)
    assert d["noncompliant"]
    assert not gaussian_decision_limit(10.,.5,.05,.05,10.1)["noncompliant"]
    assert gaussian_decision_limit(0.,1.,.01,.10)["cc_alpha"]>2.
    for L,sd in [(-1,1),(10,0),(10,-.1)]:
        try:gaussian_decision_limit(L,sd)
        except ValueError:pass
        else:raise AssertionError("Entradas inválidas devem ser rejeitadas.")
    print("OK — LoB/LoD, ICH DL/QL, LoQ experimental, CCα/CCβ")


if __name__=="__main__":
    run()
