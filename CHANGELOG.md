# Changelog

All notable changes to **QAA — Validação Analítica** will be documented here.

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
