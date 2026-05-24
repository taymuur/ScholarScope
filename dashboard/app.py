"""ScholarScope — streamlit dashboard for the openalex task 2 comparator study.

covers the 24 Russell Group universities plus the University of East Anglia (UEA)
as an external benchmark comparator. UEA is not a Russell Group member.

run from the project folder with:
    python -m streamlit run dashboard/app.py
"""

from __future__ import annotations

import math
import re
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st


# ── paths and palette ──────────────────────────────────────────────────────────
data_dir = Path(__file__).resolve().parent / "data"

rg_colour  = "#20808D"   # teal — Russell Group
uea_colour = "#B0436A"   # deep rose — UEA highlight, sits with the teal theme
rg_muted   = "#C7C4BC"   # grey — muted background points
ink        = "#28251D"

# a 15-colour set for the collaboration network, picked for clear node separation
network_palette = [
    "#20808D", "#B0436A", "#5A7D52", "#6B4F76", "#C99A2E",
    "#1B474D", "#C2607E", "#93A87E", "#8C6B97", "#E8C56C",
    "#44A7B5", "#B85C75", "#3F6B5C", "#4A6B8A", "#8A857E",
]


st.set_page_config(
    page_title="ScholarScope — Russell Group vs UEA Comparator",
    page_icon="🔬",
    layout="wide",
)

# ── styling ──────────────────────────────────────────────────────────────────
# all html passed to st.markdown must start at column 0, otherwise streamlit
# treats a 4+ space indent as a markdown code block and prints the source.
st.markdown(
"""<style>
@import url('https://api.fontshare.com/v2/css?f[]=satoshi@400,500,700&display=swap');
html, body, [class*="css"] { font-family: 'Satoshi', 'Inter', sans-serif; }

/* leave room for the streamlit toolbar, then cap width for a tidy desktop layout */
.block-container { padding-top: 3.4rem !important; padding-bottom: 1rem !important; max-width: 1480px; }

.stApp { background: #F4F2EC; color: #28251D; }
h1, h2, h3, h4, h5, h6 { color: #1F1D17; }

section[data-testid="stSidebar"] { background: #EFECE4; border-right: 1px solid #DDD9CF; }

/* metric cards — subtle lift on hover for a bit of life */
div[data-testid="stMetric"] {
    background: #FFFFFF;
    border: 1px solid #E3E0D7;
    border-radius: 14px;
    padding: 16px 18px;
    box-shadow: 0 1px 2px rgba(0,0,0,0.04);
    transition: transform 0.15s ease, box-shadow 0.15s ease;
}
div[data-testid="stMetric"]:hover {
    transform: translateY(-2px);
    box-shadow: 0 6px 18px rgba(0,0,0,0.09);
}

/* tabs */
div[data-baseweb="tab-list"] { gap: 4px; border-bottom: 1px solid #E3E0D7; }
button[data-baseweb="tab"] { font-weight: 600; font-size: 0.97rem; padding: 9px 18px; }
button[data-baseweb="tab"][aria-selected="true"] { color: #1B474D; }
div[data-baseweb="tab-highlight"] { background-color: #20808D; }

/* multiselect chips — white text on teal so field names stay readable */
span[data-baseweb="tag"] { background-color: #20808D !important; border-radius: 6px !important; }
span[data-baseweb="tag"] span { color: #FFFFFF !important; }
span[data-baseweb="tag"] svg { fill: #FFFFFF !important; }

.small-note { color: #6F6E68; font-size: 0.92rem; max-width: 100%; line-height: 1.55; }
.uea-label { color: #B0436A; font-weight: 600; }
.section-head { font-size: 1.12rem; font-weight: 700; color: #1F1D17; margin: 4px 0 2px 0; }

/* dark header banner — sits clearly apart from the cream body */
.app-header {
    background: linear-gradient(135deg, #1B474D 0%, #235F69 100%);
    border-radius: 14px;
    padding: 20px 26px;
    margin-bottom: 14px;
    display: flex; align-items: center; justify-content: space-between;
    flex-wrap: wrap; gap: 14px;
}
.brand-name { font-size: 1.95rem; font-weight: 700; letter-spacing: -0.015em; color: #FFFFFF; line-height: 1.05; }
.brand-tag  { font-size: 0.95rem; color: #BFD6D9; margin-top: 3px; }
.coverage-chip {
    display: inline-block; background: rgba(255,255,255,0.12);
    border: 1px solid rgba(255,255,255,0.22);
    border-radius: 999px; padding: 5px 14px; font-size: 0.82rem; color: #EAF2F3;
    margin-left: 6px;
}

/* dark footer banner */
.app-footer {
    margin-top: 30px; padding: 15px 20px;
    background: #1B474D; border-radius: 14px;
    text-align: center; font-size: 0.86rem; color: #BFD6D9; line-height: 1.7;
}
.app-footer strong { color: #FFFFFF; }
.app-footer a { color: #8FCAD2; text-decoration: none; }
</style>""",
    unsafe_allow_html=True,
)


