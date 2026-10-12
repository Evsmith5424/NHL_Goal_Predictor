# NHL Goal Odds

A small web page that predicts how many goals two NHL teams will score against each other. Pick any two teams and it shows:

- Expected goals for each team and the expected total
- The probability of each team scoring 0, 1, 2 … 8+ goals
- The probability of each total goal count, 0 … 12+
- "Or more" probabilities (useful for over/under lines)
- Who leads after 60 minutes, and the chance the game goes to overtime
- Offense and defense rankings for all 32 teams

No build step, no dependencies. It's plain HTML, CSS and JavaScript.

## How the model works

1. **League average** = the mean goals per game across all 32 teams.
2. **Attack rating** = a team's goals for per game ÷ league average.
3. **Defense rating** = a team's goals against per game ÷ league average.
4. **Expected goals** for Team 1 = Team 1 attack × Team 2 defense × league average (and vice versa).
5. Each team's goals follow a **Poisson distribution** with that expected value. Total goals is Poisson with the two expected values added together.
6. Regulation win/tie probabilities come from combining both teams' distributions.

### Correlation adjustments

Only correlations of moderate strength or more (|r| ≥ 0.40, p < 0.05) change predictions. They're listed in `model-config.js` and were measured on 2025-26 home and road splits.

| Relationship | r | Used? | Effect |
|---|---|---|---|
| Goals scored, home vs. road | 0.53 | Yes | Offense regressed to the mean: Spearman-Brown 2r/(1+r) ≈ 69% of a team's scoring edge is kept |
| Goal differential, home vs. road | 0.56 | Yes | Strength carries across venues, so one league-wide home-ice factor is used instead of team-specific splits |
| Goals scored vs. allowed, road | −0.49 | Descriptive | Both numbers are already in the model |
| Goals scored vs. allowed, season | −0.44 | Descriptive | Same |
| Goals allowed, home vs. road | 0.38 | No | Below cutoff, so defense ratings are used as-is |
| Goals scored vs. allowed, home | −0.21 | No | Weak, not significant |

Home-ice edge: home teams scored 3.15 goals a game vs. 3.01 for road teams (paired t-test p = 0.04). When you pick a home team, its expected goals are multiplied by 1.022 and the visitor's by 0.978. Change `MIN_R` in `model-config.js` to make the cutoff stricter or looser.

### Limitations

- Uses season averages, blended with last season early on
- Same home-ice factor for every team
- Ignores goalies, injuries, schedule and roster changes
- Covers regulation time only

## Run it locally

Open `index.html` in any browser. That's it.

## Publish with GitHub Pages

1. Push this folder to a GitHub repository.
2. In the repo, go to **Settings → Pages**.
3. Under **Build and deployment**, set Source to **Deploy from a branch**, pick `main` and `/ (root)`, and save.
4. Your site will be live at `https://<your-username>.github.io/<repo-name>/` within a minute or two.

## Automatic weekly updates

A GitHub Action (`.github/workflows/update-stats.yml`) runs every Monday at 11:00 UTC. It runs `scripts/update_stats.py`, which:

1. Downloads this season's and last season's team stats from the NHL stats API.
2. Blends them for each team (see below).
3. Rewrites `data.js` and commits it if anything changed. GitHub Pages then redeploys the site.

To run it right away, open the **Actions** tab, pick **Update NHL stats**, and click **Run workflow**.

> If the Actions tab says workflows are disabled, enable them there. The workflow already has permission to push (`contents: write`). If your repo or organization restricts that, go to **Settings → Actions → General → Workflow permissions** and choose **Read and write permissions**.

### How the two seasons are blended

A handful of games can make a team look far better or worse than it is, so each team's goals for, goals against, power play and penalty kill are a weighted mix:

```
weight on this season = min(games played this season / 25, 1)
blended = weight × this season + (1 − weight) × last season
```

| Games played | This season | Last season |
|---|---|---|
| 0 | 0% | 100% |
| 5 | 20% | 80% |
| 10 | 40% | 60% |
| 20 | 80% | 20% |
| 25+ | 100% | 0% |

Change `RAMP_GAMES` in the workflow file to make the switch faster or slower. Seasons roll over automatically: from September on, the script treats the new season as "this season".

### Running the update yourself

```
python scripts/update_stats.py
```

Needs Python 3.8+ and no extra packages.

## Files

| File | What it does |
|---|---|
| `index.html` | Page layout |
| `styles.css` | Styling, including light and dark mode |
| `data.js` | Blended team stats (generated, don't edit by hand) |
| `app.js` | Poisson model, probability tables and rankings |
| `model-config.js` | Correlations, cutoff and home/road scoring rates |
| `scripts/update_stats.py` | Downloads stats and rebuilds `data.js` |
| `.github/workflows/update-stats.yml` | Runs the update every Monday |

## Data source

NHL regular-season team stats from the NHL Stats API (api.nhle.com).
