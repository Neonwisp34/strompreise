"""Build the static site from data/all.json -> docs/.  Usage: python build.py [BASE]   (BASE default /strompreise)"""
import html, json, os, re, shutil, statistics, sys, unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = sys.argv[1] if len(sys.argv) > 1 else "/strompreise"
OUT = os.path.join(HERE, "docs")
SITE = "https://neonwisp34.github.io"
D = json.load(open(os.path.join(HERE, "data", "all.json"), encoding="utf-8"))
HIST, OPS, CANT, MUNI = D["history"], D["operators"], D["cantons"], D["municipalities"]
DE = {"Lucerne": "Luzern", "Zurich": "Zürich", "Ginevra": "Genf", "Valais": "Wallis", "St Gallen": "St. Gallen", "Ticino": "Tessin", "Vaud": "Waadt", "Neuchâtel": "Neuenburg", "Fribourg": "Freiburg", "Basel Landschaft": "Basel-Landschaft", "Basel Stadt": "Basel-Stadt", "Jura": "Jura"}
CANT = {k: DE.get(v, v) for k, v in CANT.items()}
YEARS = sorted({int(y) for h in HIST.values() for y in h})
CUR = max(YEARS)
PREV = CUR - 1
KWH = 4500  # ElCom category H4

# ---------- helpers ----------
def esc(s): return html.escape(str(s))
def slug(s):
    s = s.lower()
    for a, b in (("ä", "ae"), ("ö", "oe"), ("ü", "ue")):
        s = s.replace(a, b)
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")
def chf(x): return f"{x:,.0f}".replace(",", "'")
def chf2(x): return f"{x:,.2f}".replace(",", "'").replace(".", ",")
def fmt(x): return f"{x:.2f}".replace(".", ",")
def fmt1(x): return f"{x:.1f}".replace(".", ",")
def r2(x): return round(x, 2)

def main_op(m, y):
    rows = HIST.get(m, {}).get(str(y))
    return min(rows, key=lambda r: r["total"]) if rows else None  # lowest standard tariff of the municipality's operators

# ---------- data model ----------
rec = {}
for m, hy in HIST.items():
    if str(CUR) not in hy or m not in MUNI:
        continue
    r = main_op(m, CUR)
    p = next((x for x in hy.get(str(PREV), []) if x["op"] == r["op"]), None)  # compare same operator only
    rec[m] = {"id": m, "name": MUNI[m]["name"], "canton": CANT.get(MUNI[m]["canton"], "?"), "plz": MUNI[m]["plz"], "cur": r, "prev": p, "all": hy[str(CUR)]}
names = {}
for r in rec.values(): names.setdefault(r["name"], []).append(r["id"])
for r in rec.values():
    r["slug"] = slug(r["name"]) if len(names[r["name"]]) == 1 else slug(r["name"]) + "-" + slug(r["canton"])

N = len(rec)
allp = sorted(r["cur"]["total"] for r in rec.values())
CH_MED = statistics.median(allp)
P_LO, P_HI = allp[int(N * 0.02)], allp[int(N * 0.98)]
bycanton = {}
for r in rec.values(): bycanton.setdefault(r["canton"], []).append(r)
COMP_KEYS = [("energy", "Energie"), ("grid", "Netznutzung"), ("meter", "Messung"), ("charge", "Abgaben an Gemeinwesen"), ("aid", "Bundesabgaben (Netzzuschlag)")]
COMP_MED = {k: statistics.median(r["cur"][k] for r in rec.values()) for k, _ in COMP_KEYS}

# Swiss median per year (cheapest standard tariff per municipality), for the chart comparison line
MED_BY_YEAR = {}
for y in YEARS:
    v = [main_op(m, y)["total"] for m in HIST if m in MUNI and main_op(m, y) and main_op(m, y)["total"] >= 5]
    if len(v) > 100: MED_BY_YEAR[y] = statistics.median(v)

def comp_rank(items):
    out, last, rk = {}, None, 0
    for i, r in enumerate(sorted(items, key=lambda x: r2(x["cur"]["total"]))):
        v = r2(r["cur"]["total"])
        if v != last: rk, last = i + 1, v
        out[r["id"]] = rk
    return out
rank_ch = comp_rank(rec.values())
rank_c = {}
for c, rs in bycanton.items(): rank_c.update(comp_rank(rs))