# ── data loading ──────────────────────────────────────────────────────────────
@st.cache_data(show_spinner=False)
def load_data(path: Path) -> dict[str, pd.DataFrame]:
    """load the pre-aggregated csv files the dashboard runs on."""
    out: dict[str, pd.DataFrame] = {
        "yearly":           pd.read_csv(path / "yearly_summary.csv"),
        "field_year":       pd.read_csv(path / "field_year_summary.csv"),
        "field_counts":     pd.read_csv(path / "field_counts.csv"),
        "institution":      pd.read_csv(path / "institution_summary.csv"),
        "institution_year": pd.read_csv(path / "institution_year_summary.csv"),
        "uea_comparison":   pd.read_csv(path / "uea_metric_comparison.csv"),
        "field_spec":       pd.read_csv(path / "uea_field_specialisation.csv"),
    }
    # collaboration and record table are optional — degrade gracefully if absent
    collab = path / "uea_rg_collaboration.csv"
    out["collab"] = pd.read_csv(collab) if collab.exists() else pd.DataFrame(columns=["institution", "co_pubs"])
    rec = path / "record_table_top100k.csv"
    out["records"] = pd.read_csv(rec) if rec.exists() else pd.DataFrame()
    return out


def fmt_count(value: float) -> str:
    """compact number formatting — 1.2k, 3.4m."""
    value = float(value)
    if value >= 1_000_000:
        return f"{value / 1_000_000:.2f}m"
    if value >= 1_000:
        return f"{value / 1_000:.1f}k"
    return f"{value:,.0f}"


def fmt_pct(value: float) -> str:
    return "—" if pd.isna(value) else f"{value * 100:.1f}%"


def show_plotly(fig) -> None:
    """support both older and newer streamlit width arguments."""
    try:
        st.plotly_chart(fig, width="stretch")
    except TypeError:
        st.plotly_chart(fig, use_container_width=True)


def show_dataframe(df: pd.DataFrame) -> None:
    try:
        st.dataframe(df, width="stretch")
    except TypeError:
        st.dataframe(df, use_container_width=True)


_html_tag = re.compile(r"<[^>]+>")


data = load_data(data_dir)
yearly           = data["yearly"]
field_year       = data["field_year"]
field_counts     = data["field_counts"]
institution      = data["institution"]
institution_year = data["institution_year"]
uea_comparison   = data["uea_comparison"]
field_spec       = data["field_spec"]
collab           = data["collab"]
records          = data["records"]

# coerce the is_uea flag in case it loaded as text
institution["is_uea"]      = institution["is_uea"].astype(str).str.lower().isin(["true", "1"])
institution_year["is_uea"] = institution_year["is_uea"].astype(str).str.lower().isin(["true", "1"])


