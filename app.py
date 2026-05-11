import streamlit as st
import pandas as pd
import numpy as np
import os
from datetime import datetime
import plotly.graph_objects as go
import plotly.express as px

# =========================================================
# CONFIG
# =========================================================

st.set_page_config(
    page_title="Edge Discovery Trading System",
    layout="wide"
)

FILE_NAME = "trading_journal.csv"

STARTING_CAPITAL = 140

REQUIRED_COLS = [
    "Trade #",
    "Date",
    "Coin",
    "Direction",
    "Entry",
    "Cost",
    "Qty",
    "Risk %",
    "RRR",
    "SL",
    "TP",
    "Mode",
    "Trend",
    "Setup",
    "Regime",
    "Support",
    "Resistance",
    "Emotion",
    "Score",
    "Mistake",
    "Exit",
    "PnL",
    "Status"
]

# =========================================================
# DATA FUNCTIONS
# =========================================================

def load_data():

    if not os.path.exists(FILE_NAME):

        df = pd.DataFrame(columns=REQUIRED_COLS)
        df.to_csv(FILE_NAME, index=False)

        return df

    df = pd.read_csv(FILE_NAME)

    # Auto add missing columns
    for col in REQUIRED_COLS:
        if col not in df.columns:
            df[col] = ""

    # Numeric conversion
    numeric_cols = [
        "Entry", "Cost", "Qty",
        "Risk %", "RRR",
        "SL", "TP",
        "Support", "Resistance",
        "Exit", "PnL",
        "Score"
    ]

    for col in numeric_cols:
        df[col] = pd.to_numeric(
            df[col],
            errors="coerce"
        ).fillna(0)

    return df


def save_data(df):
    df.to_csv(FILE_NAME, index=False)


# =========================================================
# TRADE SCORING ENGINE
# =========================================================

def score_trade(
    trend,
    setup,
    entry,
    support,
    resistance,
    sl,
    rrr
):

    score = 10
    mistakes = []

    # Trend alignment
    if trend == "Uptrend" and entry < support:
        score -= 2
        mistakes.append("Against Trend")

    if trend == "Downtrend" and entry > resistance:
        score -= 2
        mistakes.append("Against Trend")

    # Breakout quality
    if setup == "Breakout" and entry < resistance:
        score -= 1
        mistakes.append("Weak Breakout")

    # RR
    if rrr < 2:
        score -= 2
        mistakes.append("Low RR")

    # SL quality
    sl_dist = abs(entry - sl)

    if sl_dist < entry * 0.002:
        score -= 1
        mistakes.append("SL Too Tight")

    if sl_dist > entry * 0.1:
        score -= 1
        mistakes.append("SL Too Wide")

    grade = (
        "A" if score >= 8
        else "B" if score >= 6
        else "C" if score >= 4
        else "D"
    )

    return score, mistakes, grade


# =========================================================
# LOAD DATA
# =========================================================

df = load_data()

# =========================================================
# PORTFOLIO ENGINE
# =========================================================

closed_trades = df[df["Status"] == "Closed"].copy()

total_pnl = (
    closed_trades["PnL"].sum()
    if not closed_trades.empty
    else 0
)

current_equity = STARTING_CAPITAL + total_pnl

trade_capital = current_equity * 0.5

open_trades = df[df["Status"] == "Open"]

open_exposure = (
    open_trades["Cost"].sum()
    if not open_trades.empty
    else 0
)

# =========================================================
# SIDEBAR
# =========================================================

st.sidebar.title("💼 Portfolio")

st.sidebar.metric(
    "Current Equity",
    f"${current_equity:,.2f}",
    f"{total_pnl:+.2f}"
)

st.sidebar.metric(
    "Next Trade Allocation",
    f"${trade_capital:,.2f}"
)

st.sidebar.metric(
    "Open Exposure",
    f"${open_exposure:,.2f}"
)

st.sidebar.metric(
    "Open Trades",
    len(open_trades)
)

if open_exposure > current_equity:
    st.sidebar.error("⚠️ Overexposed")

elif open_exposure > current_equity * 0.5:
    st.sidebar.warning("⚠️ High Exposure")

else:
    st.sidebar.success("✅ Exposure Healthy")

# =========================================================
# TABS
# =========================================================

tab1, tab2, tab3 = st.tabs([
    "🆕 New Trade",
    "🏁 Close Trade",
    "📊 Edge Discovery"
])

# =========================================================
# TAB 1 — NEW TRADE
# =========================================================

