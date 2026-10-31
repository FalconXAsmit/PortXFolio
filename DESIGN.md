---
name: Portfolix Bright Design System
colors:
  surface: '#FFFFFF'
  surface-dim: '#F8FAFC'
  surface-bright: '#FFFFFF'
  surface-container-lowest: '#FFFFFF'
  surface-container-low: '#F8FAFC'
  surface-container: '#FFFFFF'
  surface-container-high: '#F1F5F9'
  surface-container-highest: '#E2E8F0'
  on-surface: '#0F172A'
  on-surface-variant: '#475569'
  outline: '#94A3B8'
  outline-variant: '#E2E8F0'
  primary: '#0284C7'
  on-primary: '#FFFFFF'
  primary-container: '#E0F2FE'
  on-primary-container: '#0284C7'
  secondary: '#10B981'
  on-secondary: '#FFFFFF'
  secondary-container: '#D1FAE5'
  on-secondary-container: '#047857'
  tertiary: '#8B5CF6'
  error: '#F43F5E'
  on-error: '#FFFFFF'
  warning: '#F59E0B'
  background: '#F8FAFC'
  on-background: '#0F172A'
typography:
  headline-xl:
    fontFamily: Plus Jakarta Sans, Inter, sans-serif
    fontSize: 32px
    fontWeight: '800'
    lineHeight: 40px
    letterSpacing: -0.025em
  headline-lg:
    fontFamily: Plus Jakarta Sans, Inter, sans-serif
    fontSize: 22px
    fontWeight: '700'
    lineHeight: 30px
    letterSpacing: -0.02em
  headline-md:
    fontFamily: Plus Jakarta Sans, Inter, sans-serif
    fontSize: 18px
    fontWeight: '600'
    lineHeight: 26px
    letterSpacing: -0.015em
  financial-xl:
    fontFamily: JetBrains Mono, monospace
    fontSize: 26px
    fontWeight: '700'
    lineHeight: 34px
    letterSpacing: -0.025em
  financial-lg:
    fontFamily: JetBrains Mono, monospace
    fontSize: 18px
    fontWeight: '600'
    lineHeight: 24px
    letterSpacing: -0.015em
  financial-md:
    fontFamily: JetBrains Mono, monospace
    fontSize: 14px
    fontWeight: '500'
    lineHeight: 20px
  financial-sm:
    fontFamily: JetBrains Mono, monospace
    fontSize: 11px
    fontWeight: '500'
    lineHeight: 15px
  label-caps:
    fontFamily: JetBrains Mono, monospace
    fontSize: 10px
    fontWeight: '700'
    lineHeight: 14px
    letterSpacing: 0.08em
---

# Portfolix - Bright Trading Market Dashboard Design System

The **Portfolix Bright Design System** blends institutional financial depth with a luminous, daylight-ready aesthetic. Inspired by modern high-density trading terminals, Portfolix delivers razor-sharp legibility, crisp elevation tiers, and deterministic tabular typography.

## Core Philosophy: High Contrast, Daylight Clarity & Zero Cognitive Fatigue

1. **Luminous Matching Canvas (`#F0F7FD` to `#F1F5F9` Base, `#FFFFFF` Translucent Surfaces):**
   A soft, light-tinted atmospheric backdrop bathed in brand-matching ambient orbs (Sky Blue `#0284C7`, Mint Emerald `#10B981`, and Violet `#8B5CF6`). Delivers visual warmth, eliminates eye strain, and provides high-contrast foundation for floating glassmorphic white cards. Supports dynamic matching theme switching (Sky, Mint, Violet).

2. **Precise Institutional Color Semantics:**
   - **Portfolix Sky Cyan (`#0284C7`):** Primary interaction vectors, active tabs, crosshairs, and key technical anchors.
   - **Bullish Emerald (`#10B981` / `#047857` text on badges):** Call accumulation, positive alpha, buy orders, and positive P&L.
   - **Bearish Rose (`#F43F5E` / `#BE123C` text on badges):** Put premiums, downside drawdowns, sell orders, and negative P&L.
   - **Derivatives & Greeks Violet (`#8B5CF6` / `#A855F7`):** Delta/gamma ratios, options open interest, and ML alpha forecast tracks.
   - **Warning Amber (`#F59E0B` / `#B45309`):** Volatility alerts, order pending states, and risk thresholds.

3. **Tabular Zero-Jitter Figures:**
   All quantitative figures (quotes, quantities, Greeks, P&L, timestamps) use `JetBrains Mono` with fixed tabular numbers (`font-variant-numeric: tabular-nums`) to completely eliminate layout vibration during rapid price streaming.

## Surface Elevation Stack

- **Level 0 (Canvas Base):** Light slate `#F8FAFC` with a micro-grid background (`radial-gradient(#E2E8F0 1px, transparent 1px) 24px 24px`).
- **Level 1 (Card & Module Surfaces):** Pure `#FFFFFF` with 1px border `#E2E8F0`, rounded 16px radius, and soft elevation `0 1px 3px 0 rgba(0, 0, 0, 0.04)`.
- **Level 2 (Modals & Command Dialogs):** Pure `#FFFFFF` on a soft slate scrim (`rgba(15, 23, 42, 0.40)` with backdrop blur), elevated by `0 20px 30px -10px rgba(15, 23, 42, 0.12)`.
- **Level 3 (Tooltips & Hover Blurs):** Crisp white panels with border `#BAE6FD` and `0 4px 12px rgba(15, 23, 42, 0.08)`.

## Signature Architectural Modules

1. **Market Flow & Options Ratio:** Real-time visual comparison of Bullish Call accumulation vs Bearish Put premiums with live Greeks (Delta, Gamma, Theta, Vega) telemetry on a light card.
2. **Deterministic Ticker Stream:** Top ribbon with live latency measurement (`⚡ 9ms`), pulsing connection beacon, and continuous quote stream with emerald/rose price change pills.
3. **Multi-Timeframe Candlestick Engine:** Lightweight charts styled for bright mode with clean white background, `#F1F5F9` grid lines, emerald up-candles, rose down-candles, and sky blue crosshairs.
4. **Markowitz Efficient Frontier & MPT Solver:** Mean-variance optimization suite computing tangency portfolios, risk parity allocations, and rebalance delta orders.
5. **Deterministic Backtesting Lab:** Historical simulation engine calculating CAGR, Sharpe, Sortino, Calmar, and monthly return matrices.
6. **Temporal OOS Alpha Forecaster:** Out-of-sample machine learning forecasts with 95% confidence cones and directional hit rates.
