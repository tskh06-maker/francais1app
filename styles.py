import streamlit as st

CUSTOM_CSS = """
<style>
:root {
    --color-primary: #3654B5;
    --color-primary-dark: #2A4090;
    --color-card: #F8F9FC;
    --color-border: #E4E7F1;
    --color-muted: #6B7280;
    --color-ink: #1C2233;
    --color-accent-gold: #B08D57;
}

h1 { letter-spacing: -0.02em; font-weight: 800 !important; }
h2, h3 { letter-spacing: -0.01em; font-weight: 700 !important; }

.app-hero {
    padding: 1.5rem 1.75rem;
    margin-bottom: 1.5rem;
    background: linear-gradient(135deg, #EAF0FC 0%, #FBF0E4 100%);
    border: 1px solid rgba(176, 141, 87, 0.22);
    border-radius: 18px;
}
.app-hero h1 {
    color: var(--color-ink) !important;
    margin: 0 0 0.35rem 0 !important;
    font-size: 1.9rem !important;
}
.app-hero p {
    color: var(--color-muted);
    margin: 0 0 0.9rem 0;
    font-size: 0.95rem;
}
.app-hero .hero-rule {
    width: 56px;
    height: 3px;
    border-radius: 2px;
    background: linear-gradient(90deg, var(--color-primary), var(--color-accent-gold));
}
@media (max-width: 480px) {
    .app-hero { padding: 1.25rem 1.25rem; }
    .app-hero h1 { font-size: 1.5rem !important; }
    .app-hero p { font-size: 0.88rem; }
}

.stButton > button {
    border-radius: 10px !important;
    border: 1px solid var(--color-border) !important;
    font-weight: 600 !important;
    padding: 0.55rem 1rem !important;
    transition: all 0.15s ease !important;
    box-shadow: 0 1px 2px rgba(0,0,0,0.03);
}
.stButton > button:hover {
    transform: translateY(-1px);
    box-shadow: 0 4px 10px rgba(0,0,0,0.08);
    border-color: var(--color-primary) !important;
    color: var(--color-primary) !important;
}
.stButton > button[kind="primary"] {
    background: var(--color-primary) !important;
    border-color: var(--color-primary) !important;
    box-shadow: 0 4px 12px rgba(54,84,181,0.25);
}
.stButton > button[kind="primary"]:hover {
    background: var(--color-primary-dark) !important;
    color: #fff !important;
}

.st-key-noun_rows .stButton > button,
.st-key-adj_rows .stButton > button {
    justify-content: flex-start !important;
    text-align: left !important;
}

[data-testid="stVerticalBlockBorderWrapper"] {
    border-radius: 16px !important;
    border-color: var(--color-border) !important;
    transition: box-shadow 0.15s ease;
}
[data-testid="stVerticalBlockBorderWrapper"]:hover {
    box-shadow: 0 6px 16px rgba(0,0,0,0.06);
}

[data-testid="stExpander"] {
    border-radius: 14px !important;
    border: 1px solid var(--color-border) !important;
    overflow: hidden;
    margin-bottom: 0.5rem;
}

[data-testid="stMetric"] {
    background: var(--color-card);
    border: 1px solid var(--color-border);
    border-radius: 14px;
    padding: 0.9rem 1rem;
}

.card-icon { font-size: 1.6rem; margin-bottom: 0.2rem; }
.card-title { font-weight: 700; font-size: 1.02rem; margin-bottom: 0.15rem; }
.card-caption { color: var(--color-muted); font-size: 0.85rem; margin-bottom: 0.7rem; min-height: 2.4em; }

.cat-tile-icon { font-size: 1.4rem; margin-bottom: 0.15rem; }
.cat-tile-title { font-weight: 700; font-size: 0.92rem; line-height: 1.3; margin-bottom: 0.15rem; min-height: 2.4em; }
.cat-tile-count { color: var(--color-muted); font-size: 0.78rem; margin-bottom: 0.6rem; }

.conj-table-wrap {
    border: 1px solid var(--color-border);
    border-radius: 12px;
    overflow-x: auto;
    margin: 0.4rem 0 0.2rem;
    -webkit-overflow-scrolling: touch;
}
.conj-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 0.92rem;
}
.conj-table th {
    background: var(--color-card);
    color: var(--color-muted);
    font-weight: 700;
    text-align: left;
    padding: 0.5rem 0.7rem;
    border-bottom: 1px solid var(--color-border);
    white-space: nowrap;
}
.conj-table td {
    padding: 0.45rem 0.7rem;
    border-bottom: 1px solid var(--color-border);
    white-space: nowrap;
}
.conj-table tr:last-child td { border-bottom: none; }
.conj-table tr:nth-child(even) td { background: #FBFBFE; }
.conj-table td.pronoun {
    font-weight: 700;
    color: var(--color-primary);
    white-space: nowrap;
}

.stTextInput input {
    border-radius: 10px !important;
    border-color: var(--color-border) !important;
}
.stTextInput input:focus {
    border-color: var(--color-primary) !important;
    box-shadow: 0 0 0 2px rgba(54,84,181,0.15) !important;
}

.stProgress > div > div > div {
    border-radius: 999px !important;
}
.stProgress > div > div {
    border-radius: 999px !important;
    background: var(--color-card) !important;
}

.badge {
    display: inline-block;
    padding: 0.15rem 0.6rem;
    border-radius: 999px;
    font-size: 0.78rem;
    font-weight: 700;
    background: var(--color-card);
    color: var(--color-muted);
    border: 1px solid var(--color-border);
    margin-right: 0.4rem;
}

.gender-chip {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 28px;
    height: 28px;
    margin-top: 0.35rem;
    border-radius: 7px;
    font-size: 0.72rem;
    font-weight: 900;
}
.gender-chip.m { background: rgba(54, 84, 181, 0.16); color: var(--color-primary); }
.gender-chip.f { background: rgba(176, 141, 87, 0.20); color: var(--color-accent-gold); }
.gender-chip.mf {
    background: linear-gradient(90deg, rgba(54, 84, 181, 0.16) 50%, rgba(176, 141, 87, 0.20) 50%);
    color: var(--color-ink);
    font-size: 0.62rem;
}

.ring-wrap {
    display: inline-flex;
    flex-direction: column;
    align-items: center;
    gap: 0.15rem;
}
.ring-value-box {
    position: relative;
}
.ring-value {
    position: absolute;
    inset: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    font-weight: 800;
    color: #20242E;
}
.ring-title { font-weight: 700; margin-top: 0.3rem; }
.ring-sub { color: var(--color-muted); font-size: 0.85rem; }
</style>
"""

