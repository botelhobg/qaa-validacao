# QAA II — Validação Analítica

Aplicativo web didático para avaliação de **linearidade** e **efeito de matriz** em métodos analíticos, desenvolvido para a disciplina Química Analítica Avançada II.

## Módulos atuais

### Linearidade
Fluxo implementado:

1. regressão por mínimos quadrados ordinários;
2. resíduos e leverage;
3. Jackknife iterativo para valores extremos;
4. Ryan–Joiner;
5. Brown–Forsythe/Levene modificado;
6. Durbin–Watson;
7. ANOVA da regressão;
8. falta de ajuste contra erro puro.

### Efeito de matriz

1. validação prévia das curvas em solvente e matriz;
2. comparação das variâncias residuais por teste F;
3. comparação das inclinações e interceptos por teste t;
4. uso de variâncias combinadas ou Welch/Satterthwaite conforme o teste F;
5. classificação do efeito como proporcional, constante, ambos ou ausente.

## Entrada de dados

O aplicativo aceita edição/colagem direta, CSV, XLSX, XLSM e XLS. Também tenta reconhecer automaticamente o bloco histórico da disciplina com concentração e resposta.

## Executar localmente

    python -m venv .venv
    python -m pip install -r requirements.txt
    streamlit run app.py

## Deploy no Streamlit Community Cloud

- Repository: botelhobg/qaa-validacao
- Branch: main
- Main file path: app.py

O arquivo runtime.txt solicita Python 3.12 e .streamlit/config.toml define o tema.

## Referência metodológica principal

Souza, S. V. C.; Junqueira, R. G. A procedure to assess linearity by ordinary least squares method. Analytica Chimica Acta 552 (2005) 25–35.

Ferramenta didática e de apoio. A decisão final sobre a validade de um método deve respeitar o guia e os critérios de aceitação adotados.