with tab1:

    st.title("🆕 New Trade")

    mode = st.radio(
        "SL Mode",
        ["Auto SL", "Manual SL"],
        horizontal=True
    )

    direction = st.radio(
        "Direction",
        ["Long", "Short"],
        horizontal=True
    )

    col1, col2 = st.columns(2)

    with col1:

        coin = st.text_input(
            "Coin",
            "BTCUSDT"
        ).upper()

        entry = st.number_input(
            "Entry Price",
            min_value=0.0,
            value=1.0,
            format="%.8f"
        )

        risk_pct = st.number_input(
            "Risk %",
            min_value=0.1,
            value=1.0
        )

        rrr = st.selectbox(
            "R:R",
            [2, 3, 5]
        )

    with col2:

        st.info(
            f"Auto Capital Allocation: ${trade_capital:,.2f}"
        )

        cost = trade_capital

        trend = st.selectbox(
            "Trend",
            ["Uptrend", "Downtrend", "Range"]
        )

        setup = st.selectbox(
            "Setup",
            ["Breakout", "Pullback", "Reversal", "SMC/ICT"]
        )

    # =====================================================
    # MARKET REGIME
    # =====================================================

    market_regime = st.selectbox(
        "Market Regime",
        [
            "Trending Bullish",
            "Trending Bearish",
            "Range/Choppy",
            "High Volatility",
            "Low Volatility",
            "Risk-Off"
        ]
    )

    # =====================================================
    # SUPPORT RESISTANCE
    # =====================================================

    c1, c2 = st.columns(2)

    with c1:

        support = st.number_input(
            "Support",
            value=entry * 0.95,
            format="%.8f"
        )

    with c2:

        resistance = st.number_input(
            "Resistance",
            value=entry * 1.05,
            format="%.8f"
        )

    # =====================================================
    # EMOTION
    # =====================================================

    emotion = st.selectbox(
        "Emotion",
        [
            "Calm",
            "Disciplined",
            "FOMO",
            "Fearful",
            "Greedy",
            "Revenge"
        ]
    )

    # =====================================================
    # RISK ENGINE
    # =====================================================

    risk_amount = cost * (risk_pct / 100)

    if mode == "Auto SL":

        qty = cost / entry if entry > 0 else 0

        sl = (
            entry - (risk_amount / qty)
            if qty > 0
            else 0
        )

        if direction == "Long":
            tp = entry + ((entry - sl) * rrr)
        else:
            tp = entry - ((entry - sl) * rrr)

    else:

        sl = st.number_input(
            "Manual SL",
            value=entry * 0.95,
            format="%.8f"
        )

        sl_dist = abs(entry - sl)

        qty = (
            risk_amount / sl_dist
            if sl_dist > 0
            else 0
        )

        if direction == "Long":
            tp = entry + (sl_dist * rrr)
        else:
            tp = entry - (sl_dist * rrr)

    # =====================================================
    # TRADE SCORE
    # =====================================================

    score, mistakes, grade = score_trade(
        trend,
        setup,
        entry,
        support,
        resistance,
        sl,
        rrr
    )

    # =====================================================
    # LIVE PREVIEW
    # =====================================================

    st.subheader("📊 Trade Preview")

    p1, p2, p3, p4 = st.columns(4)

    p1.metric("Quantity", f"{qty:.4f}")
    p2.metric("SL", f"{sl:.4f}")
    p3.metric("TP", f"{tp:.4f}")
    p4.metric("Trade Score", f"{score}/10")

    if mistakes:
        for m in mistakes:
            st.warning(m)

    else:
        st.success("✅ High Quality Setup")
    # =====================================================
    # ESTIMATED OUTCOME
    # =====================================================

if direction == "Long":

    est_profit = (tp - entry) * qty
    est_loss = (entry - sl) * qty

else:

    est_profit = (entry - tp) * qty
    est_loss = (sl - entry) * qty

# Risk reward amount
rr_money = (
    est_profit / est_loss
    if est_loss > 0
    else 0
)

st.subheader("💰 Estimated Outcome")

e1, e2, e3 = st.columns(3)

e1.metric(
    "Estimated Profit @ TP",
    f"${est_profit:.2f}"
)

e2.metric(
    "Estimated Loss @ SL",
    f"-${est_loss:.2f}"
)

e3.metric(
    "Real RR",
    f"1:{rr_money:.2f}"
)

# =====================================================
# VISUAL TRADE HEALTH
# =====================================================

if rr_money >= 3:
    st.success("🔥 Excellent Risk/Reward")

elif rr_money >= 2:
    st.success("✅ Good Trade Structure")

elif rr_money >= 1.5:
    st.warning("⚠️ Acceptable but not ideal")

