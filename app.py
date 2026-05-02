import streamlit as st
import pandas as pd
import os
from datetime import datetime
import plotly.express as px

FILE_NAME = "trading_journal.csv"

# -------------------------------
# INIT
# -------------------------------
def load_data():
    if not os.path.exists(FILE_NAME):
        df = pd.DataFrame(columns=[
            "Trade #","Date","Coin","Entry Price","Cost","Quantity",
            "Risk %","L:P","Take Profit","Stop Loss","R:R",
            "Exit Price","PnL","Win/Lose",
            "Emotion","Strategy","Lesson Learned","Status"
        ])
        df.to_csv(FILE_NAME, index=False)
    return pd.read_csv(FILE_NAME)

def save_data(df):
    df.to_csv(FILE_NAME, index=False)

df = load_data()

st.set_page_config(layout="wide")
st.title("📊 Pro Trading Journal")

# -------------------------------
# TABS (Mobile Friendly)
# -------------------------------
tab1, tab2, tab3 = st.tabs(["➕ New Trade", "📡 Live Trades", "📊 Dashboard"])

# ===============================
# TAB 1 - NEW TRADE
# ===============================
with tab1:
    st.subheader("Add New Trade")

    with st.form("trade_form"):
        col1, col2 = st.columns(2)

        with col1:
            date = st.datetime_input("Date", datetime.now())
            coin = st.text_input("Coin")
            entry = st.number_input("Entry Price", min_value=0.0)
            account_size = st.number_input("Account Size", min_value=0.0)
            risk_pct = st.number_input("Risk % per trade", value=1.0)

        with col2:
            tp = st.number_input("Take Profit", min_value=0.0)
            sl = st.number_input("Stop Loss", min_value=0.0)
            emotion = st.selectbox("Emotion", ["Calm","Greedy","Fearful","Fomo","Disciplined"])
            strategy = st.text_input("Strategy (e.g. Breakout, Pullback)")

        lesson = st.text_area("Lesson Learned")

        submitted = st.form_submit_button("Save Trade")

        if submitted and entry > 0 and sl > 0:
            risk_amount = account_size * (risk_pct / 100)
            risk_per_unit = abs(entry - sl)
            qty = risk_amount / risk_per_unit if risk_per_unit != 0 else 0

            rr = (tp - entry) / (entry - sl) if sl != 0 else 0

            new_trade = {
                "Trade #": len(df)+1,
                "Date": date,
                "Coin": coin,
                "Entry Price": entry,
                "Cost": account_size,
                "Quantity": qty,
                "Risk %": risk_pct,
                "L:P": "",
                "Take Profit": tp,
                "Stop Loss": sl,
                "R:R": rr,
                "Exit Price": "",
                "PnL": "",
                "Win/Lose": "",
                "Emotion": emotion,
                "Strategy": strategy,
                "Lesson Learned": lesson,
                "Status": "Open"
            }

            df = pd.concat([df, pd.DataFrame([new_trade])], ignore_index=True)
            save_data(df)

            st.success(f"Trade added | Qty: {qty:.4f} | R:R: {rr:.2f}")

# ===============================
# TAB 2 - LIVE TRADES
# ===============================
with tab2:
    st.subheader("Live Trades")

    live_df = df[df["Status"] == "Open"]

    if not live_df.empty:
        for i, row in live_df.iterrows():
            with st.container():
                st.markdown(f"### {row['Coin']}")
                col1, col2, col3 = st.columns(3)

                col1.write(f"Entry: {row['Entry Price']}")
                col2.write(f"TP: {row['Take Profit']}")
                col3.write(f"SL: {row['Stop Loss']}")

                exit_price = st.number_input("Exit Price", key=f"exit{i}")
                exit_type = st.selectbox("Exit Type", ["TP","SL","Manual"], key=f"type{i}")

                if st.button("Close Trade", key=f"close{i}"):
                    pnl = (exit_price - row["Entry Price"]) * row["Quantity"]
                    result = "Win" if pnl > 0 else "Lose"

                    df.loc[i, "Exit Price"] = exit_price
                    df.loc[i, "PnL"] = pnl
                    df.loc[i, "Win/Lose"] = result
                    df.loc[i, "Status"] = "Closed"

                    save_data(df)
                    st.success("Trade Closed")
    else:
        st.info("No open trades")

# ===============================
# TAB 3 - DASHBOARD
# ===============================
with tab3:
    st.subheader("Performance Dashboard")

    closed = df[df["Status"] == "Closed"].copy()

    if not closed.empty:
        closed["PnL"] = pd.to_numeric(closed["PnL"], errors="coerce")
        closed["Date"] = pd.to_datetime(closed["Date"])
        closed = closed.sort_values("Date")

        total_pnl = closed["PnL"].sum()
        win_rate = (closed["Win/Lose"] == "Win").mean() * 100

        avg_win = closed[closed["PnL"] > 0]["PnL"].mean()
        avg_loss = closed[closed["PnL"] < 0]["PnL"].mean()

        expectancy = (win_rate/100 * avg_win) + ((1-win_rate/100) * avg_loss)

        profit_factor = abs(closed[closed["PnL"] > 0]["PnL"].sum() /
                            closed[closed["PnL"] < 0]["PnL"].sum())

        closed["CumPnL"] = closed["PnL"].cumsum()
        drawdown = (closed["CumPnL"].cummax() - closed["CumPnL"]).max()

        col1, col2, col3 = st.columns(3)
        col1.metric("Total PnL", f"{total_pnl:.2f}")
        col2.metric("Win Rate", f"{win_rate:.1f}%")
        col3.metric("Expectancy", f"{expectancy:.2f}")

        col4, col5 = st.columns(2)
        col4.metric("Profit Factor", f"{profit_factor:.2f}")
        col5.metric("Max Drawdown", f"{drawdown:.2f}")

        # Equity Curve
        fig = px.line(closed, x="Date", y="CumPnL", title="Equity Curve")
        st.plotly_chart(fig, use_container_width=True)

        # Emotion
        emo = closed.groupby("Emotion")["PnL"].sum().reset_index()
        fig2 = px.bar(emo, x="Emotion", y="PnL", title="Emotion Impact")
        st.plotly_chart(fig2, use_container_width=True)

        # Strategy
        strat = closed.groupby("Strategy")["PnL"].sum().reset_index()
        fig3 = px.bar(strat, x="Strategy", y="PnL", title="Strategy Performance")
        st.plotly_chart(fig3, use_container_width=True)

    else:
        st.info("No closed trades yet")

# ===============================
# HISTORY TABLE
# ===============================
st.subheader("Full Trade History")
st.dataframe(df, use_container_width=True)