# ---------- styling ----------
CSS = """:root{--bg:#faf9f6;--sf:#fff;--fg:#17181a;--mut:#62666d;--ac:#b8102a;--ac2:#3b3f46;--line:#e4e1da;--good:#2f7d4f;--bad:#b8102a;--mid:#8a6d1c;--gl:#e6f2ea;--bl:#fbe7ea;--ml:#f6efd9;--serif:Georgia,"Times New Roman",serif}
@media(prefers-color-scheme:dark){:root{--bg:#121315;--sf:#1a1b1e;--fg:#ecebe8;--mut:#a3a39e;--ac:#ff6b7d;--ac2:#c9c9c4;--line:#2d2e32;--good:#6fcf97;--bad:#ff7b8a;--mid:#e3b95b;--gl:#15271c;--bl:#321419;--ml:#2e2610}}
*{box-sizing:border-box}html{-webkit-text-size-adjust:100%}body{margin:0;background:var(--bg);color:var(--fg);font:16px/1.6 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
a{color:var(--fg);text-decoration-color:var(--ac);text-decoration-thickness:2px;text-underline-offset:3px}a:hover{color:var(--ac)}
.top{border-bottom:2px solid var(--fg);background:var(--bg)}.top div{max-width:960px;margin:0 auto;padding:.9rem 1.1rem;display:flex;align-items:center}
.top a{color:var(--fg);text-decoration:none;font-family:var(--serif);font-size:1.25rem;font-weight:700;display:flex;align-items:center;gap:.6rem}.logo{display:inline-block;width:14px;height:14px;background:var(--ac)}
.w{max-width:960px;margin:0 auto;padding:1.4rem 1.1rem 3rem}
h1{font-family:var(--serif);font-size:clamp(1.8rem,5vw,2.7rem);line-height:1.12;margin:.2rem 0 .5rem;font-weight:700}h2{font-family:var(--serif);font-size:1.45rem;margin:2.6rem 0 .8rem;padding-top:.9rem;border-top:1px solid var(--line)}h3{margin:1.2rem 0 .3rem}
.crumb{font-size:.86rem;color:var(--mut)}.crumb a{color:var(--mut);text-decoration:none}.crumb a:hover{text-decoration:underline}
.card{background:var(--sf);border:1px solid var(--line);border-radius:4px;padding:1.2rem 1.3rem}
.hero{display:grid;grid-template-columns:1.1fr .9fr;gap:1rem;margin:1rem 0}@media(max-width:760px){.hero{grid-template-columns:1fr}}
.price{font-family:var(--serif);font-size:clamp(3.2rem,10vw,4.6rem);font-weight:700;line-height:1}.price small{font-family:system-ui,sans-serif;font-size:1rem;font-weight:500;color:var(--mut)}
.badge{display:inline-block;font-weight:700;border-left:4px solid currentColor;padding:.3rem .8rem;margin:.9rem 0 .2rem;font-size:.97rem}
.b-good{background:var(--gl);color:var(--good)}.b-bad{background:var(--bl);color:var(--bad)}.b-mid{background:var(--ml);color:var(--mid)}
.gauge{position:relative;height:10px;background:linear-gradient(90deg,var(--good) 0 33%,#c9c4b6 33% 66%,var(--bad) 66% 100%);margin:2.2rem 0 .4rem}
.gauge i{position:absolute;top:-7px;width:3px;height:24px;background:var(--fg);transform:translateX(-50%)}.gauge i.m{background:var(--mut);height:18px;top:-4px}
.gauge b{position:absolute;top:-28px;transform:translateX(-50%);font-size:.8rem;white-space:nowrap}.gl{display:flex;justify-content:space-between;font-size:.78rem;color:var(--mut)}
.tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:.8rem;margin:1rem 0}.tile{background:var(--sf);border:1px solid var(--line);border-radius:4px;padding:.9rem 1rem}
.tile .k{font-size:.76rem;color:var(--mut);text-transform:uppercase;letter-spacing:.06em}.tile .v{font-family:var(--serif);font-size:1.6rem;font-weight:700}.tile .s{font-size:.82rem;color:var(--mut)}
.up{color:var(--bad)}.dn{color:var(--good)}.mut{color:var(--mut)}
.stack{display:flex;height:18px;overflow:hidden;margin:.6rem 0}.stack span{display:block}
.leg{display:flex;flex-wrap:wrap;gap:.3rem 1rem;font-size:.88rem;margin:.4rem 0 1rem}.leg i{display:inline-block;width:10px;height:10px;margin-right:.35rem}
table{border-collapse:collapse;width:100%}td,th{padding:.55rem .5rem;border-bottom:1px solid var(--line);text-align:left;vertical-align:top}th{font-size:.76rem;color:var(--mut);text-transform:uppercase;letter-spacing:.06em}td.n,th.n{text-align:right;font-variant-numeric:tabular-nums}
.calc label{display:block;font-weight:600;margin-bottom:.3rem}.calc input[type=range]{width:100%;accent-color:var(--ac)}
.chips{display:flex;flex-wrap:wrap;gap:.5rem;margin:.6rem 0}.chips button{border:1px solid var(--line);background:var(--bg);color:var(--fg);padding:.4rem .8rem;border-radius:3px;font:inherit;font-size:.88rem;cursor:pointer}.chips button:hover,.chips button.on{border-color:var(--ac);color:var(--ac);font-weight:600}
.out{display:flex;flex-wrap:wrap;gap:1.2rem;margin-top:.8rem}.out div{flex:1 1 140px}.out .v{font-family:var(--serif);font-size:1.8rem;font-weight:700}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(210px,1fr));gap:.6rem;padding:0;list-style:none;margin:0}.grid a{display:flex;justify-content:space-between;gap:.6rem;padding:.65rem .9rem;background:var(--sf);border:1px solid var(--line);border-radius:4px;text-decoration:none;color:var(--fg)}.grid a:hover{border-color:var(--ac)}.grid span{color:var(--mut);font-variant-numeric:tabular-nums}
input[type=search]{width:100%;padding:1rem 1.2rem;font-size:1.1rem;border:2px solid var(--fg);border-radius:3px;background:var(--sf);color:var(--fg)}input[type=search]:focus{outline:none;border-color:var(--ac)}
#r{list-style:none;padding:0;margin:.5rem 0 0}#r a{display:block;padding:.65rem 1rem;background:var(--sf);border:1px solid var(--line);margin-bottom:.4rem;text-decoration:none}
.rank{display:grid;gap:.35rem}.rank a{display:grid;grid-template-columns:2.4rem 1fr auto;align-items:center;gap:.6rem;text-decoration:none;color:var(--fg);padding:.35rem 0}.rank em{font-style:normal;color:var(--mut);font-size:.85rem}
.rank .bar{grid-column:2/4;height:4px;background:var(--line)}.rank .bar u{display:block;height:100%;background:var(--ac)}
details{border-bottom:1px solid var(--line);padding:.8rem 0}summary{cursor:pointer;font-weight:600}details p{margin:.5rem 0 0;color:var(--mut)}
footer{margin-top:3rem;padding-top:1.2rem;border-top:2px solid var(--fg);font-size:.82rem;color:var(--mut)}
.price,.tile .v,.out .v,h1,h2{font-variant-numeric:lining-nums}svg text{font-family:inherit}.note{font-size:.86rem;color:var(--mut)}"""

