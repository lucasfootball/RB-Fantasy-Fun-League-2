"""Pure data logic for the parlay tracker.

No Streamlit imports here on purpose, so these functions can be unit tested
and reused. app.py handles all presentation.

Data contract (legs.csv), one row per leg per week:
    week       int
    date       YYYY-MM-DD
    funder     display handle of the week's lowest scorer
    submitter  display handle of the member who picked the leg
    leg        free-text description of the bet
    bet_type   game_line | prop
    odds       American odds for the leg, e.g. -110 or +140 (optional)
    result     W | L | Push
    outcome    optional free-text: the actual result, for the record

Grading is manual: whatever you type in `result` is trusted as-is.

Parlay convention: a push voids that leg and the parlay plays on, so a week
"Cashed" when it has zero losses. Exactly one loss is a "Near miss".
"""

import pandas as pd

RESULT_WIN = "W"
RESULT_LOSS = "L"
RESULT_PUSH = "Push"
VALID_RESULTS = {RESULT_WIN, RESULT_LOSS, RESULT_PUSH}
VALID_BET_TYPES = {"game_line", "prop"}

LEDGER_COLUMNS = [
    "week", "date", "funder", "submitter", "leg", "bet_type", "odds", "result", "outcome"
]


def load_members(path="members.csv"):
    df = pd.read_csv(path, dtype=str).fillna("")
    df["display"] = df["display"].str.strip()
    df["full_name"] = df["full_name"].str.strip()
    return df


def load_legs(path="legs.csv"):
    """Load and normalize the ledger. Returns an empty, correctly-typed frame
    when the file has only a header."""
    df = pd.read_csv(path, dtype=str)
    for col in LEDGER_COLUMNS:
        if col not in df.columns:
            df[col] = pd.Series(dtype="object")
    df = df[LEDGER_COLUMNS].copy()

    # Drop blank rows, normalize text.
    df = df.dropna(how="all")
    for col in ["funder", "submitter", "leg", "bet_type", "result", "outcome", "date"]:
        df[col] = df[col].fillna("").astype(str).str.strip()
    df = df[df["submitter"] != ""]

    if df.empty:
        df["week"] = pd.Series(dtype="Int64")
        return df

    df["week"] = pd.to_numeric(df["week"], errors="coerce").astype("Int64")
    df["result"] = df["result"].str.capitalize().replace({"Win": "W", "Loss": "L"})
    # Single letters lose their case above (W -> W, L -> L already fine).
    df["result"] = df["result"].replace({"W": "W", "L": "L", "Push": "Push"})
    df["bet_type"] = df["bet_type"].str.lower().str.replace(" ", "_")
    odds_raw = df["odds"].fillna("").astype(str).str.replace("+", "", regex=False).str.strip()
    df["odds"] = pd.to_numeric(odds_raw, errors="coerce").astype("Int64")
    return df.sort_values(["week"]).reset_index(drop=True)


def is_empty(legs):
    return legs is None or len(legs) == 0


def _wlp(sub):
    w = int((sub["result"] == RESULT_WIN).sum())
    l = int((sub["result"] == RESULT_LOSS).sum())
    p = int((sub["result"] == RESULT_PUSH).sum())
    return w, l, p


def _hit_rate(w, l):
    denom = w + l
    return (w / denom) if denom else None


def implied_prob(odds):
    """American odds -> implied win probability (0-1). None for missing."""
    if odds is None or pd.isna(odds):
        return None
    o = int(odds)
    return (-o) / (-o + 100) if o < 0 else 100 / (o + 100)


def decimal_odds(odds):
    """American odds -> decimal multiplier. None for missing."""
    if odds is None or pd.isna(odds):
        return None
    o = int(odds)
    return 1 + (o / 100 if o > 0 else 100 / -o)


def american_from_prob(p):
    """Implied probability (0-1) -> representative American odds (int)."""
    if p is None or pd.isna(p) or p <= 0 or p >= 1:
        return None
    return round(-100 * p / (1 - p)) if p >= 0.5 else round(100 * (1 - p) / p)


def fmt_odds(odds):
    """American odds as a signed string, e.g. -110 or +140."""
    if odds is None or pd.isna(odds):
        return "-"
    o = int(odds)
    return f"+{o}" if o > 0 else str(o)


def _streaks(results):
    """Given a week-ordered result series, return (current, longest) as strings
    like 'W4', 'L2', or '-'. Pushes are skipped, not streak-breaking."""
    seq = [r for r in results if r in (RESULT_WIN, RESULT_LOSS)]
    if not seq:
        return "-", "-"

    # Current: trailing run.
    cur_val = seq[-1]
    cur_len = 0
    for r in reversed(seq):
        if r == cur_val:
            cur_len += 1
        else:
            break
    current = f"{cur_val}{cur_len}"

    # Longest of either type.
    best_val, best_len = seq[0], 1
    run_val, run_len = seq[0], 1
    for r in seq[1:]:
        if r == run_val:
            run_len += 1
        else:
            run_val, run_len = r, 1
        if run_len > best_len:
            best_val, best_len = run_val, run_len
    longest = f"{best_val}{best_len}"
    return current, longest


