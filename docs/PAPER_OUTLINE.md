# Suggested manuscript outline

## Working title

**An open web application for transparent statistical evaluation of calibration linearity and matrix effects in analytical method validation**

Alternative teaching-oriented title:

**From spreadsheet to reproducible web workflow: an open Python tool for teaching and evaluating linearity and matrix effects in analytical chemistry**

## 1. Introduction
- Method validation requires more than high (R^2).
- Residual assumptions and lack-of-fit are often omitted in routine practice.
- Matrix-effect assessment depends on comparing valid calibration functions.
- Spreadsheets are accessible but can obscure formulas, versioning and reproducibility.
- Objective: implement an auditable web workflow reproducing the statistical sequence used in analytical-chemistry teaching and intralaboratory validation.

## 2. Software design
- Python numerical core.
- Streamlit user interface.
- Separation between statistical engine and presentation layer.
- Supported input formats.
- Deployment architecture.
- Open repository and versioning.

## 3. Statistical methods
### 3.1 OLS model
### 3.2 Deleted/Jackknife residuals
### 3.3 Ryan–Joiner
### 3.4 Brown–Forsythe
### 3.5 Durbin–Watson
### 3.6 Regression ANOVA and lack of fit
### 3.7 Residual-variance comparison
### 3.8 Comparison of slopes and intercepts
### 3.9 Decision logic for matrix effect

## 4. Verification strategy
- Comparison with historical validation spreadsheets.
- Synthetic edge cases.
- Published/example datasets where raw data are available.
- Unit tests and continuous integration.
- Numerical tolerance criteria.

## 5. Case studies
Suggested minimum:
1. fully acceptable linear calibration;
2. apparently high-(R^2) but non-linear dataset;
3. dataset with an outlier/high-leverage observation;
4. solvent vs matrix curves with proportional matrix effect;
5. solvent vs matrix curves without detectable effect.

## 6. Educational implementation
- Student workflow.
- Visible calculations rather than black-box output.
- Interpretation of assumptions and hypotheses.
- Potential use in computer-based practical classes.

## 7. Limitations
- Current version assumes a univariate straight-line calibration model.
- OLS is not appropriate when heteroscedasticity requires weighted regression.
- Outlier flags require analytical investigation.
- Monte Carlo Durbin–Watson significance differs from fixed-table implementations.
- Validation acceptance criteria remain method- and regulation-specific.

## 8. Future development
- precision;
- trueness/recovery;
- LOD/LOQ;
- CCα/CCβ;
- uncertainty;
- conformity assessment;
- weighted regression;
- exportable validation report.

## Candidate journals
The journal should be chosen only after the verification package is complete. Potential scopes include analytical chemistry education, chemometrics/software notes, or method-validation/application journals.
