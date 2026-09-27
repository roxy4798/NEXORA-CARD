# Binance-Inspired Simulated Liquidation Price Model

## 1. Overview & Disclaimer

> **IMPORTANT DISCLAIMER**:
> This application is a simulation / paper-trade system. No real Binance order, account, or position exists.
> The liquidation price calculated here is a **Simulated Liquidation Price** based on a **Binance-inspired simulated liquidation model**.
> It must **NOT** be described as Binance's actual liquidation formula. The simulator does not have the user's real Binance wallet balance, other positions, maintenance margin state, or account-level information required for an actual Cross Margin liquidation calculation.

---

## 2. Theoretical Motivation & Mechanics

In Binance USDⓈ-M Futures, liquidation occurs when:
$$\text{Margin Ratio} = \frac{\text{Maintenance Margin}}{\text{Margin Balance}} \ge 100\%$$

When a user specifies a simulated **Margin Ratio ($MR\%$)** (e.g., $8.29\%$):
1. **Implied Margin Balance**:
   $$\text{Margin Balance} = \frac{\text{Maintenance Margin}}{MR / 100}$$
2. **Available Loss Buffer**:
   $$\text{Buffer} = \text{Margin Balance} - \text{Maintenance Margin} = \text{Maintenance Margin} \times \left( \frac{100 - MR}{MR} \right)$$
3. **Relation to Position Size**:
   Since $\text{Maintenance Margin} = \text{Position Size} \times \text{MMR}$, the loss buffer as a fraction of position size is:
   $$\text{Adverse Price Movement Fraction} = \frac{\text{Buffer}}{\text{Position Size}} = \text{MMR} \times \left( \frac{100 - MR}{MR} \right)$$
4. **Leverage Scaling**:
   The Maintenance Margin Rate ($\text{MMR}$) scales inversely with leverage:
   $$\text{MMR} = \frac{k}{L}$$
   Where $k \approx 0.433889434$ is the risk factor calibrated to Binance Futures leverage brackets ($L = 20, MR = 8.29\% \implies \text{adverse fraction} = 0.24$ or $24\%$).

---

## 3. Mathematical Formula

Let:
- $P_{\text{entry}}$ = Entry Price ($> 0$, Decimal)
- $L$ = Leverage ($> 0$, Decimal)
- $MR$ = Margin Ratio in percent ($0 \le MR \le 100$, Decimal)
- $\text{MMR} = \frac{k}{L}$
- $\Delta = \text{MMR} \times \left( \frac{100 - MR}{MR} \right)$

### 3.1 For LONG Positions
The position suffers losses when the market drops ($P_{\text{liq}} < P_{\text{entry}}$):

$$P_{\text{liq, LONG}} = P_{\text{entry}} \times (1 - \Delta)$$
*(Clamped to `tick_size` if $\le 0$)*

For $P_{\text{entry}} = 0.0140000$, $L = 20$, $MR = 8.29\%$:
$$\Delta = 0.24 \implies P_{\text{liq}} = 0.0140000 \times (1 - 0.24) = 0.0106400$$

### 3.2 For SHORT Positions
The position suffers losses when the market rises ($P_{\text{liq}} > P_{\text{entry}}$):

$$P_{\text{liq, SHORT}} = P_{\text{entry}} \times (1 + \Delta)$$

---

## 4. Safety Bounds and Numerical Guarantees

1. **Non-negativity & Lower Bound**:
   - If calculated $P_{\text{liq, LONG}} \le 0$, the model clamps to the symbol's `tick_size` (e.g. $0.0000001$).
2. **Determinism**:
   - Zero randomness or hidden state. Same parameters always yield identical quantized price.
3. **Monotonicity**:
   - Higher $MR$ reduces the loss buffer, moving $P_{\text{liq}}$ closer to $P_{\text{entry}}$.
   - Higher leverage reduces $\text{MMR}$ margin requirements, scaling liquidation distance appropriately.
