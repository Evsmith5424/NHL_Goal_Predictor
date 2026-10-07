
const LEAGUE = TEAMS.reduce((s,t)=>s+t.gf,0) / TEAMS.length;
const byAb = Object.fromEntries(TEAMS.map(t=>[t.ab,t]));

function expected(att, def) { return (att.gf / LEAGUE) * (def.ga / LEAGUE) * LEAGUE; }
function poisson(lambda, maxK) {
  const p = []; let v = Math.exp(-lambda);
  for (let k = 0; k <= maxK; k++) { p.push(v); v = v * lambda / (k + 1); }
  return p;
}
const pct = x => (x * 100 < 0.1 && x > 0) ? "<0.1%" : (x * 100).toFixed(1) + "%";

function distTable(el, lambda, cap) {
  const p = poisson(lambda, cap - 1);
  const rows = p.map((v,k)=>({label: String(k), v}));
  rows.push({label: cap + "+", v: 1 - p.reduce((a,b)=>a+b,0)});
  let tail = 1; const max = Math.max(...rows.map(r=>r.v));
  const mode = rows.findIndex(r=>r.v===max);
  let html = "<thead><tr><th>Goals</th><th></th><th>Exact</th><th>Or more</th></tr></thead><tbody>";
  rows.forEach((r,i)=>{
    const atLeast = tail; tail -= r.v;
    html += `<tr><td class="g">${r.label}</td><td class="barcell"><div class="dbar${i===mode?" top":""}" style="width:${(r.v/max*100).toFixed(1)}%"></div></td><td>${pct(r.v)}</td><td class="cum">${i===rows.length-1?"—":pct(atLeast)}</td></tr>`;
  });
  el.innerHTML = html + "</tbody>";
}

const s1 = document.getElementById("team1"), s2 = document.getElementById("team2");
const opts = [...TEAMS].sort((a,b)=>a.name.localeCompare(b.name)).map(t=>`<option value="${t.ab}">${t.name}</option>`).join("");
s1.innerHTML = opts; s2.innerHTML = opts;
s1.value = "COL"; s2.value = "DAL";

function update() {
  const A = byAb[s1.value], B = byAb[s2.value];
  const l1 = expected(A,B), l2 = expected(B,A);
  document.getElementById("a1").textContent = A.ab;
  document.getElementById("a2").textContent = B.ab;
  document.getElementById("x1").textContent = l1.toFixed(2);
  document.getElementById("x2").textContent = l2.toFixed(2);
  document.getElementById("xt").textContent = (l1+l2).toFixed(2);
  document.getElementById("h1").textContent = A.name;
  document.getElementById("h2").textContent = B.name;
  distTable(document.getElementById("d1"), l1, 8);
  distTable(document.getElementById("d2"), l2, 8);
  distTable(document.getElementById("dt"), l1+l2, 12);

  // Regulation outcome from the joint distribution
  const p1 = poisson(l1, 20), p2 = poisson(l2, 20);
  let w1 = 0, w2 = 0, tie = 0;
  for (let i = 0; i <= 20; i++) for (let j = 0; j <= 20; j++) {
    const v = p1[i]*p2[j]; if (i>j) w1+=v; else if (j>i) w2+=v; else tie+=v;
  }
  const tot = w1+w2+tie; w1/=tot; w2/=tot; tie/=tot;
  const bar = document.getElementById("obar").children;
  [[bar[0],w1],[bar[1],tie],[bar[2],w2]].forEach(([d,v])=>{ d.style.width=(v*100)+"%"; d.textContent=pct(v); });
  document.getElementById("olabels").innerHTML =
    `<span>${A.ab} leads ${pct(w1)}</span><span>Tied, goes to OT ${pct(tie)}</span><span>${B.ab} leads ${pct(w2)}</span>`;
  renderRanks();
}

let mode = "off";
function rankList(key, asc) {
  const sorted = [...TEAMS].sort((a,b)=> asc ? a[key]-b[key] : b[key]-a[key]);
  let rank = 0, prev = null;
  return sorted.map((t,i)=>{ if (t[key] !== prev) { rank = i+1; prev = t[key]; } return {...t, rank}; });
}
function renderRanks() {
  const off = mode === "off";
  const list = rankList(off ? "gf" : "ga", !off);
  document.getElementById("rtitle").textContent = off ? "Offense rankings" : "Defense rankings";
  const keyHead = off ? "Goals / gm" : "Allowed / gm";
  const specHead = off ? "Power play" : "Penalty kill";
  let html = `<thead><tr><th class="l">Rank</th><th class="l">Team</th><th>${keyHead}</th><th>vs avg</th><th>${specHead}</th><th>${off?"Allowed / gm":"Goals / gm"}</th><th>Points</th></tr></thead><tbody>`;
  list.forEach(t=>{
    const v = off ? t.gf : t.ga;
    const diff = v - LEAGUE;
    const better = off ? diff > 0 : diff < 0;
    const cls = t.ab === s1.value ? "sel" : t.ab === s2.value ? "sel2" : "";
    html += `<tr class="${cls}"><td class="rk l">${t.rank}</td><td class="team l">${t.name}</td><td class="key">${v.toFixed(2)}</td>`+
      `<td><span class="rel ${Math.abs(diff)<0.005?"":better?"up":"dn"}">${diff>=0?"+":"−"}${Math.abs(diff).toFixed(2)}</span></td>`+
      `<td>${(off?t.pp:t.pk).toFixed(1)}%</td><td>${(off?t.ga:t.gf).toFixed(2)}</td><td>${t.pts}</td></tr>`;
  });
  document.getElementById("rtable").innerHTML = html + "</tbody>";
}
function setTab(m) {
  mode = m;
  document.getElementById("tab-off").setAttribute("aria-selected", m==="off");
  document.getElementById("tab-def").setAttribute("aria-selected", m==="def");
  renderRanks();
}
document.getElementById("tab-off").addEventListener("click", ()=>setTab("off"));
document.getElementById("tab-def").addEventListener("click", ()=>setTab("def"));
document.getElementById("swap").addEventListener("click", ()=>{ const a=s1.value; s1.value=s2.value; s2.value=a; update(); });
s1.addEventListener("change", update); s2.addEventListener("change", update);
document.getElementById("lavg").textContent = LEAGUE.toFixed(2);
update();
