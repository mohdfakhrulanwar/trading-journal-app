import streamlit as st
import pandas as pd
import os
from datetime import datetime

# --- CONFIGURATION ---
FILE_NAME = "trading_journal.csv"
REQUIRED_COLS = [
    "Trade #", "Date", "Coin", "Entry", "Cost", "Qty",
    "Risk %", "RRR", "SL", "TP", "Mode",
    "Trend", "Setup", "Support", "Resistance", "Emotion",
    "Score", "Mistake", "Exit", "PnL", "Status"
]

# --- DATA HANDLING ---
def load_data():
    if not os.path.exists(FILE_NAME):
        df = pd.DataFrame(columns=REQUIRED_COLS)
        df.to_csv(FILE_NAME, index=False)
        return df
    
    df = pd.read_csv(FILE_NAME)
    
    # Fix for the "TypeError: Invalid value for dtype float64"
    float_cols = ["Entry", "Cost", "Qty", "Risk %", "SL", "TP", "PnL", "Exit", "Support", "Resistance"]
    for col in float_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0.0).astype(float)
    
    # Fix for text columns
    if "Mistake" in df.columns:
        df["Mistake"] = df["Mistake"].astype(str).replace("nan", "")
        
    return df

def save_data(df):
    df.to_csv(FILE_NAME, index=False)

def score_trade(trend, entry, support, resistance, sl, rrr):
    score = 10
    mistakes = []
    if trend == "Uptrend" and entry < support:
        score -= 2
        mistakes.append("Long below Support")
    if trend == "Downtrend" and entry > resistance:
        score -= 2
        mistakes.append("Short above Resistance")
    if rrr < 2:
        score -= 2
        mistakes.append("Low RR")
    
    grade = "A" if score >= 8 else "B" if score >= 6 else "C" if score >= 4 else "D"
    return score, mistakes, grade

# --- INITIALIZE ---
st.set_page_config(page_title="Crypto Journal", layout="wide")
df = load_data()

# --- UI TABS ---
tab1, tab2, tab3 = st.tabs(["🆕 New Trade", "🏁 Close Trade", "📊 Analytics"])

with tab1:
    st.subheader("Log New Position")
    mode = st.radio("SL Mode", ["Auto SL", "Manual SL"], horizontal=True)

    col1, col2 = st.columns(2)
    with col1:
        entry = st.number_input("Entry Price", min_value=0.0, value=1.0, format="%.8f", step=0.0001)
        cost = st.number_input("Capital ($)", min_value=1.0, value=100.0, step=10.0)
        risk_pct = st.number_input("Risk %", min_value=0.1, max_value=100.0, value=1.0, step=0.1)

    with col2:
        rrr = st.selectbox("Desired R:R", [2, 3, 4, 5])
        coin = st.text_input("Coin/Pair", "BTC/USDT").upper()

    # Calculations
    risk_amount = cost * (risk_pct / 100)
    if mode == "Auto SL":
        qty = cost / entry if entry > 0 else 0
        sl = entry - (risk_amount / qty) if qty > 0 else 0
        tp = entry + ((entry - sl) * rrr)
    else:
        sl = st.number_input("Manual SL Price", value=entry * 0.95, format="%.8f", step=0.0001)
        sl_dist = abs(entry - sl)
        qty = risk_amount / sl_dist if sl_dist > 0 else 0
        tp = entry + (sl_dist * rrr) if entry > sl else entry - (sl_dist * rrr)

    st.success(f"""
    🎯 **Order Plan:**  
    **Qty:** {qty:.4f} | **SL:** {sl:.8f} | **TP:** {tp:.8f} | **Risk:** ${risk_amount:.2f}
    """)

    st.markdown("---")
    c1, c2 = st.columns(2)
    with c1:
        trend = st.selectbox("Trend", ["Uptrend", "Downtrend", "Range"])
        setup = st.selectbox("Setup", ["Pullback", "Breakout", "SMC/ICT", "Reversal"])
    with c2:
        support = st.number_input("Support", value=entry*0.9, format="%.8f", step=0.0001)
        resistance = st.number_input("Resistance", value=entry*1.1, format="%.8f", step=0.0001)
    
    emotion = st.text_input("Emotion (Calm, FOMO, etc.)")
    score, mistakes, grade = score_trade(trend, entry, support, resistance, sl, rrr)
    
    if st.button("🚀 Save Trade Entry"):
        new_trade = {
            "Trade #": len(df) + 1,
            "Date": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "Coin": coin, "Entry": entry, "Cost": cost, "Qty": qty,
            "Risk %": risk_pct, "RRR": rrr, "SL": sl, "TP": tp,
            "Mode": mode, "Trend": trend, "Setup": setup,
            "Support": support, "Resistance": resistance,
            "Emotion": emotion, "Score": score, "Mistake": ", ".join(mistakes),
            "Exit": 0.0, "PnL": 0.0, "Status": "Open"
        }
        df = pd.concat([df, pd.DataFrame([new_trade])], ignore_index=True)
        save_data(df)
        st.toast(f"Saved {coin}!")
        st.info("✅ Trade Saved! Head to 'Close Trade' tab to manage it.")
        st.balloons()