else:
    st.error("❌ Poor Risk/Reward")

    # =====================================================
    # SAVE TRADE
    # =====================================================

    if st.button("🚀 Save Trade"):

        new_trade = {
            "Trade #": len(df) + 1,
            "Date": datetime.now(),
            "Coin": coin,
            "Direction": direction,
            "Entry": entry,
            "Cost": cost,
            "Qty": qty,
            "Risk %": risk_pct,
            "RRR": rrr,
            "SL": sl,
            "TP": tp,
            "Mode": mode,
            "Trend": trend,
            "Setup": setup,
            "Regime": market_regime,
            "Support": support,
            "Resistance": resistance,
            "Emotion": emotion,
            "Score": score,
            "Mistake": ", ".join(mistakes),
            "Exit": 0,
            "PnL": 0,
            "Status": "Open"
        }

        df = pd.concat(
            [df, pd.DataFrame([new_trade])],
            ignore_index=True
        )

        save_data(df)

        st.success("Trade Saved")

# =========================================================
# TAB 2 — CLOSE TRADE
# =========================================================

with tab2:

    st.title("🏁 Close Trade")

    open_trades = df[df["Status"] == "Open"]

    if open_trades.empty:

        st.info("No Open Trades")

    else:

        open_trades["label"] = (
            open_trades["Trade #"].astype(str)
            + " | "
            + open_trades["Coin"]
        )

        selected = st.selectbox(
            "Select Trade",
            open_trades["label"]
        )

        trade_idx = open_trades[
            open_trades["label"] == selected
        ].index[0]

        trade = df.loc[trade_idx]

        exit_price = st.number_input(
            "Exit Price",
            value=float(trade["TP"]),
            format="%.8f"
        )

        exit_reason = st.selectbox(
            "Exit Reason",
            [
                "Hit TP",
                "Hit SL",
                "Manual",
                "Break Even"
            ]
        )

        if st.button("✅ Close Trade"):

            if trade["Direction"] == "Long":

                pnl = (
                    (exit_price - trade["Entry"])
                    * trade["Qty"]
                )

            else:

                pnl = (
                    (trade["Entry"] - exit_price)
                    * trade["Qty"]
                )

            df.at[trade_idx, "Exit"] = exit_price
            df.at[trade_idx, "PnL"] = round(pnl, 2)
            df.at[trade_idx, "Status"] = "Closed"

            save_data(df)

            st.success(f"Trade Closed | PnL: ${pnl:.2f}")

# =========================================================
# TAB 3 — EDGE DISCOVERY
# =========================================================