# ── header ────────────────────────────────────────────────────────────────────
n_inst_total = institution["institution"].nunique()
yr_lo = int(institution_year["publication_year"].min())
yr_hi = int(institution_year["publication_year"].max())

st.markdown(
f"""<div class="app-header">
<div style="display:flex; align-items:center; gap:14px;">
<svg width="48" height="48" viewBox="0 0 48 48" xmlns="http://www.w3.org/2000/svg" style="flex-shrink:0;">
<circle cx="20" cy="20" r="15" fill="none" stroke="#FFFFFF" stroke-width="3.2"/>
<circle cx="20" cy="20" r="7" fill="#B0436A" opacity="0.95"/>
<circle cx="20" cy="20" r="2.4" fill="#FFFFFF"/>
<line x1="30.5" y1="30.5" x2="42" y2="42" stroke="#FFFFFF" stroke-width="3.8" stroke-linecap="round"/>
</svg>
<div>
<div class="brand-name">ScholarScope</div>
<div class="brand-tag">OpenAlex Russell Group vs UEA Comparator</div>
</div>
</div>
<div>
<span class="coverage-chip">{yr_lo}&ndash;{yr_hi}</span>
<span class="coverage-chip">{n_inst_total} institutions</span>
<span class="coverage-chip">Journal articles</span>
</div>
</div>""",
    unsafe_allow_html=True,
)

st.markdown(
"""<p class="small-note">
A Python prototype exploring OpenAlex journal article metadata for the 24 Russell Group universities and the University of East Anglia as an external benchmark comparator. The submitted dataset is a full 2015&ndash;2024 extract; this dashboard runs on pre-aggregated files so the demo stays responsive. <span class="uea-label">UEA is not a Russell Group member.</span> It appears here as a comparator institution.
</p>""",
    unsafe_allow_html=True,
)


# ── sidebar filters ───────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### Filters")

    group_choice = st.radio(
        "Institution groups",
        ["Both", "Russell Group only", "UEA only"],
        index=0,
        help="Drives the overview metrics and the institution explorer.",
    )

    years = sorted(yearly["publication_year"].dropna().astype(int).unique())
    year_range = st.slider("Publication years", min(years), max(years), (min(years), max(years)))

    field_options  = field_counts.sort_values("records", ascending=False)["field"].tolist()
    selected_fields = st.multiselect("Research fields", field_options, default=field_options[:8])

    min_records = st.slider("Minimum records per institution", 500, 10000, 1000, step=500)

    oa_choice = st.radio("Record table — open access", ["all", "open access only", "closed only"])

    st.divider()
    st.caption("Data: OpenAlex (openalex.org), CC0. Built for CMP-7022B.")

selected_fields = selected_fields if selected_fields else field_options

# resolve the group filter
show_rg  = group_choice in ("Both", "Russell Group only")
show_uea = group_choice in ("Both", "UEA only")


def by_group(df: pd.DataFrame) -> pd.DataFrame:
    """filter an institution-level frame to the selected group(s)."""
    mask = (show_rg & ~df["is_uea"]) | (show_uea & df["is_uea"])
    return df[mask].copy()


institution_g      = by_group(institution)
institution_year_g = by_group(institution_year)


# ── tabs ──────────────────────────────────────────────────────────────────────
tab_overview, tab_uea, tab_explorer, tab_records = st.tabs(
    ["  Overview  ", "  UEA benchmark  ", "  Institution explorer  ", "  Records  "]
)


