# Statistical methods implemented

## Scope

Version 0.2 implements two linked validation modules:

1. **Linearity**
2. **Matrix effect**

The matrix-effect workflow depends on the suitability of the individual calibration curves. Therefore, each curve is evaluated through the same linearity routine before slope and intercept comparisons are interpreted.

---

## 1. Ordinary least-squares regression

For a calibration dataset with concentration (x_i) and analytical response (y_i), the model is

[
y_i = a + b x_i + e_i
]

with intercept (a), slope (b), and residual (e_i = y_i - hat y_i).

The fit is not forced through the origin.

The software reports:
- slope;
- intercept;
- (R^2);
- residual standard deviation;
- fitted values;
- residuals;
- leverage;
- studentized residual diagnostics.

(R^2) is shown descriptively and is not used alone to establish linearity.

---

## 2. Leverage and externally studentized residuals

For a two-parameter straight-line model,

[
h_i = rac{1}{n} + rac{(x_i-ar{x})^2}{S_{xx}}
]

Internally studentized residuals are calculated as

[
r_i = rac{e_i}{s_{res}sqrt{1-h_i}}
]

The deleted/Jackknife residual used for screening is

[
J_i = r_isqrt{rac{n-3}{n-2-r_i^2}}
]

Points may be screened iteratively, with the most extreme absolute value considered first. The maximum exclusion fraction is configurable and defaults to approximately the historical QAA/Souza–Junqueira workflow limit.

Deletion is a diagnostic action, not a substitute for investigating the analytical cause of an anomalous observation.

---

## 3. Ryan–Joiner normality diagnostic

Residuals are ordered and correlated with expected normal scores. The Ryan–Joiner correlation coefficient is compared with finite-sample critical-value approximations.

The implemented decision is intended to reproduce the teaching workflow used in QAA II: residual normality is assessed before relying on the subsequent parametric tests.

---

## 4. Homoscedasticity

The application implements the Brown–Forsythe / modified Levene idea by comparing absolute deviations from group medians across the concentration range.

A non-significant result supports the assumption of approximately constant residual variance required by unweighted OLS.

---

## 5. Independence of residuals

The Durbin–Watson statistic is

[
d = rac{sum_{i=2}^{n}(e_i-e_{i-1})^2}{sum_i e_i^2}
]

Because fixed tabulated (d_L/d_U) limits do not cover every possible dataset entered into a web application, version 0.2 keeps the conventional (d) statistic but estimates a two-sided significance level by Monte Carlo simulation conditional on the observed design matrix.

This differs from historical spreadsheet implementations that rely on lookup tables. The interface explicitly reports this distinction.

---

## 6. Regression significance and lack of fit

The residual sum of squares is decomposed into pure error and lack of fit when genuine replicate measurements are available:

[
SS_{res}=SS_{PE}+SS_{LOF}
]

with

[
MS_{PE}=rac{SS_{PE}}{n-u}
]

and

[
MS_{LOF}=rac{SS_{LOF}}{u-2}
]

where (u) is the number of distinct concentration levels.

The lack-of-fit statistic is

[
F_{LOF}=rac{MS_{LOF}}{MS_{PE}}
]

A significant regression demonstrates that the response changes with concentration; it does **not** by itself demonstrate that the straight-line model is adequate. A non-significant lack-of-fit result supports the linear model within the tested range.

---

## 7. Matrix effect

Two calibration curves are compared:

- analyte in solvent;
- analyte in matrix.

Both are first evaluated independently by the linearity module.

### 7.1 Residual variances

Residual variances are compared by an F test. This determines whether a pooled-variance comparison is appropriate.

### 7.2 Slopes and intercepts

If residual variances are considered homogeneous, the application uses pooled residual variance in the comparison of the calibration parameters.

If the residual variances differ, the application uses a Welch/Satterthwaite-type comparison.

Interpretation:

- significantly different slopes → **proportional matrix effect**;
- significantly different intercepts → **constant matrix effect**;
- both significant → **proportional and constant matrix effect**;
- neither significant → no statistical evidence of matrix effect under the tested conditions.

The relative slope difference is also displayed as

[
100left(rac{b_{matrix}}{b_{solvent}}-1ight)
]

for descriptive interpretation.

---

## 8. Decision logic

The application intentionally separates:

- statistical calculation;
- diagnostic evidence;
- analytical interpretation.

The result should be interpreted against the validation guide, intended use, concentration range, matrix scope, and laboratory acceptance criteria.

---

## Main methodological reference

Souza, S. V. C.; Junqueira, R. G. **A procedure to assess linearity by ordinary least squares method.** *Analytica Chimica Acta* 552 (2005) 25–35.

The implementation also follows the intralaboratory validation workflow used in the QAA II teaching materials for matrix-effect evaluation.
