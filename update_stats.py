#!/usr/bin/env python3
"""
Rebuild data.js for the NHL Goal Odds page.

1. Team ratings
   - Last season: only games from the trade deadline onward (rosters closest to today's).
   - This season: every game so far, each counted CURRENT_WEIGHT times.
   rate = (CURRENT_WEIGHT * this-season goals + last-season post-deadline goals)
          / (CURRENT_WEIGHT * this-season games + last-season post-deadline games)

2. Rest effects (back-to-back, 1 day of rest, 2+ days of rest)
   Fitted on every game-team row from last season and this season with a
   Poisson regression that uses each game's expected goals as the offset:
     goals ~ Poisson(expected * scoring[own rest] * allowed[opponent rest])
   "expected" already accounts for both teams' strength and home ice, so the
   factors measure only the effect of rest. A factor is used in predictions
   only if it differs from 1.00 with p < REST_MAX_P.

Standard library only. Run:  python scripts/update_stats.py
"""
import json
import math
import os
import sys
import urllib.parse
import urllib.request
from collections import defaultdict
from datetime import date, datetime, timezone

CURRENT_WEIGHT = float(os.environ.get("CURRENT_WEIGHT", "3"))
REST_MAX_P = float(os.environ.get("REST_MAX_P", "0.05"))
API = "https://api.nhle.com/stats/rest/en"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data.js")

# Trade deadline for each season (first day whose games count). Add new seasons here.
TRADE_DEADLINES = {
    "20242025": "2025-03-07",
    "20252026": "2026-03-06",
    "20262027": "2027-03-01",
}
REST_BUCKETS = ["b2b", "1", "2plus"]


# ---------------------------------------------------------------- fetching
def fetch_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": "nhl-goal-odds/2.0"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def team_summary(season_id, since=None):
    exp = f"seasonId={season_id} and gameTypeId=2"
    if since:
        exp += f' and gameDate>="{since}"'
    url = f"{API}/team/summary?" + urllib.parse.urlencode({"cayenneExp": exp})
    return {row["teamId"]: row for row in fetch_json(url).get("data", [])}


def team_games(season_id):
    """One row per team per game (each game appears twice)."""
    rows, start, page = [], 0, 500
    sort = json.dumps([{"property": "gameId", "direction": "ASC"},
                       {"property": "teamId", "direction": "ASC"}])
    while True:
        q = urllib.parse.urlencode({
            "isAggregate": "false", "isGame": "true", "start": start, "limit": page,
            "sort": sort, "cayenneExp": f"seasonId={season_id} and gameTypeId=2",
        })
        data = fetch_json(f"{API}/team/summary?{q}")
        batch = data.get("data", [])
        rows += batch
        start += page
        if not batch or start >= data.get("total", 0):
            break
    return rows


def season_ids(today):
    start = today.year if today.month >= 9 else today.year - 1
    return f"{start}{start + 1}", f"{start - 1}{start}"


def label(sid):
    return f"{sid[:4]}-{sid[6:]}"


# ---------------------------------------------------------------- team ratings
def weighted_teams(cur, prev, tricodes):
    teams = []
    for tid, p in prev.items():
        c = cur.get(tid)
        gp_c = c["gamesPlayed"] if c else 0
        gp_p = p["gamesPlayed"]
        wc, wp = CURRENT_WEIGHT * gp_c, gp_p
        tot = wc + wp
        mix = lambda ck, pk=None: ((wc * c[ck] if c else 0) + wp * p[pk or ck]) / tot
        teams.append({
            "ab": tricodes.get(tid, p["teamFullName"][:3].upper()),
            "name": (c or p)["teamFullName"],
            "gf": round(((CURRENT_WEIGHT * c["goalsFor"] if c else 0) + p["goalsFor"]) / tot, 3),
            "ga": round(((CURRENT_WEIGHT * c["goalsAgainst"] if c else 0) + p["goalsAgainst"]) / tot, 3),
            "pp": round(mix("powerPlayPct") * 100, 1),
            "pk": round(mix("penaltyKillPct") * 100, 1),
            "pts": c["points"] if c else 0,
            "gp": gp_c,
            "prevGp": gp_p,
            "w": round(wc / tot, 3),
            "cur": {"gf": round(c["goalsForPerGame"], 3), "ga": round(c["goalsAgainstPerGame"], 3)} if c else None,
            "prev": {"gf": round(p["goalsFor"] / gp_p, 3), "ga": round(p["goalsAgainst"] / gp_p, 3)},
        })
    teams.sort(key=lambda t: t["name"])
    return teams