# ══ overview ══════════════════════════════════════════════════════════════════
with tab_overview:
    # the overview metrics respond to the institution group filter
    g = institution_g
    if g.empty:
        st.info("No institutions match the current filter. Loosen the group filter.")
    else:
        total_records = g["records"].sum()
        oa_share      = (g["open_access_share"] * g["records"]).sum() / total_records
        intl_share    = (g["international_share"] * g["records"]).sum() / total_records
        median_fwci   = g["mean_fwci_style_ratio"].median()

        k = st.columns(5)
        k[0].metric("Institutions", f"{len(g)}")
        k[1].metric("Article records", fmt_count(total_records))
        k[2].metric("Open access", fmt_pct(oa_share))
        k[3].metric("International", fmt_pct(intl_share))
        k[4].metric("Median FWCI ratio", f"{median_fwci:.2f}",
                    delta=f"{median_fwci - 1.0:+.2f} vs 1.0", delta_color="normal")

        st.caption("Records counts institution&ndash;work links — a paper with three institutions counts three "
                   "times. All five metrics update with the institution group filter.")

    st.write("")

    # open access over time — full width, aggregated for the selected group
    st.markdown('<div class="section-head">Open access over time</div>', unsafe_allow_html=True)
    iy = institution_year_g[institution_year_g["publication_year"].between(*year_range)]
    if iy.empty:
        st.info("No data for this filter combination.")
    else:
        oa_trend = (
            iy.groupby("publication_year")
            .apply(lambda d: (d["open_access_share"] * d["records"]).sum() / d["records"].sum())
            .reset_index(name="oa_share")
        )
        fig = go.Figure(go.Scatter(
            x=oa_trend["publication_year"], y=oa_trend["oa_share"],
            mode="lines+markers",
            line=dict(color=rg_colour, width=2.8),
            marker=dict(size=9),
            fill="tozeroy", fillcolor="rgba(32,128,141,0.10)",
            hovertemplate="Year %{x}<br>Open access share: %{y:.1%}<extra></extra>",
        ))
        fig.update_layout(
            template="plotly_white", height=400,
            xaxis=dict(title="Publication year", tickmode="linear", dtick=1),
            yaxis=dict(title="Open access share", tickformat=".0%", range=[0, 1]),
            margin=dict(l=20, r=20, t=20, b=35),
        )
        show_plotly(fig)
        st.caption("Share of journal articles published open access, weighted by record volume. "
                   "Follows the year and institution group filters.")


