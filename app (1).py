import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from pathlib import Path

st.set_page_config(page_title="Dashboard Pasar Keuangan Harian", layout="wide")

DATA_PATH = Path(__file__).with_name("db_dashboard.xlsx")

@st.cache_data
def load_data(path: Path) -> pd.DataFrame:
    raw = pd.read_excel(path, header=None, engine="openpyxl")
    headers = ["Date"] + raw.iloc[0, 1:].tolist()
    df = raw.iloc[1:].copy()
    df.columns = headers

    if pd.api.types.is_numeric_dtype(df["Date"]):
        df["Date"] = pd.to_datetime(df["Date"], unit="D", origin="1899-12-30", errors="coerce")
    else:
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")

    for col in headers[1:]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    return df.dropna(subset=["Date"]).sort_values("Date").reset_index(drop=True)


def last_valid_point(df: pd.DataFrame, col: str):
    temp = df[["Date", col]].dropna()
    if temp.empty:
        return None, None
    row = temp.iloc[-1]
    return row["Date"], row[col]


def value_on_or_before(df: pd.DataFrame, col: str, target_date: pd.Timestamp):
    temp = df.loc[(df["Date"] <= target_date) & df[col].notna(), ["Date", col]].sort_values("Date")
    if temp.empty:
        return np.nan, pd.NaT
    row = temp.iloc[-1]
    return row[col], row["Date"]


def value_on_exact_date(df: pd.DataFrame, col: str, target_date: pd.Timestamp):
    temp = df.loc[(df["Date"] == target_date) & df[col].notna(), ["Date", col]].sort_values("Date")
    if temp.empty:
        return np.nan, pd.NaT
    row = temp.iloc[-1]
    return row[col], row["Date"]


def previous_month_end(latest_date: pd.Timestamp) -> pd.Timestamp:
    return latest_date.replace(day=1) - pd.Timedelta(days=1)


def same_business_day_last_year(latest_date: pd.Timestamp) -> pd.Timestamp:
    target = latest_date - pd.DateOffset(years=1)
    while target.weekday() >= 5:
        target = target - pd.Timedelta(days=1)
    return pd.Timestamp(target).normalize()


def compute_changes(df: pd.DataFrame, col: str) -> dict:
    temp = df[["Date", col]].dropna().sort_values("Date").reset_index(drop=True)
    if temp.empty:
        return {}

    latest_date = temp["Date"].iloc[-1]
    latest_val = temp[col].iloc[-1]

    prev_val = temp[col].iloc[-2] if len(temp) > 1 else np.nan
    week_val = temp[col].iloc[-6] if len(temp) > 5 else np.nan

    month_end = previous_month_end(latest_date)
    month_val, _ = value_on_or_before(temp, col, month_end)

    ytd_target = pd.Timestamp(year=latest_date.year - 1, month=12, day=31)
    ytd_val, _ = value_on_or_before(temp, col, ytd_target)

    yoy_target = same_business_day_last_year(latest_date)
    yoy_val, _ = value_on_exact_date(temp, col, yoy_target)

    def diff(base):
        return np.nan if pd.isna(base) else latest_val - base

    return {
        "current_date": latest_date,
        "current_value": latest_val,
        "DtD": diff(prev_val),
        "DtW": diff(week_val),
        "DtM": diff(month_val),
        "YtD": diff(ytd_val),
        "YoY": diff(yoy_val),
        "YoY_target": yoy_target,
    }


def fmt_level(x, digits=2, thousands=True):
    if pd.isna(x):
        return "-"
    return f"{x:,.{digits}f}" if thousands else f"{x:.{digits}f}"


def fmt_change(x, digits=1):
    if pd.isna(x):
        return "-"
    return f"{x:+,.{digits}f}"


def padded_x_range(df: pd.DataFrame, days_pad: int = 12):
    temp = df[["Date"]].dropna().sort_values("Date")
    if temp.empty:
        return None
    start = temp["Date"].iloc[0]
    end = temp["Date"].iloc[-1] + pd.Timedelta(days=days_pad)
    return [start, end]


def base_layout(fig: go.Figure, df: pd.DataFrame, title: str, subtitle: str | None = None, height: int = 320):
    fig.update_layout(
        title={
            "text": f"<b>{title}</b>" + (f"<br><sup>{subtitle}</sup>" if subtitle else ""),
            "x": 0.02,
            "xanchor": "left"
        },
        height=height,
        margin=dict(l=15, r=55, t=72, b=20),
        plot_bgcolor="white",
        paper_bgcolor="white",
        hovermode="x unified",
        font=dict(family="Arial"),
    )
    fig.update_xaxes(showgrid=False, tickformat="%b-%y", automargin=True)
    fig.update_yaxes(showgrid=True, gridcolor="rgba(0,0,0,0.08)", zeroline=False, automargin=True)
    xr = padded_x_range(df)
    if xr is not None:
        fig.update_xaxes(range=xr)
    return fig


def line_chart(df: pd.DataFrame, col: str, title: str, color: str, value_digits: int = 2, subtitle: str | None = None, thousands: bool = True):
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=df["Date"], y=df[col], mode="lines", name=col,
            line=dict(color=color, width=2.5),
            hovertemplate="%{x|%d %b %Y}<br>%{y:,.2f}<extra></extra>",
        )
    )

    last_date, last_val = last_valid_point(df, col)
    if last_date is not None:
        fig.add_trace(
            go.Scatter(
                x=[last_date], y=[last_val], mode="markers+text",
                text=[fmt_level(last_val, value_digits, thousands)],
                textposition="middle right",
                marker=dict(color=color, size=7),
                showlegend=False,
                cliponaxis=False,
                hovertemplate="%{x|%d %b %Y}<br>%{y:,.2f}<extra></extra>",
            )
        )

    fig = base_layout(fig, df, title, subtitle)
    fig.update_layout(showlegend=False)
    return fig