GSC = '<meta name="google-site-verification" content="RTeH9c9V1LuksTyF5yz_M5L9cz1En0C2d7PBphOJKzI" />'

def page(title, desc, body, path, schemas=()):
    url = SITE + f"{BASE}/{path}".replace("//", "/")
    ld = "".join(f'<script type="application/ld+json">{json.dumps(s, ensure_ascii=False)}</script>' for s in schemas)
    return f"""<!doctype html><html lang="de-CH"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)}</title><meta name="description" content="{esc(desc)}"><link rel="canonical" href="{esc(url)}">
{GSC if path == "" else ""}<meta property="og:title" content="{esc(title)}"><meta property="og:description" content="{esc(desc)}"><meta property="og:type" content="website"><meta property="og:url" content="{esc(url)}"><meta property="og:locale" content="de_CH"><meta name="twitter:card" content="summary">
<style>{CSS}</style>{ld}</head><body><header class="top"><div><a href="{BASE}/" style="display:flex;align-items:center;gap:.6rem"><span class="logo" aria-hidden="true"></span>Strompreis-Monitor</a></div></header>
<div class="w"><main>{body}</main>
<footer>Quelle: Eidgenössische Elektrizitätskommission ElCom, Open Government Data (opendata.swiss). Tarife der ElCom-Haushaltskategorie H4 (4'500 kWh pro Jahr), Standardprodukt des Netzbetreibers, in Rappen pro kWh, wie von der ElCom ausgewiesen. Zur Mehrwertsteuer macht dieser Datensatz keine Angabe; massgebend ist die Tarifinformation Ihres Netzbetreibers. Kosten sind Schätzungen (Preis × Verbrauch), Alltagswerte grobe Richtwerte. Strompreis-Monitor ist eine unabhängige Seite ohne Verbindung zur ElCom oder zu einem Netzbetreiber. Datenstand: Tarife {CUR}.</footer></div></body></html>"""

