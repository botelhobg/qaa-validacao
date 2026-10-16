# Limites analíticos e capacidade de decisão — versão 0.4

O módulo `Limites analíticos e decisão` reúne quatro fluxos distintos. Não
devem ser interpretados como intercambiáveis ou como uma implementação
automática de qualquer guia regulatório completo.

## 1. LoB e LoD: séries do branco e de baixa concentração

**Entrada:** resultados convertidos para **concentração aparente**
(mesma unidade nas duas séries), inclusive valores negativos não
censurados que possam surgir após a subtração do branco.

Para cada conjunto, a média e o desvio-padrão amostral são calculados
sem impor que a média do branco seja zero:

```text
LoB = média_branco + c(α) × s_branco
LoD = LoB + c(β) × s_baixa_concentração
```

Por padrão, usa-se uma correção para o desvio-padrão amostral em cada série
individual:

```text
c(p) = z(1-p) / (1 - 1/(4 × (n-1)))
```

É possível desligar a correção e usar `c=z(1-p)`, caso se queira apenas a
aproximação normal simplificada. A interface apresenta a taxa observada de
resultados da amostra de baixa concentração superiores ao LoB, mas essa taxa
**não é uma verificação de probabilidade β**.

**Atenção:** esta implementação deliberadamente não substitui os desenhos
experimentais completos do CLSI EP17 com materiais/lotes independentes,
agrupamento das estimativas de dispersão e confirmação experimental da
capacidade de detecção.

## 2. Limites estimados por σ/S (ICH Q2(R2))

**Entrada:** inclinação S de uma curva adequada e desvio-padrão da
resposta σ, diretamente informado ou estimado de réplicas de branco.

```text
DL = 3.3 × σ / |S|
QL = 10 × σ / |S|
```

Os valores são **estimativas**; demonstrar precisão e viés aceitáveis
no QL pretendido exige experimentos independentes e critérios
compatíveis com o uso pretendido.

Referência: [ICH Q2(R2)](https://database.ich.org/sites/default/files/ICH_Q2%28R2%29_Guideline_2023_1130_ErrorCorrection_2025.pdf)

## 3. LoQ experimental por precisão e viés

**Entrada:** concentrações nominais conhecidas e resultados individuais
da análise em cada nível. O número de níveis e de réplicas é configurável,
inclusive quando o estudo é desbalanceado.

Para cada nível:

```text
CV (%) = 100 × s / |média|
viés (%) = 100 × (média - nominal) / nominal
```

O usuário define limites para CV e valor absoluto do viés, além do
mínimo de réplicas exigidas. O menor nível **efetivamente testado**
que cumpre os três critérios aparece como **candidato a LoQ**.

**Não há extrapolação para concentrações menores que os níveis testados.**
Se um nível acima do candidato falhar, o aplicativo alerta que a faixa
de trabalho não está automaticamente demonstrada.

## 4. CCα e CCβ: exemplo gaussiano unilateral

**Objetivo:** ilustrar como um resultado é classificado como
**acima de um limite permitido L** quando há variabilidade analítica
próxima desse limite.

Supondo

```text
Resultado observado | C verdadeiro ~ Normal(C verdadeiro, s²)
```

com s constante na região de decisão:

```text
CCα = L + z(1-α) × s
CCβ = CCα + z(1-β) × s
```

Regra proposta: observar `y > CCα` significa declarar não conformidade
**segundo o modelo assumido**. Para a concentração verdadeira `C=L`, o
risco de decisão de não conformidade é `α`. Em `C=CCβ`, a
probabilidade de obter `y>CCα` é `1-β`.

A interpretação inversa é importante: `y≤CCα` significa que a não
conformidade **não foi demonstrada** por essa regra, e não que a amostra
seja definitivamente conforme.

**IMPORTANTE SOBRE O REGULAMENTO (UE) 2021/808:** definições, objetivos
e procedimentos diferem conforme substância autorizada/proibida e
finalidade confirmatória ou de triagem. A implementação didática
acima **não é uma implementação regulatória de CCα/CCβ**.
Não deve ser usada para emitir decisões oficiais de conformidade
sem desenvolvimento/validação do protocolo aplicável.

Referência: [Regulamento (UE) 2021/808](https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX%3A32021R0808).

## Exemplos reprodutíveis

- `ich_limits(0.05, 0.005)` gera `DL=0.33` e `QL=1.0`.
- `gaussian_decision_limit(10,0.5,0.05,0.05)` gera
  `CCα≈10.8224` e `CCβ≈11.6449`.
- `test_limits.py` contém verificações numéricas de cada fluxo.

## Limitações comuns

- Nenhuma fórmula compensa preparo de amostras inadequado ou efeito de
  matriz não tratado.
- Desvio-padrão estimado com poucas réplicas é instável.
- Resultados censurados/truncados podem invalidar os pressupostos
  das fórmulas para branco.
- Os limites devem ser avaliados com dados do **procedimento analítico**
  e não apenas do equipamento, quando o objetivo inclui preparo.
- A aceitação de um método depende de critérios analíticos e regulatórios
  escolhidos **antes** da avaliação.