# ---------------------------------------------------------------- rest model
def bucket(days):
    if days is None:
        return None
    return "b2b" if days == 0 else "1" if days == 1 else "2plus"


def tag_rest(rows):
    """Adds 'rest' (own) and 'oppRest' to each row. Days of rest = days between games - 1."""
    by_team = defaultdict(list)
    for r in rows:
        by_team[r["teamFullName"]].append(r)
    rest_of = {}
    for name, games in by_team.items():
        games.sort(key=lambda r: r["gameDate"])
        prev = None
        for g in games:
            d = date.fromisoformat(g["gameDate"][:10])
            rest_of[(g["gameId"], g["teamId"])] = bucket(None if prev is None else (d - prev).days - 1)
            prev = d
    by_game = defaultdict(list)
    for r in rows:
        r["rest"] = rest_of[(r["gameId"], r["teamId"])]
        by_game[r["gameId"]].append(r)
    for pair in by_game.values():
        if len(pair) == 2:
            pair[0]["oppRest"], pair[1]["oppRest"] = pair[1]["rest"], pair[0]["rest"]
        else:
            for r in pair:
                r["oppRest"] = None
    return [r for r in rows if "oppRest" in r]


def add_expected(rows):
    """Expected goals for each row from season ratings and home ice, without rest."""
    gf, ga, gp = defaultdict(float), defaultdict(float), defaultdict(int)
    home_g = road_g = home_n = road_n = 0
    for r in rows:
        gf[r["teamFullName"]] += r["goalsFor"]
        ga[r["teamFullName"]] += r["goalsAgainst"]
        gp[r["teamFullName"]] += 1
        if r["homeRoad"] == "H":
            home_g += r["goalsFor"]; home_n += 1
        else:
            road_g += r["goalsFor"]; road_n += 1
    league = sum(gf.values()) / sum(gp.values())
    home_f, road_f = (home_g / home_n) / league, (road_g / road_n) / league
    # opponent full name from abbreviation, via the paired row
    name_by_game = defaultdict(dict)
    for r in rows:
        name_by_game[r["gameId"]][r["teamId"]] = r["teamFullName"]
    for r in rows:
        opp = [n for tid, n in name_by_game[r["gameId"]].items() if tid != r["teamId"]]
        if not opp:
            r["exp"] = None
            continue
        att = (gf[r["teamFullName"]] / gp[r["teamFullName"]]) / league
        dfn = (ga[opp[0]] / gp[opp[0]]) / league
        r["exp"] = att * dfn * league * (home_f if r["homeRoad"] == "H" else road_f)
    return home_g / home_n, road_g / road_n


def fit_rest(rows):
    rows = [r for r in rows if r.get("exp") and r["rest"] and r["oppRest"]]
    score = {b: 1.0 for b in REST_BUCKETS}    # own rest -> goals scored
    allow = {b: 1.0 for b in REST_BUCKETS}    # own rest -> goals the opponent scores
    for _ in range(50):                        # alternating Poisson MLE (converges fast)
        for b in REST_BUCKETS:
            o = sum(r["goalsFor"] for r in rows if r["rest"] == b)
            e = sum(r["exp"] * allow[r["oppRest"]] for r in rows if r["rest"] == b)
            score[b] = o / e if e else 1.0
        for b in REST_BUCKETS:
            o = sum(r["goalsFor"] for r in rows if r["oppRest"] == b)
            e = sum(r["exp"] * score[r["rest"]] for r in rows if r["oppRest"] == b)
            allow[b] = o / e if e else 1.0
    out = {}
    for b in REST_BUCKETS:
        n = sum(1 for r in rows if r["rest"] == b)
        g_s = sum(r["goalsFor"] for r in rows if r["rest"] == b)
        g_a = sum(r["goalsFor"] for r in rows if r["oppRest"] == b)
        out[b] = {"games": n, "scoring": stat(score[b], g_s), "allowed": stat(allow[b], g_a)}
    return out, len(rows)