# ══ uea benchmark ═════════════════════════════════════════════════════════════
with tab_uea:
    if not (show_rg and show_uea):
        st.info(
            "The UEA benchmark needs **both** groups selected — every chart here compares "
            "UEA against the Russell Group. Switch the group filter to **Both**."
        )
    else:
        st.markdown('<div class="section-head">UEA performance index vs the Russell Group median</div>',
                    unsafe_allow_html=True)
        st.markdown(
"""<p class="small-note">Each bar shows UEA's value as a ratio of the Russell Group institutional median. A value of 1.0 means UEA matches the RG median; above means stronger, below means weaker. Putting every metric on this common index lets unlike units share one axis.</p>""",
            unsafe_allow_html=True,
        )

        metric_labels = {
            "output_records":               "Output records",
            "mean_fwci_style_ratio":        "Mean FWCI ratio",
            "median_field_year_percentile": "Median field-year percentile",
            "top_10_share":                 "Top 10% share",
            "open_access_share":            "Open access share",
            "international_share":          "International collaboration share",
        }
        comp = uea_comparison.copy()
        comp["label"]  = comp["metric"].map(metric_labels).fillna(comp["metric"])
        comp = comp.sort_values("uea_vs_rg_ratio")
        comp["colour"] = [uea_colour if v >= 1.0 else rg_muted for v in comp["uea_vs_rg_ratio"]]

        fig = go.Figure(go.Bar(
            y=comp["label"], x=comp["uea_vs_rg_ratio"], orientation="h",
            marker_color=comp["colour"],
            text=[f"{v:.2f}" for v in comp["uea_vs_rg_ratio"]],
            textposition="outside",
            hovertemplate=("<b>%{y}</b><br>UEA / RG median: %{x:.3f}<br>"
                           "UEA value: %{customdata[0]}<br>RG median: %{customdata[1]}<extra></extra>"),
            customdata=list(zip(comp["uea_value"].round(3), comp["rg_median"].round(3))),
        ))
        fig.add_vline(x=1.0, line_dash="dot", line_color=ink,
                      annotation_text="RG median", annotation_position="top right",
                      annotation_font_size=10)
        fig.update_layout(
            template="plotly_white", height=360,
            xaxis=dict(title="UEA / RG median ratio"),
            yaxis=dict(title=""),
            margin=dict(l=20, r=40, t=20, b=35),
        )
        show_plotly(fig)

        st.divider()

        st.divider()

        # field specialisation — full width
        st.markdown('<div class="section-head">Field concentration</div>', unsafe_allow_html=True)
        st.markdown(
"""<p class="small-note">Specialisation index = UEA field share &divide; Russell Group field share. Above 1.0 means UEA is more concentrated in that field than the RG average.</p>""",
            unsafe_allow_html=True,
        )
        spec = field_spec[field_spec["rg_share"] > 0].sort_values("specialisation_index")
        spec_colour = [uea_colour if v >= 1.0 else rg_muted for v in spec["specialisation_index"]]
        fig = go.Figure(go.Bar(
            y=spec["field"], x=spec["specialisation_index"], orientation="h",
            marker_color=spec_colour,
            hovertemplate=("<b>%{y}</b><br>Specialisation index: %{x:.2f}<br>"
                           "UEA share: %{customdata[0]:.1%}<br>RG share: %{customdata[1]:.1%}<extra></extra>"),
            customdata=list(zip(spec["uea_share"], spec["rg_share"])),
        ))
        fig.add_vline(x=1.0, line_dash="dot", line_color=ink,
                      annotation_text="RG baseline", annotation_position="top right",
                      annotation_font_size=10)
        fig.update_layout(
            template="plotly_white", height=540,
            xaxis=dict(title="Specialisation index"),
            yaxis=dict(title=""),
            margin=dict(l=20, r=20, t=20, b=35),
        )
        show_plotly(fig)

        st.divider()

        # metric trend over time — full width, user picks which metric to track
        st.markdown('<div class="section-head">UEA vs Russell Group over time</div>',
                    unsafe_allow_html=True)
        trend_options = {
            "Mean FWCI ratio":              "mean_fwci_style_ratio",
            "Median field-year percentile": "median_percentile",
            "Open access share":            "open_access_share",
            "Top 10% share":                "top10_share",
        }
        pick = st.selectbox("Metric", list(trend_options), index=0)
        col = trend_options[pick]
        is_pct = col in ("open_access_share", "top10_share")

        iy = institution_year[institution_year["publication_year"].between(*year_range)]
        uea_t = iy[iy["is_uea"]].sort_values("publication_year")
        rg_t  = (
            iy[~iy["is_uea"]].groupby("publication_year")[col]
            .agg(med="median", q1=lambda x: x.quantile(0.25), q3=lambda x: x.quantile(0.75))
            .reset_index()
        )

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=pd.concat([rg_t["publication_year"], rg_t["publication_year"][::-1]]),
            y=pd.concat([rg_t["q3"], rg_t["q1"][::-1]]),
            fill="toself", fillcolor="rgba(32,128,141,0.12)",
            line=dict(color="rgba(255,255,255,0)"),
            name="RG interquartile range", hoverinfo="skip",
        ))
        fig.add_trace(go.Scatter(
            x=rg_t["publication_year"], y=rg_t["med"],
            mode="lines+markers", name="Russell Group median",
            line=dict(color=rg_colour, width=2.6), marker=dict(size=8),
            hovertemplate="Year %{x}<br>RG median: %{y:.3f}<extra></extra>",
        ))
        fig.add_trace(go.Scatter(
            x=uea_t["publication_year"], y=uea_t[col],
            mode="lines+markers", name="University of East Anglia",
            line=dict(color=uea_colour, width=3.0), marker=dict(size=10, symbol="diamond"),
            hovertemplate="Year %{x}<br>UEA: %{y:.3f}<extra></extra>",
        ))
        if col == "mean_fwci_style_ratio":
            fig.add_hline(y=1.0, line_dash="dot", line_color="#BAB9B4",
                          annotation_text="field-year average", annotation_position="bottom right",
                          annotation_font_size=10)
        fig.update_layout(
            template="plotly_white", height=440,
            xaxis=dict(title="Publication year", tickmode="linear", dtick=1),
            yaxis=dict(title=pick, tickformat=".0%" if is_pct else None),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            margin=dict(l=20, r=20, t=20, b=35),
        )
        show_plotly(fig)

        st.divider()

        # co-publication network
        st.markdown('<div class="section-head">UEA co-publication network</div>', unsafe_allow_html=True)
        st.markdown(
"""<p class="small-note">A radial map with UEA at the centre and its top 15 Russell Group co-authoring institutions around it. Edge thickness and node size both encode co-publication volume; each partner has its own colour. Counts use unique works.</p>""",
            unsafe_allow_html=True,
        )

        if collab.empty:
            st.info("Collaboration data not found. Expected `data/uea_rg_collaboration.csv`.")
        else:
            net = collab.sort_values("co_pubs", ascending=False).head(15).reset_index(drop=True)
            n = len(net)
            angles = [2 * math.pi * i / n for i in range(n)]
            radius = 2.0
            max_co = net["co_pubs"].max()

            fig = go.Figure()
            # edges behind nodes
            for i, row in net.iterrows():
                x = radius * math.cos(angles[i])
                y = radius * math.sin(angles[i])
                w = 0.7 + 5.5 * (row["co_pubs"] / max_co)
                alpha = 0.35 + 0.5 * (row["co_pubs"] / max_co)
                c = network_palette[i % len(network_palette)]
                r_, g_, b_ = int(c[1:3], 16), int(c[3:5], 16), int(c[5:7], 16)
                fig.add_trace(go.Scatter(
                    x=[0, x], y=[0, y], mode="lines",
                    line=dict(width=w, color=f"rgba({r_},{g_},{b_},{alpha:.2f})"),
                    hoverinfo="skip", showlegend=False,
                ))
                fig.add_annotation(x=x / 2, y=y / 2, text=f"{int(row['co_pubs']):,}",
                                   showarrow=False, font=dict(size=9, color="#3A3631"),
                                   bgcolor="rgba(255,255,255,0.78)", borderpad=2)

            node_x, node_y = [0.0], [0.0]
            node_text, node_size, node_colour, hover = ["UEA"], [36], [uea_colour], \
                ["<b>University of East Anglia</b><extra></extra>"]
            for i, row in net.iterrows():
                x = radius * math.cos(angles[i])
                y = radius * math.sin(angles[i])
                node_x.append(x); node_y.append(y)
                short = (row["institution"]
                         .replace("University of ", "")
                         .replace("University College London", "UCL")
                         .replace("King's College London", "King's College"))
                node_text.append(short)
                node_size.append(15 + 23 * (row["co_pubs"] / max_co))
                node_colour.append(network_palette[i % len(network_palette)])
                hover.append(f"<b>{row['institution']}</b><br>"
                             f"Co-publications with UEA: {int(row['co_pubs']):,}<extra></extra>")

            text_pos = ["middle center"] + [
                "top center" if node_y[i + 1] >= 0 else "bottom center" for i in range(n)
            ]
            fig.add_trace(go.Scatter(
                x=node_x, y=node_y, mode="markers+text",
                text=node_text, textposition=text_pos,
                textfont=dict(size=[13] + [10] * n, color=[uea_colour] + [ink] * n),
                marker=dict(size=node_size, color=node_colour, line=dict(width=1.5, color="white")),
                hovertemplate=hover, showlegend=False,
            ))
            fig.update_layout(
                template="plotly_white", height=560,
                xaxis=dict(visible=False),
                yaxis=dict(visible=False, scaleanchor="x"),
                margin=dict(l=10, r=10, t=10, b=10),
                plot_bgcolor="#FBFBF9",
            )
            show_plotly(fig)