# ---------- charts ----------
def chart(series, med):
    """series: [(year, price)] for the municipality; med: {year: median}."""
    if len(series) < 2: return ""
    W, H, PL, PR, PT, PB = 720, 280, 50, 24, 30, 34
    ys = [v for _, v in series] + [med[y] for y, _ in series if y in med]
    lo, hi = min(ys) * 0.9, max(ys) * 1.08
    xs0, xs1 = series[0][0], series[-1][0]
    X = lambda x: PL + (x - xs0) / (xs1 - xs0) * (W - PL - PR)
    Y = lambda y: PT + (hi - y) / (hi - lo) * (H - PT - PB)
    path = lambda pts: " ".join(f"{'M' if i == 0 else 'L'}{X(x):.1f},{Y(v):.1f}" for i, (x, v) in enumerate(pts))
    grid = ""
    step = 5 if hi - lo > 18 else 2
    t = int(lo // step * step) + step
    while t < hi:
        grid += f'<line x1="{PL}" x2="{W-PR}" y1="{Y(t):.1f}" y2="{Y(t):.1f}" stroke="var(--line)"/><text x="{PL-8}" y="{Y(t)+4:.1f}" font-size="16" text-anchor="end" fill="var(--mut)">{t}</text>'
        t += step
    area = path(series) + f" L{X(xs1):.1f},{H-PB} L{X(xs0):.1f},{H-PB} Z"
    mpts = [(y, med[y]) for y, _ in series if y in med]
    xl = "".join(f'<text x="{X(y):.1f}" y="{H-8}" font-size="16" text-anchor="middle" fill="var(--mut)">{y}</text>' for y, _ in series[::4])
    dots = "".join(f'<circle cx="{X(y):.1f}" cy="{Y(v):.1f}" r="3.5" fill="var(--ac)"><title>{y}: {fmt(v)} Rp./kWh</title></circle>' for y, v in series)
    ly, lv = series[-1]
    peak = max(series[-8:], key=lambda p: p[1])
    pk = f'<text x="{X(peak[0]):.1f}" y="{Y(peak[1])-10:.1f}" font-size="16" text-anchor="middle" fill="var(--fg)" font-weight="700">Höchststand {peak[0]}: {fmt1(peak[1])}</text>' if peak[0] != ly else ""
    return (f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="Verlauf des Strompreises seit {xs0} im Vergleich zum Schweizer Median" style="width:100%;height:auto">'
            f'<defs><linearGradient id="g" x1="0" x2="0" y1="0" y2="1"><stop offset="0" stop-color="var(--ac)" stop-opacity=".16"/><stop offset="1" stop-color="var(--ac)" stop-opacity="0"/></linearGradient></defs>{grid}'
            f'<path d="{area}" fill="url(#g)"/><path d="{path(mpts)}" fill="none" stroke="var(--mut)" stroke-width="2" stroke-dasharray="5 5"/>'
            f'<path d="{path(series)}" fill="none" stroke="var(--ac)" stroke-width="3" stroke-linejoin="round"/>{dots}{pk}{xl}</svg>'
            f'<div class="leg"><span><i style="background:var(--ac)"></i>Diese Gemeinde</span><span><i style="background:var(--mut)"></i>Schweizer Median (gestrichelt)</span></div>')

def gauge(price):
    pos = lambda v: max(2, min(98, (v - P_LO) / (P_HI - P_LO) * 100))
    return (f'<div class="gauge" role="img" aria-label="Preisskala"><i class="m" style="left:{pos(CH_MED):.1f}%"></i><i style="left:{pos(price):.1f}%"></i>'
            f'<b style="left:{pos(price):.1f}%">{fmt1(price)}</b></div><div class="gl"><span>günstig {fmt1(P_LO)}</span><span>Median {fmt1(CH_MED)}</span><span>teuer {fmt1(P_HI)}</span></div>')

CALC_JS = """<script>(function(){var c=document.getElementById('calc');if(!c)return;var P=parseFloat(c.dataset.p),M=parseFloat(c.dataset.m),s=c.querySelector('input'),o=c.querySelectorAll('.v'),k=c.querySelector('.kv');
function f(n){return Math.round(n).toString().replace(/\\B(?=(\\d{3})+(?!\\d))/g,"'")}
function u(){var v=+s.value,y=P*v/100,d=(P-M)*v/100;k.textContent=f(v)+' kWh pro Jahr';o[0].textContent='CHF '+f(y);o[1].textContent='CHF '+f(y/12);
o[2].textContent=(Math.abs(d)<0.5?'gleich viel':(d>0?'+':'\\u2212')+'CHF '+f(Math.abs(d)))+(Math.abs(d)<0.5?'':' pro Jahr');o[2].className='v '+(d>0?'up':'dn')}
s.addEventListener('input',u);c.querySelectorAll('button').forEach(function(b){b.addEventListener('click',function(){s.value=b.dataset.v;c.querySelectorAll('button').forEach(function(x){x.classList.remove('on')});b.classList.add('on');u()})});u()})();</script>"""

def op_link(o):
    on = OPS.get(o["op"], {"name": "Netzbetreiber"})
    u = (on.get("url") or "").strip()
    if u and "@" not in u and " " not in u:
        href = u if u.startswith("http") else "https://" + u
        return f'<a href="{esc(href)}" rel="nofollow noopener">{esc(on["name"])}</a>'
    return esc(on["name"])

COLORS = {"energy": "#b8102a", "grid": "#3b3f46", "meter": "#9aa0a8", "charge": "#d9a441", "aid": "#5b8c6a"}

# ---------- municipality pages ----------
pages = {}
for r in rec.values():
    c, p = r["cur"], r["prev"]
    price = c["total"]
    n_ops = len(r["all"])
    pre = "ab " if n_ops > 1 else ""
    ann, mon = price * KWH / 100, price * KWH / 1200
    cm = statistics.median([x["cur"]["total"] for x in bycanton[r["canton"]]])
    dpct = (price / CH_MED - 1) * 100
    cheaper_than = round(100 * sum(1 for q in allp if q > price + 1e-9) / N)
    pricier_than = round(100 * sum(1 for q in allp if q < price - 1e-9) / N)
    if dpct <= -5:
        cls, verdict = "b-good", f"Günstiger als {cheaper_than}% der Schweizer Gemeinden"
    elif dpct >= 5:
        cls, verdict = "b-bad", f"Teurer als {pricier_than}% der Schweizer Gemeinden"
    else:
        cls, verdict = "b-mid", "Im Schweizer Mittelfeld"
    vs = "genau auf Höhe" if r2(price) == r2(CH_MED) else f"{fmt1(abs(dpct))}% {'über' if dpct > 0 else 'unter'}"
    # change vs last year
    chg = "<div class='tile'><div class='k'>Veränderung zu %d</div><div class='v'>unverändert</div></div>" % PREV
    if p:
        dd = r2(price) - r2(p["total"])
        if dd != 0:
            pc = dd / p["total"] * 100
            sign, cc = ("+", "up") if dd > 0 else ("−", "dn")
            chg = f"<div class='tile'><div class='k'>Veränderung zu {PREV}</div><div class='v {cc}'>{sign}{fmt(abs(dd))} Rp.</div><div class='s'>{sign}{fmt1(abs(pc))}% (gleicher Netzbetreiber)</div></div>"
    else:
        chg = ""
    series = [(y, row["total"]) for y in YEARS for row in [main_op(r["id"], y)] if row and row["total"] >= 5]
    # reasons: compare components to Swiss median
    parts = []
    for k, lab in COMP_KEYS:
        dv = c[k] - COMP_MED[k]
        if abs(dv) >= 0.4: parts.append((abs(dv), lab, dv))
    parts.sort(reverse=True)
    if parts:
        top = parts[0]
        why = f"Den grössten Unterschied zum Schweizer Median macht der Posten <b>{esc(top[1])}</b> aus: {fmt(abs(top[2]))} Rp./kWh {'mehr' if top[2] > 0 else 'weniger'}."
        if len(parts) > 1:
            s2 = parts[1]
            why += f" Danach folgt {esc(s2[1])} mit {fmt(abs(s2[2]))} Rp. {'mehr' if s2[2] > 0 else 'weniger'}."
    else:
        why = "Alle Preisbestandteile liegen nahe beim Schweizer Median."
    tot = sum(c[k] for k, _ in COMP_KEYS) or 1
    stack = "".join(f'<span style="width:{c[k]/tot*100:.1f}%;background:{COLORS[k]}" title="{lab}: {fmt(c[k])} Rp."></span>' for k, lab in COMP_KEYS if c[k] > 0)
    legend = "".join(f'<span><i style="background:{COLORS[k]}"></i>{lab} {fmt(c[k])}</span>' for k, lab in COMP_KEYS if c[k] > 0)
    brows = "".join(f'<tr><td>{lab}</td><td class="n">{fmt(c[k])}</td><td class="n mut">{fmt(COMP_MED[k])}</td></tr>' for k, lab in COMP_KEYS if c[k] > 0 or COMP_MED[k] > 0.05)
    ops = "".join(f'<tr><td>{op_link(o)}</td><td>{esc(o["product"] or "")}</td><td class="n">{fmt(o["total"])}</td></tr>' for o in sorted(r["all"], key=lambda x: x["total"]))
    multi = f'<p class="note">In {esc(r["name"])} sind mehrere Netzbetreiber tätig (je nach Ortsteil). Angezeigt wird der tiefste Tarif; Ihr Preis hängt vom zuständigen Betreiber ab.</p>' if n_ops > 1 else ""
    # similar municipalities (closest prices in same canton)
    sim = sorted((x for x in bycanton[r["canton"]] if x["id"] != r["id"]), key=lambda x: abs(x["cur"]["total"] - price))[:8]
    simh = "".join(f'<li><a href="{BASE}/gemeinde/{x["slug"]}/">{esc(x["name"])}<span>{fmt(x["cur"]["total"])}</span></a></li>' for x in sim)
    plz = ", ".join(r["plz"][:6])
    everyday = [("Waschmaschine, 1 Ladung", 1.0, "ca. 1 kWh"), ("Backofen, 1 Stunde", 2.0, "ca. 2 kWh"), ("Elektroauto, 100 km", 18.0, "ca. 18 kWh")]
    def money(v): return f"CHF {chf2(v)}" if v >= 1 else f"{round(v * 100)} Rp."
    evh = "".join(f'<div class="tile"><div class="k">{a}</div><div class="v">{money(price * kw / 100)}</div><div class="s">{b}</div></div>' for a, kw, b in everyday)
    presets = [("Wohnung, 1–2 Personen", 1600), ("Wohnung, Familie", 2500), ("Haus (H4)", 4500), ("Haus mit Wärmepumpe", 9000)]
    chips = "".join(f'<button type="button" data-v="{v}"{" class=on" if v == KWH else ""}>{lab}</button>' for lab, v in presets)
    why_cheap = "günstiger" if dpct < 0 else "teurer"
    faq = [
        (f"Wie hoch ist der Strompreis in {r['name']}?", f"{pre.capitalize()}{fmt(price)} Rp./kWh im Jahr {CUR} (ElCom-Kategorie H4). Für 4'500 kWh pro Jahr sind das rund CHF {chf(ann)}."),
        (f"Wie viel kostet Strom in {r['name']} pro Monat?", f"Bei 4'500 kWh Jahresverbrauch rund CHF {chf(mon)} pro Monat. Mit dem Rechner oben können Sie Ihren eigenen Verbrauch einsetzen."),
        (f"Ist Strom in {r['name']} {why_cheap} als im Schweizer Durchschnitt?", f"Der Preis liegt {vs} dem Schweizer Median von {fmt(CH_MED)} Rp./kWh und {'über' if price > cm else ('unter' if price < cm else 'genau auf Höhe')} dem Median im Kanton {r['canton']} ({fmt(cm)} Rp./kWh)."),
    ]
    faqh = "".join(f"<details><summary>{esc(q)}</summary><p>{a}</p></details>" for q, a in faq)
    body = f"""<div class="crumb"><a href="{BASE}/">Schweiz</a> › <a href="{BASE}/kanton/{slug(r['canton'])}/">{esc(r['canton'])}</a> › {esc(r['name'])}</div>
<h1>Strompreis in {esc(r['name'])} {CUR}</h1>
<p class="mut">Kanton {esc(r['canton'])}{' · PLZ ' + esc(plz) if plz else ''}</p>
<section class="hero"><div class="card"><div class="price">{pre}{fmt(price)} <small>Rp./kWh</small></div>
<span class="badge {cls}">{verdict}</span>
<p style="margin:.4rem 0 0">Rund <b>CHF {chf(mon)} pro Monat</b> oder <b>CHF {chf(ann)} pro Jahr</b> für einen Haushalt mit 4'500 kWh. Der Preis liegt {vs} dem Schweizer Median.</p>{multi}</div>
<div class="card"><b>Wo steht {esc(r['name'])}?</b>{gauge(price)}<p class="note" style="margin:.8rem 0 0">Rang <b>{rank_ch[r['id']]}</b> von {N} in der Schweiz (1 = günstigster Preis, gleiche Preise teilen den Rang) · Rang <b>{rank_c[r['id']]}</b> von {len(bycanton[r['canton']])} im Kanton {esc(r['canton'])}.</p></div></section>
<div class="tiles">{chg}<div class="tile"><div class="k">Kantonsmedian</div><div class="v">{fmt(cm)}</div><div class="s">Rp./kWh, Kanton {esc(r['canton'])}</div></div><div class="tile"><div class="k">Schweizer Median</div><div class="v">{fmt(CH_MED)}</div><div class="s">Rp./kWh</div></div></div>
<h2>Was kostet Strom für Sie?</h2>
<div class="card calc" id="calc" data-p="{price:.4f}" data-m="{CH_MED:.4f}"><label for="kwh">Ihr Jahresverbrauch: <span class="kv"></span></label>
<input id="kwh" type="range" min="500" max="15000" step="100" value="{KWH}"><div class="chips">{chips}</div>
<div class="out"><div><div class="mut">Pro Jahr</div><div class="v"></div></div><div><div class="mut">Pro Monat</div><div class="v"></div></div><div><div class="mut">Gegenüber dem Schweizer Median</div><div class="v"></div></div></div>
<p class="note" style="margin-bottom:0">Vereinfachte Rechnung (Preis × Verbrauch) mit dem H4-Tarif. Die Verbrauchsprofile sind grobe Richtwerte; Ihre Rechnung kann abweichen.</p></div>
<h2>Verlauf seit {series[0][0] if series else YEARS[0]}</h2><div class="card">{chart(series, MED_BY_YEAR)}</div>
<h2>Warum ist Strom in {esc(r['name'])} {why_cheap}?</h2>
<div class="card"><div class="stack" role="img" aria-label="Zusammensetzung des Preises">{stack}</div><div class="leg">{legend}</div><p style="margin:.2rem 0 0">{why}</p>
<table style="margin-top:1rem"><tr><th>Bestandteil</th><th class="n">{esc(r['name'])}</th><th class="n">CH-Median</th></tr>{brows}</table></div>
<h2>Alltag in Franken</h2><div class="tiles">{evh}</div><p class="note">Grobe Richtwerte für typische Geräte, berechnet mit dem Preis von {esc(r['name'])}.</p>
<h2>Stromanbieter in {esc(r['name'])}</h2><div class="card"><table><tr><th>Netzbetreiber</th><th>Produkt</th><th class="n">Rp./kWh</th></tr>{ops}</table></div>
<h2>Ähnliche Preise im Kanton {esc(r['canton'])}</h2><ul class="grid">{simh}</ul>
<p><a href="{BASE}/kanton/{slug(r['canton'])}/">Alle Gemeinden im Kanton {esc(r['canton'])} ansehen</a></p>
<h2>Häufige Fragen</h2>{faqh}{CALC_JS}"""
    title = f"Strompreis {r['name']} {CUR}: {pre}{fmt(price)} Rp./kWh"
    desc = f"Strompreis {r['name']} ({r['canton']}) {CUR}: {pre}{fmt(price)} Rp./kWh, rund CHF {chf(mon)} pro Monat. {verdict}. Rechner, Verlauf und Preisbestandteile."
    schemas = [{"@context": "https://schema.org", "@type": "Dataset", "name": f"Strompreis {r['name']} {CUR}", "description": desc, "creator": {"@type": "Organization", "name": "ElCom"}, "spatialCoverage": f"{r['name']}, {r['canton']}, Schweiz"},
               {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [{"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": re.sub(r"<[^>]+>", "", a)}} for q, a in faq]}]
    pages[f"gemeinde/{r['slug']}/index.html"] = page(title, desc, body, f"gemeinde/{r['slug']}/", schemas)

