# Noob Trade Quant Methodology

## 1. Executive Summary

Noob Trade uses a historical pattern-matching framework rather than a direct price prediction model.
The core idea is:

1. Select a current chart window for a stock.
2. Compare that window with historical windows of the same timeframe and the same bar length.
3. Rank the most similar historical setups.
4. Inspect what happened in the next 5 trading days after each historical setup.
5. Convert those realized forward outcomes into interpretable reach probabilities.

This makes the output explainable, data-driven, and suitable for decision support.

## 2. Core Data Logic

For each stock and timeframe, the system builds rolling historical windows.

- Timeframe examples: `Daily`, `5 Days`, `Weekly`, `2 Weeks`, `Monthly`
- Window size examples: `20`, `30`, `60` bars
- Matching rule: compare only windows with the same timeframe and the same bar count

So a `DAILY 30-bar setup` is only compared with other historical `DAILY 30-bar` setups.

## 3. Feature Construction

For each historical window, the model stores:

- Price path shape
- Return over the window
- Maximum drawdown
- Volatility
- Indicator snapshot
- Forward 5-day / 10-day / 20-day future statistics

The current factor set is:

- MA
- EMA
- MACD
- BOLL
- RSI
- VOL
- KDJ
- OI
- OBV

Note: `PBV` has been standardized to `OBV`.

## 4. Historical Search Logic

### 4.1 Matching Universe

Given the current window `W_now`, define the candidate set:

\[
\mathcal{H} = \{ W_i : \text{same timeframe, same window size, and } t_i < t_{now} \}
\]

This avoids look-ahead bias because only historical windows ending before the current window are eligible.

### 4.2 Similarity Components

Each candidate is scored by two layers:

1. Indicator similarity
2. Price-path similarity

The displayed similarity score is a blended fit:

\[
\text{DisplayFit}(W_i) = 0.75 \cdot \text{IndicatorFit}(W_i) + 0.25 \cdot \text{PathFit}(W_i)
\]

This is important because we do not only want indicator snapshots to be close; we also want the full bar pattern to resemble the current setup.

### 4.3 Top Historical Bundles

The engine sorts all candidates by descending similarity and selects the top 20 windows:

\[
\{W_{(1)}, W_{(2)}, \dots, W_{(20)}\}
\]

These 20 windows form the historical reference bundle used in the final analysis.

## 5. Indicator Score Logic

For each selected indicator, let:

\[
\text{sim}_j = \text{distance between current factor } j \text{ and historical factor } j
\]

### 5.1 Score Table

#### MA / EMA
- if `sim <= 1%` → score `3`
- if `sim <= 3%` → score `2`
- if `sim <= 5%` → score `1`
- else → `0`

#### MACD / BOLL
- if `sim <= 1%` → score `30`
- if `sim <= 3%` → score `20`
- if `sim <= 5%` → score `10`
- else → `0`

#### RSI / VOL
- if `sim <= 1%` → score `15`
- if `sim <= 3%` → score `10`
- if `sim <= 5%` → score `5`
- else → `0`

#### KDJ / OI / OBV
- if `sim <= 1%` → score `9`
- if `sim <= 3%` → score `6`
- if `sim <= 5%` → score `3`
- else → `0`

### 5.2 Full Score by Factor

\[
S_j^{max} = 
\begin{cases}
3 & j \in \{MA, EMA\} \\
30 & j \in \{MACD, BOLL\} \\
15 & j \in \{RSI, VOL\} \\
9 & j \in \{KDJ, OI, OBV\}
\end{cases}
\]

### 5.3 Weight by Factor

\[
w_j = 
\begin{cases}
1 & j \in \{MA, EMA\} \\
10 & j \in \{MACD, BOLL\} \\
5 & j \in \{RSI, VOL\} \\
3 & j \in \{KDJ, OI, OBV\}
\end{cases}
\]

Total full weight over all 9 factors:

\[
W_{full} = 41
\]

## 6. Fit Ratio

For a user-selected factor subset `J`, the hard-fit ratio is:

\[
\text{FitRatio} = \frac{\sum_{j \in J} S_j}{\sum_{j \in J} S_j^{max}}
\]

This measures how well the selected factor set aligns with the historical candidate.

## 7. OTC + 5 Trading Day Logic

After the top 20 historical windows are found, the model does not only look at the close on day +5.
Instead, it inspects the entire next 5-trading-day path after each matched historical window.

For each historical match, let:

- `P0` = close at the matched historical end date
- `H5` = highest high over the next 5 trading days
- `L5` = lowest low over the next 5 trading days

### 7.1 Maximum Upside Reach

\[
R^{up}_{5d} = \frac{H5 - P0}{P0} \times 100\%
\]

### 7.2 Maximum Downside Reach

\[
R^{down}_{5d} = \frac{L5 - P0}{P0} \times 100\%
\]

This means a stock is counted as having reached `+5%` if it touched that level at any point during the next 5 trading days, even if it later retraced.

## 8. Probability Construction

For the top 20 most similar historical setups, the system calculates the reach probability for each target threshold.

### 8.1 Upside Reach Probability

For threshold `u` in `{1%, 5%, 10%}`:

\[
\Pr(\text{reach } +u\% \text{ within 5D}) = \frac{1}{20} \sum_{k=1}^{20} \mathbf{1}(R^{up}_{5d,k} \ge u)
\]

### 8.2 Downside Reach Probability

For threshold `d` in `{1%, 5%, 10%}`:

\[
\Pr(\text{reach } -d\% \text{ within 5D}) = \frac{1}{20} \sum_{k=1}^{20} \mathbf{1}(R^{down}_{5d,k} \le -d)
\]

Important interpretation:

- Upside and downside probabilities are not complementary.
- Their sum may exceed 100%.
- That is mathematically valid because the same 5-day path may touch both an upside and a downside threshold.

## 9. Final Probability Output

The displayed signal is based on the top-20 historical bundle.

Current main headline output:
- Probability of reaching `+1%` within 5 trading days

Secondary outputs:
- Probability of reaching `+5%`
- Probability of reaching `+10%`
- Probability of reaching `-1%`
- Probability of reaching `-5%`
- Probability of reaching `-10%`

So the front-end message can be interpreted as:

- `90% probability of reaching +1% within 5D`
- `80% probability of reaching +5% within 5D`
- `30% probability of reaching +10% within 5D`

and similarly for downside thresholds.

## 10. Weighting and Penalty Logic

### 10.1 Why Penalty Exists

If the user selects only a very small and low-weight factor subset, the historical match set becomes less informative.
However, the system should not mechanically crush the final probability to unrealistic levels.

So the design principle is:

- Historical similarity ranking stays untouched.
- Penalty only affects the final displayed probability.

### 10.2 Light Adaptive Penalty

Let the selected total factor weight be:

\[
W_{sel} = \sum_{j \in J} w_j
\]

Then:

\[
\text{WeightRatio} = \frac{W_{sel}}{W_{full}}
\]

The final penalty is intentionally mild:

\[
\text{Penalty}(J) = 0.88 + 0.12 \cdot \sqrt{\text{WeightRatio}}
\]

bounded above by `1.0`.

Interpretation:

- High-weight selections: penalty is very close to `1`
- Low-weight selections: only a gentle discount
- The penalty never destroys the signal

### 10.3 Final Probability with Penalty

For any upside or downside threshold probability `p_raw`, the displayed probability is:

\[
p_{final} = p_{raw} \cdot \text{Penalty}(J)
\]

This preserves:

- The relative structure of historical reach probabilities
- The ranking of thresholds
- The interpretability of the bundle

while still acknowledging that weaker factor selections should carry slightly less confidence.

## 11. Why This Method Is Efficient

This approach is efficient because it separates the pipeline into two layers:

1. Historical database layer
   - rolling windows
   - indicators
   - path features
   - forward 5D stats

2. Online inference layer
   - select current factor subset
   - search top 20 historical matches
   - compute threshold reach probabilities
   - apply a light final penalty

So the system is not trying to predict the market from scratch every time.
It is retrieving similar historical states and translating them into forward-risk statistics.

## 12. Interpretation for Presentation

A clean presentation narrative is:

> We do not claim to predict the next closing price.
> Instead, we search the historical database for the 20 most similar setups, inspect what those setups actually did in the following 5 trading days, and convert those outcomes into threshold-based reach probabilities.
> The result is an explainable quant signal grounded in historical analogs.

## 13. Compliance / Disclaimer

This system is a historical signal engine for decision support.
It does not constitute investment advice, portfolio management advice, or a guaranteed forecast.

A formal sentence you can use in the presentation:

> The output is based on historical market data and weighted analysis of similar chart structures. It is intended solely as an analytical decision-support signal and does not constitute any investment or trading advice.
