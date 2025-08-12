
import streamlit as st
import pandas as pd
from datetime import date
import calendar
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
import io
import os

st.set_page_config(page_title="Daily Expenses Dashboard", layout="wide")

DATA_PATH = "expenses.csv"

# ---------- Helpers ----------
def init_data():
    if not os.path.exists(DATA_PATH):
        df = pd.DataFrame(columns=["date","category","amount","notes"])
        df.to_csv(DATA_PATH, index=False)

def load_data():
    init_data()
    df = pd.read_csv(DATA_PATH)
    if not df.empty:
        df["date"] = pd.to_datetime(df["date"]).dt.date
        df["category"] = df["category"].astype(str)
        df["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0.0)
        df["notes"] = df["notes"].astype(str)
    return df

def save_data(df: pd.DataFrame):
    df.to_csv(DATA_PATH, index=False)

def month_name_to_num(name: str) -> int:
    if name == "All year":
        return 0
    months = {calendar.month_name[i]: i for i in range(1,13)}
    return months.get(name, 0)

def filter_df(df, year, month_opt, categories):
    if df.empty:
        return df
    df2 = df.copy()
    df2["year"] = pd.to_datetime(df2["date"]).dt.year
    df2["month"] = pd.to_datetime(df2["date"]).dt.month
    df2 = df2[df2["year"] == year]
    m = month_name_to_num(month_opt)
    if m != 0:
        df2 = df2[df2["month"] == m]
    if categories:
        df2 = df2[df2["category"].isin(categories)]
    return df2.drop(columns=["year","month"], errors="ignore")

def compute_kpis(df: pd.DataFrame):
    if df.empty:
        return 0.0, 0.0, 0.0, 0.0
    total = float(df["amount"].sum())
    by_day = df.groupby("date")["amount"].sum()
    avg_day = float(by_day.mean()) if not by_day.empty else 0.0
    max_day = float(by_day.max()) if not by_day.empty else 0.0
    return total, avg_day, max_day, float(len(df))

def generate_pdf(df_filtered, year, month_opt, total, avg_day, max_day):
    buffer = io.BytesIO()
    with PdfPages(buffer) as pdf:
        # Page 1: Summary
        fig1 = plt.figure(figsize=(8.27, 11.69))
        plt.axis("off")
        title = f"Expenses Report - {month_opt} {year}" if month_opt != "All year" else f"Expenses Report - Year {year}"
        lines = [
            title, "",
            f"Total spend: {total:,.2f}",
            f"Daily average: {avg_day:,.2f}",
            f"Max day: {max_day:,.2f}",
            f"Records: {len(df_filtered)}",
        ]
        y = 0.9
        for ln in lines:
            plt.text(0.1, y, ln, fontsize=14)
            y -= 0.06
        pdf.savefig(fig1, bbox_inches="tight"); plt.close(fig1)

        # Page 2: Daily chart
        fig2 = plt.figure(figsize=(8.27, 11.69))
        if not df_filtered.empty:
            by_day = df_filtered.groupby("date")["amount"].sum().sort_index()
            idx = list(range(len(by_day)))
            labels = [str(x) for x in by_day.index]
            plt.bar(idx, by_day.values)
            plt.title("Expenses by day")
            plt.xticks(idx, labels, rotation=90)
            plt.ylabel("Amount")
            plt.tight_layout()
        else:
            plt.axis("off")
            plt.text(0.1, 0.9, "No data to display", fontsize=14)
        pdf.savefig(fig2, bbox_inches="tight"); plt.close(fig2)

        # Page 3: Categories chart
        fig3 = plt.figure(figsize=(8.27, 11.69))
        if not df_filtered.empty:
            by_cat = df_filtered.groupby("category")["amount"].sum().sort_values(ascending=False)
            if not by_cat.empty:
                plt.pie(by_cat.values, labels=by_cat.index, autopct="%1.1f%%")
                plt.title("Category breakdown")
            else:
                plt.axis("off"); plt.text(0.1, 0.9, "No categories", fontsize=14)
        else:
            plt.axis("off"); plt.text(0.1, 0.9, "No data", fontsize=14)
        pdf.savefig(fig3, bbox_inches="tight"); plt.close(fig3)
    buffer.seek(0)
    return buffer.getvalue()

# ---------- UI ----------
st.title("💸 Daily Expenses Dashboard")

with st.sidebar:
    st.header("Settings")
    year = st.number_input("Year", min_value=2000, max_value=2100, value=date.today().year, step=1)
    months = ["All year"] + [calendar.month_name[i] for i in range(1,13)]
    month_opt = st.selectbox("Month", months, index=date.today().month)
    st.markdown("---")
    st.caption("Add a new expense")
    with st.form("add_expense", clear_on_submit=True):
        d = st.date_input("Date", value=date.today())
        cat = st.text_input("Category", placeholder="e.g., Food, Transport, Groceries")
        amt = st.number_input("Amount", min_value=0.0, step=1.0, format="%.2f")
        note = st.text_input("Notes", placeholder="Optional")
        submitted = st.form_submit_button("Add")
        if submitted:
            df = load_data()
            new_row = {"date": d, "category": cat if cat.strip() else "Uncategorized", "amount": amt, "notes": note}
            df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
            save_data(df)
            st.success("Added")

df_all = load_data()
cats_all = sorted(df_all["category"].dropna().unique().tolist()) if not df_all.empty else []
categories = st.multiselect("Filter by category", cats_all, default=[])

df_filtered = filter_df(df_all, year, month_opt, categories)

# KPIs
total, avg_day, max_day, count_rec = compute_kpis(df_filtered)
c1, c2, c3, c4 = st.columns(4)
c1.metric("Total spend", f"{total:,.2f}")
c2.metric("Daily average", f"{avg_day:,.2f}")
c3.metric("Max day", f"{max_day:,.2f}")
c4.metric("Records", f"{int(count_rec)}")

st.markdown("---")

# Charts
st.subheader("Charts")
if not df_filtered.empty:
    # Daily bar chart
    by_day = df_filtered.groupby("date")["amount"].sum().sort_index()
    idx = list(range(len(by_day)))
    labels = [str(x) for x in by_day.index]
    fig1 = plt.figure()
    plt.bar(idx, by_day.values)
    plt.title("Expenses by day")
    plt.xticks(idx, labels, rotation=90)
    plt.ylabel("Amount")
    st.pyplot(fig1)

    # Pie by category
    by_cat = df_filtered.groupby("category")["amount"].sum().sort_values(ascending=False)
    fig2 = plt.figure()
    if not by_cat.empty:
        plt.pie(by_cat.values, labels=by_cat.index, autopct="%1.1f%%")
        plt.title("Category breakdown")
    st.pyplot(fig2)
else:
    st.info("No data for current filters.")

st.markdown("---")
st.subheader("Data")
st.dataframe(df_filtered.sort_values("date"))

# Export buttons
colA, colB = st.columns(2)
with colA:
    csv_bytes = df_filtered.to_csv(index=False).encode("utf-8")
    st.download_button("⬇️ Export CSV", data=csv_bytes, file_name=f"expenses_{year}_{month_opt}.csv", mime="text/csv")
with colB:
    pdf_bytes = generate_pdf(df_filtered, year, month_opt, total, avg_day, max_day)
    st.download_button("⬇️ Export PDF", data=pdf_bytes, file_name=f"expenses_{year}_{month_opt}.pdf", mime="application/pdf")

st.caption("Note: data is saved locally to expenses.csv next to the app.")