def member_standings(legs, members):
    """One row per member with record, hit rate, streaks. Members with no legs
    show zeros so the table is full even on a fresh start."""
    rows = []
    for _, m in members.iterrows():
        name = m["display"]
        sub = legs[legs["submitter"] == name].sort_values("week") if not is_empty(legs) else legs.iloc[0:0]
        w, l, p = _wlp(sub) if len(sub) else (0, 0, 0)
        hr = _hit_rate(w, l)
        cur, longest = _streaks(list(sub["result"])) if len(sub) else ("-", "-")
        rows.append({
            "Member": name,
            "Legs": w + l + p,
            "W": w,
            "L": l,
            "Push": p,
            "Hit rate": hr,
            "Streak": cur,
            "Longest": longest,
        })
    df = pd.DataFrame(rows)
    # Sort by hit rate desc (Nones last), then wins.
    df = df.sort_values(
        by=["Hit rate", "W"], ascending=[False, False], na_position="last"
    ).reset_index(drop=True)
    df.index = df.index + 1
    df.index.name = "Rank"
    return df


def funding_counts(legs, members):
    """How many weeks each member funded the parlay (was lowest scorer)."""
    if is_empty(legs):
        base = pd.DataFrame({"Member": members["display"], "Weeks funded": 0})
        return base.sort_values("Member").reset_index(drop=True)
    per_week = legs.dropna(subset=["week"]).groupby("week")["funder"].first()
    counts = per_week.value_counts()
    rows = [{"Member": m, "Weeks funded": int(counts.get(m, 0))}
            for m in members["display"]]
    return (pd.DataFrame(rows)
            .sort_values(["Weeks funded", "Member"], ascending=[False, True])
            .reset_index(drop=True))


def parlay_history(legs):
    """One row per week: counts and a status (Cashed / Near miss / Missed)."""
    if is_empty(legs):
        return pd.DataFrame(columns=["week", "date", "funder", "Legs", "W", "L", "Push", "status"])
    rows = []
    for wk, sub in legs.dropna(subset=["week"]).groupby("week"):
        w, l, p = _wlp(sub)
        status = "Cashed" if l == 0 else ("Near miss" if l == 1 else "Missed")
        rows.append({
            "week": int(wk),
            "date": sub["date"].iloc[0],
            "funder": sub["funder"].iloc[0],
            "Legs": len(sub),
            "W": w, "L": l, "Push": p,
            "status": status,
        })
    return pd.DataFrame(rows).sort_values("week").reset_index(drop=True)


def bet_type_split(legs):
    """Hit rate by bet type."""
    if is_empty(legs):
        return pd.DataFrame(columns=["Bet type", "W", "L", "Push", "Hit rate"])
    rows = []
    label = {"game_line": "Game lines", "prop": "Player props"}
    for bt, sub in legs.groupby("bet_type"):
        w, l, p = _wlp(sub)
        rows.append({
            "Bet type": label.get(bt, bt or "Unspecified"),
            "W": w, "L": l, "Push": p,
            "Hit rate": _hit_rate(w, l),
        })
    return pd.DataFrame(rows).sort_values("Bet type").reset_index(drop=True)


def chalk_ranking(legs, members):
    """Per member, average implied win probability of their legs (needs odds).
    Higher = chalkier (safe favorites); lower = longshots. Easiest first."""
    cols = ["Member", "Priced legs", "Avg implied", "Typical line"]
    if is_empty(legs):
        return pd.DataFrame(columns=cols)
    rows = []
    for _, m in members.iterrows():
        name = m["display"]
        sub = legs[legs["submitter"] == name]
        probs = [implied_prob(o) for o in sub["odds"] if not pd.isna(o)]
        if not probs:
            continue
        avg = sum(probs) / len(probs)
        rows.append({
            "Member": name,
            "Priced legs": len(probs),
            "Avg implied": avg,
            "Typical line": fmt_odds(american_from_prob(avg)),
        })
    if not rows:
        return pd.DataFrame(columns=cols)
    return (pd.DataFrame(rows)
            .sort_values("Avg implied", ascending=False)
            .reset_index(drop=True))


def season_summary(legs):
    """Headline numbers for the metrics row."""
    hist = parlay_history(legs)
    if hist.empty:
        return {"weeks": 0, "cashed": 0, "near_miss": 0, "latest_week": None}
    return {
        "weeks": len(hist),
        "cashed": int((hist["status"] == "Cashed").sum()),
        "near_miss": int((hist["status"] == "Near miss").sum()),
        "latest_week": int(hist["week"].max()),
    }


def available_weeks(legs):
    """Logged week numbers, most recent first."""
    if is_empty(legs):
        return []
    return sorted((int(w) for w in legs["week"].dropna().unique()), reverse=True)


def week_detail(legs, wk):
    """One week's rows plus its funder and status."""
    if is_empty(legs):
        return None
    sub = legs[legs["week"] == wk].copy()
    if sub.empty:
        return None
    w, l, p = _wlp(sub)
    status = "Cashed" if l == 0 else ("Near miss" if l == 1 else "Missed")
    priced = [decimal_odds(o) for o in sub["odds"] if not pd.isna(o)]
    combined = 1.0
    for d in priced:
        combined *= d
    payout_10 = round(10 * combined, 2) if priced else None
    price_american = american_from_prob(1 / combined) if priced and combined > 1 else None
    return {
        "week": int(wk),
        "date": sub["date"].iloc[0],
        "funder": sub["funder"].iloc[0],
        "status": status,
        "W": w, "L": l, "Push": p,
        "legs_priced": len(priced),
        "payout_10": payout_10,
        "price_american": price_american,
        "legs": sub[["submitter", "leg", "bet_type", "odds", "result", "outcome"]],
    }


def latest_week_detail(legs):
    """The most recent week's detail, for the hero."""
    if is_empty(legs):
        return None
    return week_detail(legs, int(legs["week"].max()))
