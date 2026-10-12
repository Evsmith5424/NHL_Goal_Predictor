// Correlations measured from the 2025-26 regular season (41 home + 41 road games per team).
// Only correlations at or above MIN_R in strength (and statistically significant) change predictions.
const MIN_R = 0.40;

const CORRELATIONS = [
  { id: "offense",  label: "Goals scored at home vs. on the road",        r: 0.53,  p: 0.002,
    effect: "Offense regressed toward league average (see below)" },
  { id: "diff",     label: "Goal differential at home vs. on the road",   r: 0.56,  p: 0.001,
    effect: "Teams' strength carries across venues, so the model uses full-season ratings at both rinks rather than noisy home-only or road-only splits" },
  { id: "roadGFGA", label: "Goals scored vs. allowed, road games",        r: -0.49, p: 0.004,
    effect: "Describes which teams are good. Both numbers are already in the model, so it doesn't change a game's prediction" },
  { id: "seasonGFGA", label: "Goals scored vs. allowed, full season",     r: -0.44, p: 0.012,
    effect: "Same as above, descriptive only" },
  { id: "defense",  label: "Goals allowed at home vs. on the road",       r: 0.38,  p: 0.031,
    effect: "Below the cutoff, so defense ratings are used as-is" },
  { id: "homeGFGA", label: "Goals scored vs. allowed, home games",        r: -0.21, p: 0.25,
    effect: "Weak and not significant, not used" },
];

// League-wide home/road scoring (a significant difference in averages, paired t-test p = 0.04).
const VENUE = { homeGF: 3.149, roadGF: 3.014 };   // goals per game, 2025-26