def sbn_ust_chart(df: pd.DataFrame, subtitle: str | None = None):
    colors = {"SBN10Y": "#1f77b4", "UST10Y": "#ff7f0e"}
    names = {"SBN10Y": "SBN 10Y", "UST10Y": "UST 10Y"}
    fig = go.Figure()
    for col in ["SBN10Y", "UST10Y"]:
        fig.add_trace(
            go.Scatter(
                x=df["Date"], y=df[col], mode="lines", name=names[col],
                line=dict(color=colors[col], width=2.5),
                hovertemplate=f"%{{x|%d %b %Y}}<br>{names[col]}: %{{y:.2f}}<extra></extra>",
            )
        )
        last_date, last_val = last_valid_point(df, col)
        if last_date is not None:
            fig.add_trace(
                go.Scatter(
                    x=[last_date], y=[last_val], mode="markers+text",
                    text=[f"{last_val:.2f}"], textposition="middle right",
                    marker=dict(color=colors[col], size=7),
                    showlegend=False,
                    cliponaxis=False,
                    hovertemplate=f"%{{x|%d %b %Y}}<br>{names[col]}: %{{y:.2f}}<extra></extra>",
                )
            )
    fig = base_layout(fig, df, "Yield SBN 10Y dan UST 10Y", subtitle)
    fig.update_layout(legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
    return fig


def summary_table(df: pd.DataFrame, specs: list[dict]) -> pd.DataFrame:
    rows = []
    for spec in specs:
        m = compute_changes(df, spec["column"])
        rows.append({
            "Indikator": spec["label"],
            spec.get("level_name", "Level"): fmt_level(m.get("current_value", np.nan), spec.get("digits", 2), spec.get("thousands", True)),
            "DtD": fmt_change(m.get("DtD", np.nan), spec.get("chg_digits", 1)),
            "DtW": fmt_change(m.get("DtW", np.nan), spec.get("chg_digits", 1)),
            "DtM": fmt_change(m.get("DtM", np.nan), spec.get("chg_digits", 1)),
            "YtD": fmt_change(m.get("YtD", np.nan), spec.get("chg_digits", 1)),
            "YoY": fmt_change(m.get("YoY", np.nan), spec.get("chg_digits", 1)),
        })
    return pd.DataFrame(rows)


def render_table(df_table: pd.DataFrame):
    st.dataframe(df_table, use_container_width=True, hide_index=True)


# ================= APP =================
df = load_data(DATA_PATH)
latest_date = df["Date"].max()

st.markdown(
    f"""
    <h2 style='text-align:center; color:#0B3B82; margin-bottom:0;'>PERKEMBANGAN INDIKATOR PASAR KEUANGAN HARIAN</h2>
    <p style='text-align:center; color:#333; margin-top:0;'>{latest_date.strftime('%d %B %Y')}</p>
    """,
    unsafe_allow_html=True,
)

with st.sidebar:
    st.header("Pengaturan")
    min_date = df["Date"].min().date()
    max_date = df["Date"].max().date()
    picked = st.date_input(
        "Rentang tanggal",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date,
    )
    if isinstance(picked, tuple) and len(picked) == 2:
        start_date, end_date = pd.to_datetime(picked[0]), pd.to_datetime(picked[1])
    else:
        start_date, end_date = df["Date"].min(), df["Date"].max()

    st.markdown("---")
    st.caption("Definisi perubahan tabel")
    st.caption("DtD = terhadap observasi tersedia sebelumnya")
    st.caption("DtW = terhadap 5 hari bursa sebelumnya")
    st.caption("DtM = terhadap posisi akhir bulan sebelumnya")
    st.caption("YtD = terhadap posisi akhir tahun sebelumnya")
    st.caption("YoY = terhadap exact same business day tahun sebelumnya")

plot_df = df[(df["Date"] >= start_date) & (df["Date"] <= end_date)].copy()
closing_date = plot_df["Date"].max() if not plot_df.empty else latest_date
subtitle = f"Closing per {closing_date.strftime('%d %b %Y')}"

c1, c2 = st.columns(2)
with c1:
    st.plotly_chart(
        line_chart(plot_df, "Rupiah", "Nilai Tukar Rupiah per Dolar AS", "#1f77b4", value_digits=0, subtitle=subtitle, thousands=True),
        use_container_width=True,
    )
    render_table(summary_table(plot_df, [
        {"column": "Rupiah", "label": "Rupiah", "digits": 0, "chg_digits": 1, "thousands": True, "level_name": "Level"}
    ]))

with c2:
    st.plotly_chart(
        line_chart(plot_df, "IHSG", "IHSG", "#1f77b4", value_digits=2, subtitle=subtitle, thousands=True),
        use_container_width=True,
    )
    render_table(summary_table(plot_df, [
        {"column": "IHSG", "label": "IHSG", "digits": 2, "chg_digits": 1, "thousands": True, "level_name": "Level"}
    ]))

st.markdown("<div style='height:12px;'></div>", unsafe_allow_html=True)
st.plotly_chart(sbn_ust_chart(plot_df, subtitle=subtitle), use_container_width=True)
render_table(summary_table(plot_df, [
    {"column": "SBN10Y", "label": "SBN 10Y", "digits": 2, "chg_digits": 2, "thousands": False, "level_name": "Yield"},
    {"column": "UST10Y", "label": "UST 10Y", "digits": 2, "chg_digits": 2, "thousands": False, "level_name": "Yield"},
]))

with st.expander("Lihat data mentah"):
    st.dataframe(plot_df, use_container_width=True, hide_index=True)