def stat(f, goals):
    """Factor with 95% CI and p-value vs 1.00 (Poisson: SE of log factor = 1/sqrt(goals))."""
    se = 1 / math.sqrt(goals) if goals else float("inf")
    z = math.log(f) / se if goals else 0
    p = math.erfc(abs(z) / math.sqrt(2))
    return {"f": round(f, 4), "lo": round(math.exp(math.log(f) - 1.96 * se), 4),
            "hi": round(math.exp(math.log(f) + 1.96 * se), 4), "p": round(p, 4),
            "used": p < REST_MAX_P}


# ---------------------------------------------------------------- output
def write(meta, teams, rest):
    lines = [
        "// Generated by scripts/update_stats.py. Edits here are overwritten on the next update.",
        "const META = " + json.dumps(meta, ensure_ascii=False) + ";",
        "const REST = " + json.dumps(rest, ensure_ascii=False) + ";",
        "const TEAMS = [",
        *["  " + json.dumps(t, ensure_ascii=False) + "," for t in teams],
        "];",
        "",
    ]
    with open(OUT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def main():
    cur_id, prev_id = season_ids(datetime.now(timezone.utc))
    deadline = TRADE_DEADLINES.get(prev_id, f"{prev_id[4:]}-03-01")
    tricodes = {t["id"]: t["triCode"] for t in fetch_json(f"{API}/team")["data"]}

    prev = team_summary(prev_id, since=deadline)
    if len(prev) < 32:
        raise SystemExit(f"Expected 32 teams after the {prev_id} deadline, got {len(prev)}. Not updating.")
    try:
        cur = team_summary(cur_id)
    except Exception as e:
        print(f"Could not load {cur_id}: {e}. Using last season only.", file=sys.stderr)
        cur = {}
    teams = weighted_teams(cur, prev, tricodes)

    rows = []
    for sid in (prev_id, cur_id):
        try:
            season_rows = tag_rest(team_games(sid))
            if season_rows:
                add_expected(season_rows)
            for r in season_rows:
                r["season"] = sid
            rows += season_rows
        except Exception as e:
            print(f"Game log for {sid} unavailable: {e}", file=sys.stderr)
    full_prev = [r for r in rows if r["season"] == prev_id] or rows
    home_gf = sum(r["goalsFor"] for r in full_prev if r["homeRoad"] == "H") / max(1, sum(1 for r in full_prev if r["homeRoad"] == "H"))
    road_gf = sum(r["goalsFor"] for r in full_prev if r["homeRoad"] == "R") / max(1, sum(1 for r in full_prev if r["homeRoad"] == "R"))
    rest, n_rows = fit_rest(rows) if rows else (None, 0)

    meta = {
        "season": label(cur_id), "lastSeason": label(prev_id), "deadline": deadline,
        "currentWeight": CURRENT_WEIGHT, "updated": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "avgGamesPlayed": round(sum(t["gp"] for t in teams) / len(teams), 1),
        "avgPrevGames": round(sum(t["prevGp"] for t in teams) / len(teams), 1),
        "restRows": n_rows, "restMaxP": REST_MAX_P,
        "venue": {"homeGF": round(home_gf, 3), "roadGF": round(road_gf, 3)} if rows else None,
    }
    write(meta, teams, rest)
    print(f"Wrote {len(teams)} teams; rest model fitted on {n_rows} team-games.")
    if rest:
        for b in REST_BUCKETS:
            r = rest[b]
            print(f"  {b:6s} n={r['games']:5d}  scoring x{r['scoring']['f']:.3f} (p={r['scoring']['p']:.3f})"
                  f"  allowed x{r['allowed']['f']:.3f} (p={r['allowed']['p']:.3f})")


if __name__ == "__main__":
    main()
