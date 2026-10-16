# Changelog

All notable changes to **QAA — Validação Analítica** will be documented here.

## [0.4.0] — 2026-10-16

### Added
- Limites analíticos e decisão: LoB/LoD (brancos + baixo nível), DL/QL por σ/S segundo ICH Q2(R2), LoQ experimental (CV e viés) e CCα/CCβ gaussiano unilateral didático.
- Planos de estudo configuráveis com concentrações e réplicas desbalanceadas para LoQ experimental.
- Riscos α e β ajustáveis, gráficos e interpretação dos limites.
- Notas de escopo para diferenciar estimativas didáticas de procedimentos regulatórios.
- Testes numéricos independentes e teste de abertura do novo módulo.
- Documentação metodológica em `docs/LIMITS.md`.

### Caution
- A demonstração de CCα/CCβ não substitui o Regulamento (UE) 2021/808.
- Os limites estimados exigem verificação em condições reais do método.

## [0.3.1] — 2026-10-16

### Added
- Seleção explícita do ensaio de adição-recuperação: matriz branca ou amostra com analito nativo.
- Tabelas de dados, fórmulas, exemplos e interpretação específicos para cada desenho experimental.
- Preservação independente do planejamento e dos resultados de cada modalidade.
- Casos de teste numéricos para a diferença entre recuperação global e recuperação incremental.

### Notes
- Recuperação próxima de 100% na fortificação incremental não prova ausência de viés no analito nativo.

## [0.3.0] — 2026-10-16

### Added
- Configuração independente de níveis e replicatas para linearidade e curvas de matriz.
- Suporte a réplicas desbalanceadas, com edição de cada nível e exportação CSV do modelo.
- Módulo de precisão (repetibilidade/precisão intermediária por ANOVA).
- Módulo de veracidade/viés frente a MR ou MRC.
- Módulo de recuperação por fortificação e critérios editáveis.
- Testes de regressão para os novos módulos.

### Fixed
- O aplicativo não declara linearidade validada quando falta teste de erro puro/falta de ajuste.
- Recomendação de curva em solvente condicionada à adequação prévia das duas curvas.

### Notes
- A sequência real das medições deve ser preservada para interpretação de Durbin–Watson.
- Critérios estatísticos e analíticos dependem do guia aplicável.

## [0.2.0] — 2026-10-08

### Added
- Web interface in Streamlit.
- Linearity workflow based on OLS regression and residual diagnostics.
- Iterative deleted/Jackknife studentized-residual screening.
- Ryan–Joiner normality diagnostic.
- Brown–Forsythe / modified Levene homoscedasticity diagnostic.
- Durbin–Watson statistic with Monte Carlo significance estimate.
- Regression ANOVA and lack-of-fit test against pure error.
- Matrix-effect module comparing solvent and matrix calibration curves.
- Residual-variance comparison by F test.
- Slope and intercept comparisons using pooled-variance or Welch/Satterthwaite t tests.
- CSV, XLSX, XLSM and XLS input.
- Automatic recognition of the historical QAA calibration-table format.
- Example datasets and basic tests.
- Streamlit Cloud deployment configuration.

### Notes
- This release is intended for teaching and research support.
- The software does not replace laboratory-specific validation protocols or regulatory decision criteria.
