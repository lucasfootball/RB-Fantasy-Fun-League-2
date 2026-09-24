"""Loser's Parlay tracker dashboard.

Reads members.csv and a ledger CSV, renders a scoreboard-style view.
All data logic lives in logic.py; this file is presentation only.
"""

import os
import datetime as dt

import pandas as pd
import streamlit as st

import logic

LEAGUE_NAME = "Loser's Parlay"
SEASON_LABEL = "2026 season"

WIN_GREEN = "#2F855A"
LOSS_RED = "#B23B3B"
PUSH_AMBER = "#B7791F"
NAVY = "#2F6F4F"  # turf-green accent (kept name for the bar-chart call)

st.set_page_config(page_title=LEAGUE_NAME, page_icon="🏈", layout="wide")

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500&family=IBM+Plex+Sans:wght@400;500;600&display=swap');

html, body, [class*="css"], .stMarkdown, .stDataFrame { font-family: 'IBM Plex Sans', sans-serif; }
h1, h2, h3, .hero-verdict, .section-title, .title-row .name, .stMetric label { font-family: 'Space Grotesk', 'IBM Plex Sans', sans-serif; }

.title-row { display:flex; align-items:baseline; gap:.6rem; margin-bottom:.2rem; }
.title-row .name { font-weight:500; font-size:2rem; letter-spacing:.2px; color:#1C1B19; }
.title-row .season { color:#7a746a; font-size:1rem; font-weight:400; }

.hero { border-radius:10px; padding:1.3rem 1.5rem; color:#1C1B19; background:#FFFFFF; margin:.4rem 0 1.2rem 0; border:0.5px solid #e2ddd0; border-left:8px solid #B4ADA0; }
.hero.cashed { border-left-color:#2F855A; }
.hero.near   { border-left-color:#B7791F; }
.hero.missed { border-left-color:#B23B3B; }
.hero.empty  { border-left-color:#B4ADA0; background:#F2EFE7; }
.hero-eyebrow { font-size:.8rem; letter-spacing:.08em; color:#7a746a; margin-bottom:.35rem; }
.hero-verdict { font-size:2.3rem; line-height:1.05; font-weight:500; }
.hero-sub { margin-top:.45rem; font-size:1rem; color:#4b463f; }

.section-title { font-weight:500; font-size:1.15rem; color:#1C1B19; margin:.8rem 0 .3rem 0; }
.note { color:#7a746a; font-size:.85rem; }
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)


# ---- data source ----
st.sidebar.markdown(f"### {LEAGUE_NAME}")
st.sidebar.caption("Weekly loser-funded parlay tracker")

live_legs = logic.load_legs("legs.csv")
default_source = "Sample preview" if logic.is_empty(live_legs) else "Live ledger"
source = st.sidebar.radio(
    "Data source",
    ["Live ledger", "Sample preview"],
    index=["Live ledger", "Sample preview"].index(default_source),
    help="Live reads legs.csv. Sample preview reads sample_legs.csv so you can see a populated season.",
)
legs_path = "legs.csv" if source == "Live ledger" else "sample_legs.csv"

members = logic.load_members("members.csv")
legs = logic.load_legs(legs_path)

try:
    updated = dt.datetime.fromtimestamp(os.path.getmtime(legs_path)).strftime("%b %d, %Y %H:%M")
    st.sidebar.caption(f"Data updated: {updated}")
except OSError:
    pass

with st.sidebar.expander("How to update each week"):
    st.markdown(
        "1. Add 10 rows to `legs.csv`, one per member.\n"
        "2. Fill `result` with W, L, or Push.\n"
        "3. Commit and push. The app redeploys automatically.\n\n"
        "See `README.md` for the row format."
    )


# ---- header ----
st.markdown(
    f'<div class="title-row"><span class="name">{LEAGUE_NAME}</span>'
    f'<span class="season">{SEASON_LABEL}</span></div>',
    unsafe_allow_html=True,
)


# ---- hero verdict ----
def verdict_text(status, losses, total):
    if status == "Cashed":
        return "The parlay cashed", "cashed"
    if status == "Near miss":
        return "Missed by 1 leg", "near"
    return f"Missed by {losses} legs", "missed"


latest = logic.latest_week_detail(legs)
if latest is None:
    st.markdown(
        '<div class="hero empty"><div class="hero-verdict">Season hasn\'t kicked off</div>'
        '<div class="hero-sub">Add week 1 to the ledger and results show up here.</div></div>',
        unsafe_allow_html=True,
    )
else:
    verdict, cls = verdict_text(latest["status"], latest["L"], latest["W"] + latest["L"] + latest["Push"])
    total = latest["W"] + latest["L"] + latest["Push"]
    try:
        nice_date = dt.datetime.strptime(latest["date"], "%Y-%m-%d").strftime("%b %d, %Y")
    except ValueError:
        nice_date = latest["date"]
    st.markdown(
        f'<div class="hero {cls}">'
        f'<div class="hero-eyebrow">WEEK {latest["week"]} · {nice_date}</div>'
        f'<div class="hero-verdict">{verdict}</div>'
        f'<div class="hero-sub">{latest["W"]} of {total} legs hit · funded by {latest["funder"]}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )


# ---- metrics row ----
standings = logic.member_standings(legs, members)
summary = logic.season_summary(legs)


def hottest_hand(standings_df):
    best_name, best_len = None, 0
    for _, r in standings_df.iterrows():
        s = r["Streak"]
        if isinstance(s, str) and s.startswith("W"):
            try:
                n = int(s[1:])
            except ValueError:
                continue
            if n > best_len:
                best_name, best_len = r["Member"], n
    return f"{best_name} (W{best_len})" if best_name else "-"


c1, c2, c3, c4 = st.columns(4)
c1.metric("Weeks logged", summary["weeks"])
c2.metric("Parlays cashed", f'{summary["cashed"]} / {summary["weeks"]}' if summary["weeks"] else "0 / 0")
c3.metric("Near misses", summary["near_miss"])
c4.metric("Hottest hand", hottest_hand(standings))


# ---- weekly legs (filterable, defaults to the active week) ----
st.markdown('<div class="section-title">Weekly legs</div>', unsafe_allow_html=True)


def color_result(val):
    return {
        "W": f"background-color:{WIN_GREEN}; color:white; font-weight:600; text-align:center;",
        "L": f"background-color:{LOSS_RED}; color:white; font-weight:600; text-align:center;",
        "Push": f"background-color:{PUSH_AMBER}; color:white; font-weight:600; text-align:center;",
    }.get(val, "")


weeks = logic.available_weeks(legs)
if weeks:
    sel = st.selectbox("Show week", weeks, index=0, format_func=lambda w: f"Week {w}")
    wk = logic.week_detail(legs, sel)
    verdict = {
        "Cashed": "Cashed",
        "Near miss": "Missed by 1 leg",
        "Missed": f"Missed by {wk['L']} legs",
    }[wk["status"]]
    payout = ""
    if wk["payout_10"] is not None:
        price = logic.fmt_odds(wk["price_american"]) if wk["price_american"] else ""
        note = "" if wk["legs_priced"] == len(wk["legs"]) else f" ({wk['legs_priced']} of {len(wk['legs'])} priced)"
        payout = f" · if all hit: {price} → $10 pays ${wk['payout_10']:,.2f}{note}"
    st.caption(f"{wk['date']} · funded by {wk['funder']} · {verdict}{payout}")

    legs_tbl = wk["legs"].rename(columns={
        "submitter": "Member", "leg": "Leg", "bet_type": "Type",
        "odds": "Odds", "result": "Result", "outcome": "Outcome",
    })
    legs_tbl["Type"] = legs_tbl["Type"].map({"game_line": "Game line", "prop": "Prop"}).fillna(legs_tbl["Type"])
    legs_tbl["Odds"] = legs_tbl["Odds"].map(logic.fmt_odds)
    legs_tbl = legs_tbl[["Member", "Leg", "Type", "Odds", "Result", "Outcome"]]
    st.dataframe(
        legs_tbl.style.map(color_result, subset=["Result"]),
        width="stretch", hide_index=True,
    )
else:
    st.info("Add week 1 to the ledger and the weekly legs show up here.")


# ---- standings ----
st.markdown('<div class="section-title">Standings</div>', unsafe_allow_html=True)
st.caption("Hit rate excludes pushes. Streak skips pushes rather than breaking on them.")


def color_streak(val):
    if isinstance(val, str) and val.startswith("W"):
        return f"color:{WIN_GREEN}; font-weight:600;"
    if isinstance(val, str) and val.startswith("L"):
        return f"color:{LOSS_RED}; font-weight:600;"
    return "color:#6B7280;"


standings_style = (
    standings.style
    .format({"Hit rate": "{:.0%}"}, na_rep="-")
    .map(color_streak, subset=["Streak"])
    .background_gradient(subset=["Hit rate"], cmap="Greens", vmin=0, vmax=1)
)
st.dataframe(standings_style, width="stretch")


# ---- funding + bet type ----
left, right = st.columns(2)

with left:
    st.markdown('<div class="section-title">Who\'s funded the parlay</div>', unsafe_allow_html=True)
    st.caption("Times each member was the week's lowest scorer, and paid the $10.")
    funding = logic.funding_counts(legs, members)
    try:
        chart_df = funding[funding["Weeks funded"] > 0].set_index("Member")["Weeks funded"]
        if len(chart_df):
            st.bar_chart(chart_df, color=NAVY, horizontal=True)
        else:
            st.info("No weeks funded yet.")
    except Exception:
        st.dataframe(funding, width="stretch", hide_index=True)

with right:
    st.markdown('<div class="section-title">Hit rate by bet type</div>', unsafe_allow_html=True)
    st.caption("Game lines vs player props across every leg logged.")
    bts = logic.bet_type_split(legs)
    if len(bts):
        st.dataframe(
            bts.style.format({"Hit rate": "{:.0%}"}, na_rep="-"),
            width="stretch", hide_index=True,
        )
    else:
        st.info("No legs logged yet.")


# ---- chalk vs longshots ----
st.markdown('<div class="section-title">Chalk vs longshots</div>', unsafe_allow_html=True)
st.caption("Average implied win probability of each member's legs, from the odds. Higher means safer favorites; lower means bigger swings.")
chalk = logic.chalk_ranking(legs, members)
if len(chalk):
    top, bot = chalk.iloc[0], chalk.iloc[-1]
    st.caption(f"Chalkiest: {top['Member']} ({top['Avg implied']:.0%}) · biggest gambler: {bot['Member']} ({bot['Avg implied']:.0%})")
    st.dataframe(
        chalk.style.format({"Avg implied": "{:.0%}"})
        .background_gradient(subset=["Avg implied"], cmap="Blues", vmin=0.3, vmax=0.8),
        width="stretch", hide_index=True,
    )
else:
    st.info("Add odds to the legs and the chalk-vs-longshots ranking appears here.")


# ---- parlay history ----
st.markdown('<div class="section-title">Parlay history</div>', unsafe_allow_html=True)
hist = logic.parlay_history(legs)
if len(hist):
    show = hist.rename(columns={"week": "Week", "date": "Date", "funder": "Funder", "status": "Status"})
    show = show[["Week", "Date", "Funder", "Legs", "W", "L", "Push", "Status"]]

    def color_status(val):
        return {
            "Cashed": f"color:{WIN_GREEN}; font-weight:600;",
            "Near miss": f"color:{PUSH_AMBER}; font-weight:600;",
            "Missed": f"color:{LOSS_RED}; font-weight:600;",
        }.get(val, "")

    st.dataframe(
        show.style.map(color_status, subset=["Status"]),
        width="stretch", hide_index=True,
    )
else:
    st.info("Weekly parlay results will appear here once you log week 1.")


st.markdown(
    '<p class="note">Grading is manual: results are entered by hand each week, not pulled from a sportsbook. '
    'A push voids that leg, so a week cashes when it has zero losses.</p>',
    unsafe_allow_html=True,
)