# ══ institution explorer ══════════════════════════════════════════════════════
with tab_explorer:
    st.markdown('<div class="section-head">Institution comparator</div>', unsafe_allow_html=True)
    st.markdown(
"""<p class="small-note">Each point is an institution. Choose the y-axis metric, then spotlight any institutions to label and enlarge them. Bubble size encodes international collaboration share. Responds to the group and minimum-records filters.</p>""",
        unsafe_allow_html=True,
    )

    y_options = {
        "Median field-year percentile": "median_percentile",
        "Mean FWCI ratio":              "mean_fwci_style_ratio",
        "Top 10% share":                "top10_share",
        "Open access share":            "open_access_share",
    }
    c1, c2 = st.columns([1, 1.6])
    with c1:
        y_pick = st.selectbox("Y-axis metric", list(y_options), index=0)
    y_col = y_options[y_pick]

    inst_f = institution_g[institution_g["records"] >= min_records].copy()

    with c2:
        spotlight = st.multiselect(
            "Spotlight institutions",
            sorted(inst_f["institution"].unique()),
            default=[i for i in ["University of East Anglia"] if i in set(inst_f["institution"])],
        )

    if inst_f.empty:
        st.info("No institutions match the current filters. Lower the minimum records or change the group filter.")
    else:
        inst_f["spot"] = inst_f["institution"].isin(spotlight)
        base = inst_f[~inst_f["spot"]]
        spot = inst_f[inst_f["spot"]]

        fig = go.Figure()
        # background institutions
        fig.add_trace(go.Scatter(
            x=base["records"], y=base[y_col], mode="markers",
            name="Institutions",
            marker=dict(
                size=base["international_share"] * 42 + 9,
                color=[uea_colour if u else rg_muted for u in base["is_uea"]],
                opacity=0.7, line=dict(width=0.7, color="#A8A49B"),
            ),
            customdata=list(zip(base["institution"], base["international_share"])),
            hovertemplate=("<b>%{customdata[0]}</b><br>Records: %{x:,}<br>"
                           + y_pick + ": %{y:.2f}<br>International: %{customdata[1]:.1%}<extra></extra>"),
        ))
        # spotlit institutions — labelled and enlarged
        if not spot.empty:
            fig.add_trace(go.Scatter(
                x=spot["records"], y=spot[y_col], mode="markers+text",
                name="Spotlight",
                text=[s.replace("University of ", "") for s in spot["institution"]],
                textposition="top center",
                textfont=dict(size=11, color=ink),
                marker=dict(
                    size=spot["international_share"] * 42 + 17,
                    color=[uea_colour if u else rg_colour for u in spot["is_uea"]],
                    symbol=["diamond" if u else "circle" for u in spot["is_uea"]],
                    line=dict(width=1.6, color="white"),
                ),
                customdata=list(zip(spot["institution"], spot["international_share"])),
                hovertemplate=("<b>%{customdata[0]}</b><br>Records: %{x:,}<br>"
                               + y_pick + ": %{y:.2f}<br>International: %{customdata[1]:.1%}<extra></extra>"),
            ))
        if y_col == "mean_fwci_style_ratio":
            fig.add_hline(y=1.0, line_dash="dot", line_color="#BAB9B4",
                          annotation_text="field-year average", annotation_position="bottom right",
                          annotation_font_size=10)
        fig.update_layout(
            template="plotly_white", height=560,
            xaxis=dict(title="Article records"),
            yaxis=dict(title=y_pick,
                       tickformat=".0%" if y_col in ("open_access_share", "top10_share") else None),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            margin=dict(l=20, r=20, t=20, b=35),
        )
        show_plotly(fig)

        # spotlight detail table
        if not spot.empty:
            st.markdown('<div class="section-head">Spotlight detail</div>', unsafe_allow_html=True)
            detail = spot[["institution", "peer_group", "records", "median_percentile",
                           "mean_fwci_style_ratio", "top10_share", "open_access_share",
                           "international_share"]].copy()
            detail = detail.rename(columns={
                "institution": "Institution", "peer_group": "Group", "records": "Records",
                "median_percentile": "Median percentile", "mean_fwci_style_ratio": "FWCI ratio",
                "top10_share": "Top 10% share", "open_access_share": "Open access",
                "international_share": "International",
            })
            for c in ("Top 10% share", "Open access", "International"):
                detail[c] = (detail[c] * 100).round(1).astype(str) + "%"
            detail["FWCI ratio"] = detail["FWCI ratio"].round(2)
            detail["Median percentile"] = detail["Median percentile"].round(1)
            show_dataframe(detail.reset_index(drop=True))


