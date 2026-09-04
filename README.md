# Loser's Parlay Tracker

A scoreboard for the league's weekly loser-funded parlay. The lowest scorer each
week funds a $10 parlay, all 10 members pick a leg, and this dashboard tracks who
hit, who missed, and how everyone stacks up across the season.

Grading is manual: you enter each leg's result by hand. No sportsbook API is
required.

## Files

| File | What it is |
| --- | --- |
| `app.py` | The Streamlit dashboard (presentation only) |
| `logic.py` | Pure data logic: standings, funding, history, streaks |
| `members.csv` | The 10-person roster and display handles |
| `legs.csv` | The season ledger. You edit this each week. |
| `sample_legs.csv` | Fake 4-week season, for previewing the populated view |
| `test_logic.py` | Checks the stats compute correctly (`python test_logic.py`) |
| `.streamlit/config.toml` | Theme |
| `requirements.txt` | Dependencies |

Two members are named David, so the roster uses `David S.` (Scherrer) and
`David B.` (Beato) as handles. Use those exact handles in the ledger.

## Deploy (public, obscure URL)

Streamlit Community Cloud has no true link-only mode. A public app is technically
public, but with an obscure URL and no badge or gallery listing, only people you
send the link to will realistically find it.

1. Create a **public** GitHub repo and push these files to it.
2. Go to share.streamlit.io, sign in with GitHub, and click **Create app**.
3. Point it at your repo, branch `main`, main file `app.py`.
4. Set a non-obvious custom subdomain (avoid your league name). Don't add the
   Streamlit badge to the repo and don't post it to the gallery.
5. Deploy. Share the URL with the league.

The app redeploys automatically every time you push to the repo, so updating the
ledger updates the dashboard.

## Update each week

Add 10 rows to `legs.csv`, one per member, then commit and push. Row format:

| column | value |
| --- | --- |
| `week` | week number, e.g. `5` |
| `date` | `YYYY-MM-DD` of that NFL week |
| `funder` | handle of the week's lowest scorer (who paid the $10) |
| `submitter` | handle of the member who picked the leg |
| `leg` | free text, e.g. `Bills -3.5` or `CMC over 89.5 scrim yds` |
| `bet_type` | `game_line` or `prop` |
| `result` | `W`, `L`, or `Push` |
| `outcome` | optional free text, the actual result for the record |

Example week:

```
5,2025-10-05,David B.,Lucas,Bills -3.5,game_line,W,Bills won by 10
5,2025-10-05,David B.,Ryan,Mahomes over 275.5 pass yds,prop,L,241 pass yds
...eight more rows...
```

## Conventions

- Hit rate excludes pushes: `W / (W + L)`.
- A streak skips pushes rather than breaking on them.
- Parlay result: a push voids that leg and the parlay plays on, so a week
  **Cashed** at zero losses, is a **Near miss** at exactly one loss, and
  **Missed** at two or more.

## Preview before week 1

The ledger starts empty, so the live dashboard shows empty states until you log
week 1. To see the populated version, use the sidebar **Data source** toggle and
pick **Sample preview**, which reads `sample_legs.csv`.

## Run locally

```
pip install -r requirements.txt
streamlit run app.py
```

## Next

- Weekly recap email drafted from the same ledger (distribution, decided later).
- Optional NFL API enrichment to auto-attach the real final line or stat next to
  each leg, or to semi-auto-grade the game-line legs.
