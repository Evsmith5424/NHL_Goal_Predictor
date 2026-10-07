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

### Limitations

- Uses full-season averages from the 2025-26 regular season
- Neutral rink (no home-ice advantage)
- Ignores goalies, injuries, schedule and roster changes
- Covers regulation time only

## Run it locally

Open `index.html` in any browser. That's it.

## Publish with GitHub Pages

1. Push this folder to a GitHub repository.
2. In the repo, go to **Settings → Pages**.
3. Under **Build and deployment**, set Source to **Deploy from a branch**, pick `main` and `/ (root)`, and save.
4. Your site will be live at `https://<your-username>.github.io/<repo-name>/` within a minute or two.

## Updating the stats

All team numbers live in [`data.js`](data.js). Each row is:

```js
["COL", "Colorado Avalanche", 3.63, 2.40, 17.1, 84.6, 121],
//  abbr, name,               GF/GP, GA/GP, PP%, PK%, points
```

Current numbers are available from the NHL stats API:

```
https://api.nhle.com/stats/rest/en/team/summary?cayenneExp=seasonId=20262027%20and%20gameTypeId=2
```

Use `goalsForPerGame`, `goalsAgainstPerGame`, `powerPlayPct`, `penaltyKillPct` and `points` from each team's entry (multiply the two percentages by 100).

## Files

| File | What it does |
|---|---|
| `index.html` | Page layout |
| `styles.css` | Styling, including light and dark mode |
| `data.js` | Team stats |
| `app.js` | Poisson model, probability tables and rankings |

## Data source

2025-26 NHL regular season team stats from the NHL Stats API (api.nhle.com).