# ══ records ═══════════════════════════════════════════════════════════════════
with tab_records:
    st.markdown('<div class="section-head">Record table</div>', unsafe_allow_html=True)

    if records.empty:
        st.info("Record table not found. Expected `data/record_table_top100k.csv`.")
    else:
        st.caption("The 100,000 most-cited records from the full dataset, for responsiveness.")
        inst_col = ("comparator_institutions" if "comparator_institutions" in records.columns
                    else "russell_group_institutions")

        table_df = records[
            records["publication_year"].between(*year_range)
            & records["field"].isin(selected_fields)
        ].copy()
        if oa_choice == "open access only" and "is_open_access" in table_df.columns:
            table_df = table_df[table_df["is_open_access"]]
        elif oa_choice == "closed only" and "is_open_access" in table_df.columns:
            table_df = table_df[~table_df["is_open_access"]]

        search = st.text_input("Search titles or institutions", "")
        if search:
            mask = (
                table_df["title"].fillna("").str.contains(search, case=False, regex=False)
                | table_df[inst_col].fillna("").str.contains(search, case=False, regex=False)
            )
            table_df = table_df[mask]

        cols = [c for c in ["publication_year", "title", inst_col, "field",
                            "cited_by_count", "field_year_percentile", "oa_status",
                            "journal", "doi"] if c in table_df.columns]
        display_df = table_df[cols].sort_values("cited_by_count", ascending=False).head(500).copy()

        # strip html tags — openalex titles can carry <i>, <sup>, <sub> markup
        for c in ("title", "journal"):
            if c in display_df.columns:
                display_df[c] = (display_df[c].fillna("").astype(str)
                                 .str.replace(_html_tag, "", regex=True))

        display_df = display_df.rename(columns={
            "publication_year": "Year", "title": "Title", inst_col: "Institutions",
            "field": "Field", "cited_by_count": "Citations",
            "field_year_percentile": "Field-year percentile", "oa_status": "OA status",
            "journal": "Journal", "doi": "DOI",
        })
        show_dataframe(display_df)

        st.download_button(
            "Export filtered records (CSV)",
            display_df.to_csv(index=False).encode("utf-8"),
            "scholarscope_records.csv", "text/csv",
        )


# ── footer ────────────────────────────────────────────────────────────────────
st.markdown(
"""<div class="app-footer">
<div><strong>ScholarScope</strong> &nbsp;&middot;&nbsp; Built by Taimur Shahzad Gill &nbsp;&middot;&nbsp; &copy; 2026 &nbsp;&middot;&nbsp; All rights reserved</div>
<div style="margin-top:2px; font-size:0.8rem;">Data: <a href="https://openalex.org">OpenAlex</a> (CC0) &nbsp;&middot;&nbsp; CMP-7022B Visualisation Project</div>
</div>""",
    unsafe_allow_html=True,
)
