"""Verificação de abertura das páginas do Streamlit."""
from streamlit.testing.v1 import AppTest

def check(page):
    test=AppTest.from_file("app.py",default_timeout=20).run()
    assert len(test.exception)==0,[str(e.message) for e in test.exception]
    test.sidebar.radio[0].set_value(page).run()
    assert len(test.exception)==0,[str(e.message) for e in test.exception]
    return test

if __name__=="__main__":
    check("Linearidade")
    check("Efeito de matriz")
    check("Precisão, veracidade e recuperação")
    check("Limites analíticos e decisão")
    print("OK — interface Streamlit carrega nos quatro módulos")