# ---------- canton pages ----------
def rank_list(items, rk=None, limit=None):
    items = items[:limit] if limit else items
    mx = max(x["cur"]["total"] for x in items) or 1
    return '<div class="rank">' + "".join(
        f'<a href="{BASE}/gemeinde/{x["slug"]}/"><em>{rk[x["id"]] if rk else i + 1}</em><span>{esc(x["name"])} <em>{esc(x["canton"])}</em></span><b>{fmt(x["cur"]["total"])}</b><div class="bar"><u style="width:{x["cur"]["total"]/mx*100:.0f}%"></u></div></a>'
        for i, x in enumerate(items)) + "</div>"

for cn, rs in bycanton.items():
    rs = sorted(rs, key=lambda x: x["cur"]["total"])
    rk = comp_rank(rs)
    med = statistics.median(x["cur"]["total"] for x in rs)
    lo, hi = rs[0], rs[-1]
    flat = r2(lo["cur"]["total"]) == r2(hi["cur"]["total"])
    ext = f"Alle {len(rs)} Gemeinden haben denselben Preis." if flat else f"Zwischen <b>{fmt(lo['cur']['total'])}</b> ({esc(lo['name'])}) und <b>{fmt(hi['cur']['total'])}</b> Rp./kWh ({esc(hi['name'])}) liegen {fmt(hi['cur']['total'] - lo['cur']['total'])} Rp."
    rows = rank_list(rs, rk)
    body = f"""<div class="crumb"><a href="{BASE}/">Schweiz</a> › {esc(cn)}</div><h1>Strompreise im Kanton {esc(cn)} {CUR}</h1>
<p>{ext}</p><div class="tiles"><div class="tile"><div class="k">Median Kanton</div><div class="v">{fmt(med)}</div><div class="s">Rp./kWh</div></div><div class="tile"><div class="k">Schweizer Median</div><div class="v">{fmt(CH_MED)}</div><div class="s">Rp./kWh</div></div><div class="tile"><div class="k">Gemeinden</div><div class="v">{len(rs)}</div></div></div>
<h2>Alle Gemeinden vom günstigsten bis zum höchsten Preis</h2><div class="card">{rows}</div>"""
    pages[f"kanton/{slug(cn)}/index.html"] = page(f"Strompreise Kanton {cn} {CUR}: alle Gemeinden", f"Strompreise {CUR} aller {len(rs)} Gemeinden im Kanton {cn}. Median {fmt(med)} Rp./kWh.", body, f"kanton/{slug(cn)}/")