with tab2:
    st.subheader("Manage Open Positions")
    open_trades = df[df["Status"] == "Open"].copy()

    if not open_trades.empty:
        open_trades["label"] = open_trades["Trade #"].astype(str) + " | " + open_trades["Coin"]
        selected = st.selectbox("Select trade to close:", open_trades["label"])
        trade_idx = open_trades[open_trades["label"] == selected].index[0]

        planned_tp = float(df.at[trade_idx, "TP"])
        planned_sl = float(df.at[trade_idx, "SL"])

        col_ex1, col_ex2 = st.columns(2)
        with col_ex1:
            reason = st.selectbox("Exit Reason", ["Hit TP", "Hit SL", "Manual Close", "Break Even"])
        
        with col_ex2:
            if reason == "Hit TP": default_exit = planned_tp
            elif reason == "Hit SL": default_exit = planned_sl
            else: default_exit = float(df.at[trade_idx, "Entry"])
            
            exit_price = st.number_input("Final Exit Price", value=default_exit, format="%.8f", step=0.0001)

        if st.button("✅ Confirm Close"):
            pnl = (exit_price - float(df.at[trade_idx, "Entry"])) * float(df.at[trade_idx, "Qty"])
            df.at[trade_idx, "Exit"] = exit_price
            df.at[trade_idx, "PnL"] = round(pnl, 2)
            df.at[trade_idx, "Status"] = "Closed"
            df.at[trade_idx, "Mistake"] = f"{df.at[trade_idx, 'Mistake']} | Exit: {reason}".strip(" | ")
            save_data(df)
            st.success(f"Closed! PnL: ${pnl:.2f}")
            st.rerun()
    else:
        st.info("No active trades.")

with tab3:
    st.subheader("Performance Analytics")
    st.dataframe(df, use_container_width=True)
    
    closed = df[df["Status"] == "Closed"].copy()
    if not closed.empty:
        total_pnl = closed["PnL"].sum()
        win_rate = (len(closed[closed["PnL"] > 0]) / len(closed)) * 100
        
        m1, m2, m3 = st.columns(3)
        m1.metric("Total PnL", f"${total_pnl:.2f}")
        m2.metric("Win Rate", f"{win_rate:.1f}%")
        m3.metric("Trades", len(closed))
        
        st.bar_chart(closed.groupby("Setup")["PnL"].sum())

# --- DANGER ZONE ---
st.markdown("---")
with st.expander("🧹 Data Management"):
    if st.button("Delete All Trade History"):
        if os.path.exists(FILE_NAME):
            os.remove(FILE_NAME)
            st.rerun()