with tab3:

    st.title("📊 Edge Discovery Dashboard")

    closed = df[df["Status"] == "Closed"].copy()

    if closed.empty:

        st.warning("No Closed Trades Yet")

    else:

        # =================================================
        # FILTERS
        # =================================================

        st.sidebar.subheader("📌 Analytics Filters")

        selected_setup = st.sidebar.multiselect(
            "Setup",
            options=closed["Setup"].dropna().unique(),
            default=closed["Setup"].dropna().unique()
        )

        selected_emotion = st.sidebar.multiselect(
            "Emotion",
            options=closed["Emotion"].dropna().unique(),
            default=closed["Emotion"].dropna().unique()
        )

        selected_coin = st.sidebar.multiselect(
            "Coin",
            options=closed["Coin"].dropna().unique(),
            default=closed["Coin"].dropna().unique()
        )

        filtered = closed[
            (closed["Setup"].isin(selected_setup)) &
            (closed["Emotion"].isin(selected_emotion)) &
            (closed["Coin"].isin(selected_coin))
        ]

        # =================================================
        # EQUITY CURVE
        # =================================================

        filtered = filtered.sort_values("Date")

        filtered["Equity"] = filtered["PnL"].cumsum()

        filtered["Peak"] = filtered["Equity"].cummax()

        filtered["Drawdown"] = (
            filtered["Equity"]
            - filtered["Peak"]
        )

        # =================================================
        # CORE METRICS
        # =================================================

        total_pnl = filtered["PnL"].sum()

        win_rate = (
            filtered["PnL"] > 0
        ).mean()

        avg_win = filtered[
            filtered["PnL"] > 0
        ]["PnL"].mean()

        avg_loss = filtered[
            filtered["PnL"] < 0
        ]["PnL"].mean()

        expectancy = (
            (win_rate * avg_win)
            + ((1 - win_rate) * avg_loss)
        )

        profit_factor = (
            filtered[filtered["PnL"] > 0]["PnL"].sum()
            /
            abs(filtered[filtered["PnL"] < 0]["PnL"].sum())
            if abs(filtered[filtered["PnL"] < 0]["PnL"].sum()) > 0
            else 0
        )

        max_dd = filtered["Drawdown"].min()

        # =================================================
        # METRICS UI
        # =================================================

        m1, m2, m3, m4 = st.columns(4)

        m1.metric(
            "Total PnL",
            f"${total_pnl:.2f}"
        )

        m2.metric(
            "Win Rate",
            f"{win_rate*100:.1f}%"
        )

        m3.metric(
            "Expectancy",
            f"{expectancy:.2f}"
        )

        m4.metric(
            "Profit Factor",
            f"{profit_factor:.2f}"
        )

        # =================================================
        # EQUITY CURVE
        # =================================================

        st.subheader("📈 Equity Curve")

        fig = go.Figure()

        fig.add_trace(
            go.Scatter(
                x=filtered["Date"],
                y=filtered["Equity"],
                name="Equity"
            )
        )

        fig.add_trace(
            go.Scatter(
                x=filtered["Date"],
                y=filtered["Peak"],
                name="Peak",
                line=dict(dash="dash")
            )
        )

        st.plotly_chart(
            fig,
            use_container_width=True
        )

        # =================================================
        # DRAWDOWN
        # =================================================

        st.subheader("📉 Drawdown")

        dd_fig = go.Figure()

        dd_fig.add_trace(
            go.Scatter(
                x=filtered["Date"],
                y=filtered["Drawdown"],
                fill="tozeroy",
                name="Drawdown"
            )
        )

        st.plotly_chart(
            dd_fig,
            use_container_width=True
        )

        # =================================================
        # STRATEGY COMPARISON
        # =================================================

        st.subheader("📈 Strategy Equity Comparison")

        strategy_equity = []

        for s in filtered["Setup"].dropna().unique():

            temp = filtered[
                filtered["Setup"] == s
            ].copy()

            temp = temp.sort_values("Date")

            temp["StrategyEquity"] = (
                temp["PnL"].cumsum()
            )

            temp["Strategy"] = s

            strategy_equity.append(temp)

        if strategy_equity:

            eq_df = pd.concat(strategy_equity)

            fig2 = px.line(
                eq_df,
                x="Date",
                y="StrategyEquity",
                color="Strategy"
            )

            st.plotly_chart(
                fig2,
                use_container_width=True
            )

        # =================================================
        # MARKET REGIME
        # =================================================

        st.subheader("🌍 Market Regime Analysis")

        regime_perf = filtered.groupby(
            "Regime"
        )["PnL"].agg(
            Trades="count",
            TotalPnL="sum",
            AvgPnL="mean"
        )

        regime_perf["WinRate"] = (
            filtered.groupby("Regime")["PnL"]
            .apply(lambda x: (x > 0).mean() * 100)
        )

        st.dataframe(
            regime_perf,
            use_container_width=True
        )

        # =================================================
        # STRATEGY VS REGIME
        # =================================================

        st.subheader("🧠 Strategy vs Regime")

        matrix = pd.pivot_table(
            filtered,
            values="PnL",
            index="Setup",
            columns="Regime",
            aggfunc="mean"
        )

        st.dataframe(
            matrix,
            use_container_width=True
        )

        # =================================================
        # EXECUTIVE CONSULTANT
        # =================================================

        st.subheader("🧠 Executive Consultant")

        # Best setup
        best_setup = (
            filtered.groupby("Setup")["PnL"]
            .sum()
            .sort_values(ascending=False)
        )

        if not best_setup.empty:

            st.success(
                f"🏆 Strongest Edge: {best_setup.index[0]}"
            )

        # Worst emotion
        emotion_perf = (
            filtered.groupby("Emotion")["PnL"]
            .mean()
            .sort_values()
        )

        if not emotion_perf.empty:

            st.warning(
                f"⚠️ Weakest Emotion: {emotion_perf.index[0]}"
            )

        # Current health
        if max_dd < -500:

            st.error(
                "⚠️ Drawdown expanding. Reduce risk."
            )

        elif expectancy > 0:

            st.success(
                "✅ System expectancy positive."
            )

        else:

            st.warning(
                "⚠️ Negative expectancy. Review setups."
            )

        # =================================================
        # RAW DATA
        # =================================================

        st.subheader("📋 Trade Database")

        st.dataframe(
            filtered,
            use_container_width=True
        )

# =========================================================
# DANGER ZONE
# =========================================================

st.sidebar.markdown("---")

with st.sidebar.expander("🧹 Data Management"):

    if st.button("Delete All Trade History"):

        if os.path.exists(FILE_NAME):

            os.remove(FILE_NAME)

            st.rerun()
