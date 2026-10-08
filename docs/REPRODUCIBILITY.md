# Reproducibility and verification plan

## Goal

The software is intended to make the statistical workflow auditable rather than to act as a black box.

A publication-quality verification should document three layers:

### Layer 1 — Unit-level calculations
Verify the numerical implementation of:
- OLS coefficients;
- fitted values and residuals;
- leverage;
- deleted/Jackknife residuals;
- Ryan–Joiner statistic;
- Brown–Forsythe statistic;
- Durbin–Watson statistic;
- ANOVA partitions;
- pure-error and lack-of-fit sums of squares;
- F test for residual variances;
- t tests for slopes and intercepts.

### Layer 2 — Dataset-level equivalence
Run selected calibration datasets through:
1. the historical spreadsheet workflow;
2. the Python implementation;
3. an independent statistical implementation where possible.

Record numerical agreement and explain any intentional methodological differences.

### Layer 3 — Analytical interpretation
Use datasets representing:
- acceptable linear calibration;
- one influential/outlying observation;
- heteroscedastic residuals;
- curvature/lack of fit;
- autocorrelated residuals;
- proportional matrix effect;
- constant matrix effect;
- no detectable matrix effect.

For each case, compare the software decision with the intended analytical interpretation.

## Known intentional difference

The historical spreadsheet workflow for Durbin–Watson may use tabulated critical limits. The web application estimates a two-sided significance level by Monte Carlo simulation conditional on the observed concentration design.

This difference must be stated explicitly in any publication describing equivalence with the spreadsheet workflow.

## Recommended artifact package for a paper

Archive:
- tagged software release;
- exact example datasets;
- expected outputs;
- test script;
- environment/dependency specification;
- screenshots of the public application;
- manuscript supplementary table comparing spreadsheet and Python outputs.

A Zenodo archive of a tagged GitHub release can later provide a citable DOI.
