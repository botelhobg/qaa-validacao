# QAA II — Validação Analítica

Aplicativo web didático e reprodutível para avaliação de **linearidade** e **efeito de matriz** em métodos analíticos, desenvolvido no contexto da disciplina Química Analítica Avançada II.

## Estado atual

**Versão 0.2.0**

Módulos disponíveis:
- Linearidade
- Efeito de matriz

O projeto está sendo organizado também como software de pesquisa, com documentação metodológica, testes automáticos, versionamento e plano de verificação para futura publicação.


## Novidades da versão 0.3

### Desenho experimental configurável

No módulo **Linearidade** ou em cada curva do módulo **Efeito de matriz**, escolha **Configurar ensaio**.

1. Informe o número de níveis (2–40) e um número inicial de réplicas por nível (1–50).
2. Edite as **concentrações reais** e, se necessário, a quantidade de réplicas individual de cada nível.
3. Clique em **Gerar/redefinir tabela vazia**.
4. Digite ou cole as respostas e execute o cálculo.
5. Também é possível continuar com um exemplo, colar uma tabela livre ou importar CSV/Excel.

Exemplos de desenhos suportados: **4 níveis × 2 réplicas**, **7 níveis × 3 réplicas**, **5 níveis com 2/3/2/4/3 réplicas**, etc. As curvas de solvente e matriz podem ter planos distintos.

**Atenção:** a ordem das linhas é usada no cálculo de Durbin–Watson. Para interpretá-lo como verificação de autocorrelação, preserve a ordem real das leituras, especialmente quando as concentrações foram randomizadas. A falta de ajuste requer pelo menos três concentrações e réplicas independentes suficientes para estimar erro puro. Quando um diagnóstico não puder ser estimado, o aplicativo não deve declarar a linearidade plenamente validada.

### Precisão, veracidade e recuperação

Novo módulo com três abas independentes:

- **Precisão:** repetibilidade por variância residual intradia; precisão intermediária por ANOVA de um fator, inclusive séries com quantidades desiguais de réplicas.
- **Veracidade (MR/MRC):** média, desvio-padrão, viés absoluto/relativo, IC e teste t exploratório; a incerteza padrão do valor certificado entra na avaliação aproximada de compatibilidade.
- **Recuperação:** fortificação em níveis e réplicas configuráveis, resultados individuais, média, CV, IC e intervalo de aceitação definido pelo usuário.

Os novos módulos são didáticos; não substituem o planejamento do estudo de validação nem os critérios do guia adotado.

## Linearidade

Fluxo implementado:

1. regressão por mínimos quadrados ordinários;
2. resíduos e leverage;
3. Jackknife iterativo para valores extremos;
4. Ryan–Joiner;
5. Brown–Forsythe / Levene modificado;
6. Durbin–Watson;
7. ANOVA da regressão;
8. falta de ajuste contra erro puro.

O coeficiente de determinação é apresentado como informação descritiva, mas **não é usado isoladamente como evidência de linearidade**.

## Efeito de matriz

1. validação prévia das curvas em solvente e matriz;
2. comparação das variâncias residuais por teste F;
3. comparação das inclinações e interceptos por teste t;
4. uso de variâncias combinadas ou Welch/Satterthwaite conforme o teste F;
5. classificação do efeito como proporcional, constante, ambos ou ausência de evidência.

## Entrada de dados

O aplicativo aceita:
- edição/colagem direta;
- CSV;
- XLSX;
- XLSM;
- XLS.

Também tenta reconhecer automaticamente o bloco histórico da disciplina contendo concentração e resposta.

## Executar localmente

    python -m venv .venv
    python -m pip install -r requirements.txt
    streamlit run app.py

## Deploy no Streamlit Community Cloud

- Repository: botelhobg/qaa-validacao
- Branch: main
- Main file path: app.py

O arquivo `runtime.txt` solicita Python 3.12 e `.streamlit/config.toml` define o tema.

## Documentação para pesquisa e publicação

- `docs/METHODS.md` — descrição das rotinas estatísticas implementadas.
- `docs/REPRODUCIBILITY.md` — plano de verificação e comparação com as planilhas históricas.
- `docs/PAPER_OUTLINE.md` — esqueleto inicial de manuscrito.
- `CHANGELOG.md` — histórico de versões.
- `CITATION.cff` — metadados de citação do software.
- `.github/workflows/tests.yml` — testes automáticos a cada atualização do repositório.

## Verificação

Os testes básicos podem ser executados com:

    python test_core.py

Para uma publicação, a equivalência numérica entre as rotinas Python e as planilhas históricas deve ser documentada em datasets representativos, distinguindo resultados equivalentes de diferenças metodológicas deliberadas.

## Diferença metodológica importante

A estatística de Durbin–Watson é calculada pela definição convencional. Contudo, a versão web estima a significância por simulação Monte Carlo condicionada ao desenho experimental, permitindo trabalhar com tamanhos de amostra arbitrários. Planilhas históricas podem empregar limites tabulados.

## Referência metodológica principal

Souza, S. V. C.; Junqueira, R. G. *A procedure to assess linearity by ordinary least squares method.* Analytica Chimica Acta 552 (2005) 25–35.

## Uso

Ferramenta didática e de apoio à pesquisa. A decisão final sobre a validade de um método deve respeitar o uso pretendido, o guia adotado e os critérios de aceitação definidos para o laboratório.

## Próximos módulos planejados

Precisão, recuperação/veracidade, limites, CCα/CCβ, incerteza e decisão de conformidade.
