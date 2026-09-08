# Phase 5/6 Specification — Cross-Domain Prioritization Framework

> **Status: SPECIFICATION ONLY — NOT YET BUILDABLE**
>
> This section documents the intended decision logic for Phases 5–6, once the exposure mapping (Phase 2), financial transmission model (Phase 3), and Monte Carlo/CFaR engine (Phases 4–5) exist. It is recorded now so that future schema and module design does not foreclose it, but **no code should be written against this section in the current MVP**.

---

## 10.1.1 The Unifying Principle

Hedging, financing, and capital allocation are three different actions available in response to the same underlying diagnostic: where is the company's financial resilience weakest relative to what a correlated shock could do to it.

All three domains draw on the same core inputs — Cash-Flow-at-Risk (CFaR), Enterprise Value sensitivity, and proximity to a hard constraint — but each asks a different question of them.

| Domain | Core question | What "priority" means |
|---|---|---|
| **Hedging** | Which risk should be neutralized first? | Highest expected damage x least existing protection |
| **Financing** | Which balance-sheet structure should be fixed first? | Highest refinancing/covenant fragility x highest cost of inaction |
| **Capital Allocation** | Which use of a marginal dollar creates the most value per unit of risk consumed? | Highest risk-adjusted return, penalized by how much resilience it consumes |

---

## 10.1.2 Common Inputs Required

> All three domains depend on these. They must exist before any of the formulas below are computable — they are the **output of Phases 2–5**, not this phase.

- **CFaR_i** — Cash-Flow-at-Risk contribution of risk factor i (e.g. commodity, FX, rate), at a chosen confidence level (e.g. 95%), expressed in currency terms.
- **dEV/dM** — sensitivity of Enterprise Value to a unit move in a given financial metric M (EBITDA, FCF, Debt, Liquidity, ROIC), derived from the Phase 3 transmission model.
- **Proximity_i** — how close a given constraint (covenant threshold, minimum cash buffer, credit-rating trigger) sits to breach, defined as:

  Proximity_i = 1 / ((Current buffer - Minimum required buffer) / Minimum required buffer)

  Smaller headroom -> larger Proximity value -> higher urgency.

- **Correlation_i** — how correlated risk factor i is with the others (from Phase 4 Monte Carlo/correlation modeling). Diversifiable risk should be weighted down relative to systemic/correlated risk that hits multiple metrics simultaneously.

---

## 10.1.3 Hedging Priority Formula

  HedgePriority_i = CFaR_i x Proximity_i x (1 - ExistingHedgeCoverage_i)

- Rank risk factors (commodity, FX, rate — and sub-factors like copper vs. aluminium) by this score, **descending**.
- ExistingHedgeCoverage_i (0 to 1) discounts risks already partially hedged. This is why the hedges stub table (Section 4.3) must eventually carry notional/hedge_ratio per instrument, so this term is computable.
- **Interpretation:** hedge the risk that can do the most cash-flow damage, that the company is closest to being unable to absorb, and that is not already covered.

---

## 10.1.4 Financing Priority Formula

  FinancingPriority_j = RefinancingFragility_j x CostOfInaction_j

Where, for each financing structure element j (e.g. a specific debt tranche, a floating-rate exposure, an upcoming maturity):

- **RefinancingFragility_j** = a composite of:
  - (a) proximity to maturity
  - (b) proportion floating-rate vs. fixed
  - (c) proximity to covenant breach under Phase 5 stress scenarios (Proximity_i applied specifically to debt-related constraints)

- **CostOfInaction_j** = the estimated EV or liquidity impact if this financing structure is left unaddressed and the adverse scenario materializes (dEV/dDebt x expected adverse move, or equivalent for liquidity).

- **Interpretation:** fix the financing structure most likely to become a forced, expensive, or covenant-breaching event under stress, weighted by how damaging that event would actually be.

---

## 10.1.5 Capital Allocation Priority Formula

  AllocationPriority_k = Risk-Adjusted Return_k / Resilience Consumed_k

Where, for each candidate use of capital k (capex project, buyback, debt paydown, cash buffer build, M&A, etc.):

- **Risk-Adjusted Return_k** = expected ROIC or NPV of the allocation, discounted by its own outcome volatility — a Sharpe-like ratio:
  (Expected Return_k - Risk-Free Rate) / sigma(Return_k)

- **Resilience Consumed_k** = the extent to which pursuing k reduces the company's remaining headroom against the constraints tracked in Proximity_i (e.g. a large capex program financed with floating-rate debt consumes more resilience than one financed from existing cash reserves, even at identical ROIC).

- **Interpretation:** prioritize capital uses that generate strong risk-adjusted returns without meaningfully eating into the buffer that protects the company against the correlated shocks already identified as high-priority hedging/financing concerns — capital allocation decisions should be evaluated **jointly with**, not independently of, the hedging and financing priorities from ss10.1.3–10.1.4.

---

## 10.1.6 Why These Three Must Be Evaluated Together, Not Independently

A high-ROIC capital project financed with new floating-rate debt can simultaneously:

- (a) **look attractive** under AllocationPriority, while
- (b) **worsening** RefinancingFragility for that same debt tranche, while
- (c) **increasing** Proximity_i for a liquidity constraint that a hedging decision was trying to protect.

The eventual Phase 6 decision engine must therefore **solve these three priority rankings jointly** — e.g. as a constrained optimization where hedging and financing decisions are treated as inputs that reshape the Proximity and Resilience Consumed terms feeding the capital allocation decision — **not as three independent priority lists computed in isolation**.

> **This joint optimization is explicitly out of scope until Phase 6** and depends on all of Phases 2–5 being complete and validated first.

---

## Schema / Module Design Constraints Implied by This Spec

To avoid foreclosing Phase 5/6 implementation, the following must be preserved in current schema design:

| Current schema element | Why it must remain extensible |
|---|---|
| hedges stub table (Section 4.3) | Must eventually support notional and hedge_ratio per instrument — required for ExistingHedgeCoverage_i |
| Phase 3 transmission model output | Must emit dEV/dM per metric — required by both FinancingPriority and AllocationPriority |
| Phase 4 correlation matrix | Must be accessible at runtime — required for Correlation_i weighting |
| Covenant / constraint tracking | Must carry both current buffer AND minimum required buffer — required for Proximity_i |
| Capital project register | Must carry expected return, return volatility, and financing structure — required for AllocationPriority_k |