RING_COLOR = "#0CA30C"


def inject_custom_css():
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


def render_hero(title, subtitle):
    st.markdown(
        f'<div class="app-hero">'
        f"<h1>{title}</h1><p>{subtitle}</p>"
        f'<div class="hero-rule"></div>'
        f"</div>",
        unsafe_allow_html=True,
    )


def render_ring(percent, title="", sub="", size=128, stroke=13):
    percent = max(0, min(100, percent))
    color = RING_COLOR

    radius = (size - stroke) / 2
    circumference = 2 * 3.14159265 * radius
    offset = circumference * (1 - percent / 100)
    center = size / 2
    font_size = size * 0.22

    return f"""
    <div class="ring-wrap">
      <div class="ring-value-box" style="width:{size}px;height:{size}px;">
        <svg width="{size}" height="{size}" style="transform:rotate(-90deg);">
          <circle cx="{center}" cy="{center}" r="{radius}" fill="none"
            stroke="var(--color-border)" stroke-width="{stroke}" />
          <circle cx="{center}" cy="{center}" r="{radius}" fill="none"
            stroke="{color}" stroke-width="{stroke}" stroke-linecap="round"
            stroke-dasharray="{circumference:.2f}" stroke-dashoffset="{offset:.2f}" />
        </svg>
        <div class="ring-value" style="font-size:{font_size:.0f}px;">{percent:.0f}%</div>
      </div>
      <div class="ring-title">{title}</div>
      <div class="ring-sub">{sub}</div>
    </div>
    """


def render_conjugation_table_html(pronoun_rows):
    header = "<tr><th>人称</th><th>現在形</th><th>半過去</th><th>複合過去</th><th>大過去</th></tr>"
    body = "".join(
        f'<tr><td class="pronoun">{label}</td><td>{présent}</td><td>{imparfait}</td>'
        f"<td>{compose}</td><td>{plusque}</td></tr>"
        for label, présent, imparfait, compose, plusque in pronoun_rows
    )
    return f'<div class="conj-table-wrap"><table class="conj-table">{header}{body}</table></div>'
