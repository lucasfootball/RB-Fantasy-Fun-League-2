"""Quick checks for the parlay logic. Run: python test_logic.py"""
import logic

members = logic.load_members("members.csv")


def check(label, cond):
    print(("PASS" if cond else "FAIL"), "-", label)
    assert cond, label


print("== SAMPLE DATA ==")
legs = logic.load_legs("sample_legs.csv")
check("40 legs loaded", len(legs) == 40)

st = logic.member_standings(legs, members)
print(st.to_string())
ryan = st[st["Member"] == "Ryan"].iloc[0]
check("Ryan is 4-0-0", (ryan["W"], ryan["L"], ryan["Push"]) == (4, 0, 0))
check("Ryan streak W4", ryan["Streak"] == "W4")
ben = st[st["Member"] == "Ben"].iloc[0]
check("Ben has a push and W3 streak (push skipped)", ben["Push"] == 1 and ben["Streak"] == "W3")
adam = st[st["Member"] == "Adam"].iloc[0]
check("Adam 2-2 hit rate 0.5", adam["W"] == 2 and adam["L"] == 2 and abs(adam["Hit rate"] - 0.5) < 1e-9)

print()
fund = logic.funding_counts(legs, members)
print(fund.to_string(index=False))
check("Adam funded once", int(fund[fund["Member"] == "Adam"]["Weeks funded"].iloc[0]) == 1)
check("four distinct funders", int((fund["Weeks funded"] > 0).sum()) == 4)

print()
hist = logic.parlay_history(legs)
print(hist.to_string(index=False))
statuses = dict(zip(hist["week"], hist["status"]))
check("W1 Missed", statuses[1] == "Missed")
check("W2 Cashed", statuses[2] == "Cashed")
check("W3 Near miss", statuses[3] == "Near miss")
check("W4 Missed", statuses[4] == "Missed")

print()
summary = logic.season_summary(legs)
print("summary:", summary)
check("summary weeks 4", summary["weeks"] == 4)
check("summary cashed 1", summary["cashed"] == 1)
check("summary latest week 4", summary["latest_week"] == 4)

print()
bts = logic.bet_type_split(legs)
print(bts.to_string(index=False))
check("bet-type counts sum to 40", int(bts[["W", "L", "Push"]].values.sum()) == 40)

print()
latest = logic.latest_week_detail(legs)
check("latest week is 4, funded by David B.", latest["week"] == 4 and latest["funder"] == "David B.")
check("latest week has 10 legs", len(latest["legs"]) == 10)

print("\n== EMPTY DATA (fresh start) ==")
empty = logic.load_legs("legs.csv")
check("empty ledger", logic.is_empty(empty))
st0 = logic.member_standings(empty, members)
check("standings still lists 10 members", len(st0) == 10)
check("all zeros", int(st0[["W", "L", "Push"]].values.sum()) == 0)
check("empty season summary", logic.season_summary(empty)["weeks"] == 0)
check("no latest week", logic.latest_week_detail(empty) is None)

print("\nALL CHECKS PASSED")