# ---------- home ----------
srt = sorted(rec.values(), key=lambda x: x["cur"]["total"])
chips = "".join(f'<li><a href="{BASE}/kanton/{slug(c)}/">{esc(c)}<span>{len(bycanton[c])}</span></a></li>' for c in sorted(bycanton))
prev_med = MED_BY_YEAR.get(PREV)
dmed = f"{(CH_MED / prev_med - 1) * 100:+.1f}%".replace(".", ",").replace("-", "−") if prev_med else ""
body = f"""<h1>Was kostet Strom in Ihrer Gemeinde?</h1>
<p class="mut" style="font-size:1.1rem;margin-top:0">Die offiziellen Strompreise {CUR} aller {N} Schweizer Gemeinden: Preis, Vergleich, Verlauf und ein Rechner für Ihren Verbrauch.</p>
<input id="q" type="search" placeholder="Gemeinde oder Postleitzahl eingeben …" aria-label="Gemeinde oder Postleitzahl suchen" autocomplete="off"><ul id="r"></ul>
<div class="tiles"><div class="tile"><div class="k">Schweizer Median</div><div class="v">{fmt(CH_MED)}</div><div class="s">Rp./kWh {('· ' + dmed + ' zu ' + str(PREV)) if dmed else ''}</div></div>
<div class="tile"><div class="k">Günstigster Preis</div><div class="v">{fmt(srt[0]['cur']['total'])}</div><div class="s">{esc(srt[0]['name'])} ({esc(srt[0]['canton'])})</div></div>
<div class="tile"><div class="k">Höchster Preis</div><div class="v">{fmt(srt[-1]['cur']['total'])}</div><div class="s">{esc(srt[-1]['name'])} ({esc(srt[-1]['canton'])})</div></div>
<div class="tile"><div class="k">Preisspanne</div><div class="v">{srt[-1]['cur']['total'] / srt[0]['cur']['total']:.1f}×</div><div class="s">teuerste zu günstigste Gemeinde</div></div></div>
<h2>Nach Kanton</h2><ul class="grid">{chips}</ul>
<div class="hero" style="margin-top:2rem"><div><h2 style="margin-top:0">Die günstigsten Preise {CUR}</h2><div class="card">{rank_list(srt, rank_ch, 12)}</div></div>
<div><h2 style="margin-top:0">Die höchsten Preise {CUR}</h2><div class="card">{rank_list(srt[::-1], {x['id']: rank_ch[x['id']] for x in srt}, 12)}</div></div></div>
<script>const I={json.dumps([[x['name'], x['canton'], x['slug'], ' '.join(x['plz'])] for x in sorted(rec.values(), key=lambda x: x['name'])], ensure_ascii=False)};
const q=document.getElementById('q'),r=document.getElementById('r');q.addEventListener('input',()=>{{const t=q.value.trim().toLowerCase();r.innerHTML='';if(t.length<2)return;I.filter(i=>(i[0]+' '+i[3]).toLowerCase().includes(t)).slice(0,30).forEach(i=>{{const l=document.createElement('li'),a=document.createElement('a');a.href='{BASE}/gemeinde/'+i[2]+'/';a.textContent=i[0]+' ('+i[1]+')';l.appendChild(a);r.appendChild(l)}})}})</script>"""
pages["index.html"] = page(f"Strompreis-Monitor: Strompreise {CUR} aller Schweizer Gemeinden", f"Strompreis pro Gemeinde {CUR}: offizielle ElCom-Tarife für {N} Schweizer Gemeinden, mit Vergleich, Verlauf und Stromkosten-Rechner. Median {fmt(CH_MED)} Rp./kWh.", body, "")

# ---------- write ----------
if os.path.isdir(OUT): shutil.rmtree(OUT)
for pth, cont in pages.items():
    fp = os.path.join(OUT, pth); os.makedirs(os.path.dirname(fp), exist_ok=True)
    open(fp, "w", encoding="utf-8").write(cont)
urls = [f"{SITE}{BASE}/{pth[:-10]}" for pth in pages]
open(os.path.join(OUT, "sitemap.xml"), "w").write('<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">' + "".join(f"<url><loc>{u}</loc></url>" for u in urls) + "</urlset>")
open(os.path.join(OUT, "robots.txt"), "w").write(f"User-agent: *\nAllow: /\nSitemap: {SITE}{BASE}/sitemap.xml\n")
open(os.path.join(OUT, ".nojekyll"), "w").write("")
print(len(pages), "pages;", CUR, "CH median", round(CH_MED, 2), "| cheapest", srt[0]["name"], round(srt[0]["cur"]["total"], 3), "| dearest", srt[-1]["name"], round(srt[-1]["cur"]["total"], 3))
