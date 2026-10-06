"""Build the static site from data/all.json -> site/.  Usage: python build.py [BASE]   (BASE default /strompreise)"""
import html, json, os, re, shutil, statistics, sys
from datetime import date

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
KWH = 4500  # ElCom category H4: 4-room apartment with electric stove

def esc(s): return html.escape(str(s))
import unicodedata
def slug(s):
    s = s.lower()
    for a, b in (("ä", "ae"), ("ö", "oe"), ("ü", "ue"), ("é", "e"), ("è", "e"), ("à", "a"), ("ê", "e"), ("ç", "c"), ("ô", "o"), ("î", "i"), ("â", "a")):
        s = s.replace(a, b)
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")

def main_op(m, y):
    rows = HIST.get(m, {}).get(str(y))
    return min(rows, key=lambda r: r["total"]) if rows else None  # lowest-price standard tariff of the municipality's operators

# one record per municipality for current year
rec = {}
for m, hy in HIST.items():
    if str(CUR) not in hy or m not in MUNI:
        continue
    r = main_op(m, CUR)
    p = next((x for x in hy.get(str(PREV), []) if x["op"] == r["op"]), None)  # compare same operator only
    rec[m] = {"id": m, "name": MUNI[m]["name"], "canton": CANT.get(MUNI[m]["canton"], "?"), "cid": MUNI[m]["canton"],
              "plz": MUNI[m]["plz"], "cur": r, "prev": p, "all": hy[str(CUR)]}
names = {}
for r in rec.values(): names.setdefault(r["name"], []).append(r["id"])
for r in rec.values():
    r["slug"] = slug(r["name"]) if len(names[r["name"]]) == 1 else slug(r["name"]) + "-" + slug(r["canton"])

allp = [r["cur"]["total"] for r in rec.values()]
CH_MED = statistics.median(allp)
bycanton = {}
for r in rec.values(): bycanton.setdefault(r["canton"], []).append(r)
def comp_rank(items):
    out, last, rk = {}, None, 0
    for i, r in enumerate(sorted(items, key=lambda x: round(x["cur"]["total"], 2))):
        v = round(r["cur"]["total"], 2)
        if v != last: rk, last = i + 1, v
        out[r["id"]] = rk
    return out
rank_ch = comp_rank(rec.values())
rank_c = {}
for c, rs in bycanton.items():
    rank_c.update(comp_rank(rs))

CSS = """:root{--bg:#fff;--fg:#1a1d21;--mut:#5a6270;--ac:#0b57d0;--line:#e3e6eb;--card:#f6f8fb;--up:#b3261e;--dn:#146c2e}
@media(prefers-color-scheme:dark){:root{--bg:#14171b;--fg:#e8eaed;--mut:#9aa3af;--ac:#8ab4f8;--line:#2a2f36;--card:#1b1f25;--up:#f2b8b5;--dn:#81c995}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font:16px/1.55 system-ui,-apple-system,Segoe UI,sans-serif}
.w{max-width:860px;margin:0 auto;padding:1rem 1.1rem 3rem}a{color:var(--ac)}h1{font-size:1.9rem;line-height:1.2;margin:.4rem 0 .3rem}h2{font-size:1.25rem;margin:2rem 0 .6rem}
.big{font-size:3rem;font-weight:700;line-height:1}.u{font-size:1.1rem;color:var(--mut);font-weight:400}.card{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:1rem 1.2rem;margin:1rem 0}
.row{display:flex;gap:1rem;flex-wrap:wrap}.row>div{flex:1 1 180px}.mut{color:var(--mut);font-size:.9rem}.up{color:var(--up)}.dn{color:var(--dn)}
table{border-collapse:collapse;width:100%}td,th{padding:.45rem .5rem;border-bottom:1px solid var(--line);text-align:left}th{font-size:.85rem;color:var(--mut)}td.n,th.n{text-align:right;font-variant-numeric:tabular-nums}
nav{font-size:.9rem;color:var(--mut)}input{width:100%;padding:.8rem 1rem;font-size:1.05rem;border:1px solid var(--line);border-radius:10px;background:var(--bg);color:var(--fg)}
.bar{height:10px;border-radius:5px;background:var(--ac);display:inline-block}footer{margin-top:3rem;font-size:.85rem;color:var(--mut)}ul.l{columns:2;padding-left:1.1rem}@media(max-width:560px){ul.l{columns:1}.big{font-size:2.4rem}}"""

def page(title, desc, body, path, schema=None):
    url = SITE + f"{BASE}/{path}".replace("//", "/")
    ld = f'<script type="application/ld+json">{json.dumps(schema, ensure_ascii=False)}</script>' if schema else ""
    return f"""<!doctype html><html lang="de-CH"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)}</title><meta name="description" content="{esc(desc)}"><link rel="canonical" href="{esc(url)}">
<style>{CSS}</style>{ld}</head><body><div class="w"><nav><a href="{BASE}/">Strompreise Schweiz</a></nav><main>{body}</main>
<footer>Quelle: Eidgenössische Elektrizitätskommission ElCom, Open Government Data (opendata.swiss). Tarife der ElCom-Haushaltskategorie H4 (4'500 kWh pro Jahr), Standardprodukt des Netzbetreibers, in Rappen pro kWh, wie von der ElCom ausgewiesen. Zur Mehrwertsteuer macht dieser Datensatz keine Angabe; massgebend ist die Tarifinformation Ihres Netzbetreibers. Die Jahreskosten sind eine Schätzung (Preis × 4'500 kWh). Unabhängige Seite, keine Verbindung zur ElCom oder zu einem Netzbetreiber. Daten: {CUR}, Seite erstellt am {date.today():%d.%m.%Y}.</footer></div></body></html>"""

def chart(points):
    if len(points) < 2: return ""
    W, H, P = 640, 200, 34
    xs = [p[0] for p in points]; ys = [p[1] for p in points]
    lo, hi = min(ys) * 0.92, max(ys) * 1.05
    X = lambda x: P + (x - xs[0]) / (xs[-1] - xs[0]) * (W - 2 * P)
    Y = lambda y: H - P / 1.5 - (y - lo) / (hi - lo) * (H - P * 1.6)
    d = " ".join(f"{'M' if i == 0 else 'L'}{X(x):.1f},{Y(y):.1f}" for i, (x, y) in enumerate(points))
    dots = "".join(f'<circle cx="{X(x):.1f}" cy="{Y(y):.1f}" r="3" fill="var(--ac)"><title>{x}: {fmt(y)} Rp./kWh</title></circle>' for x, y in points)
    lab = "".join(f'<text x="{X(x):.1f}" y="{H-6}" font-size="11" text-anchor="middle" fill="var(--mut)">{x}</text>' for x, _ in points[::max(1, len(points)//6)])
    return f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="Strompreis-Verlauf" style="width:100%;height:auto"><path d="{d}" fill="none" stroke="var(--ac)" stroke-width="2.5"/>{dots}{lab}<text x="4" y="14" font-size="11" fill="var(--mut)">{hi:.0f} Rp.</text><text x="4" y="{H-P/1.5}" font-size="11" fill="var(--mut)">{lo:.0f}</text></svg>'

def chf(x): return f"{x:,.0f}".replace(",", "'")
def fmt(x): return f"{x:.2f}".replace(".", ",")
def fmt1(x): return f"{x:.1f}".replace(".", ",")

pages = {}
def rel(v, ref):
    d = round(v, 2) - round(ref, 2)
    return "genau auf dem Niveau" if d == 0 else ("%s Rp. %s" % (fmt(abs(d)), "über" if d > 0 else "unter"))

def op_link(o):
    on = OPS.get(o["op"], {"name": "Netzbetreiber"})
    u = (on.get("url") or "").strip()
    if u and "@" not in u and " " not in u:
        href = u if u.startswith("http") else "https://" + u
        return f'<a href="{esc(href)}" rel="nofollow noopener">{esc(on["name"])}</a>'
    return esc(on["name"])

for r in rec.values():
    c, p = r["cur"], r["prev"]
    n_ops = len(r["all"])
    pre = "ab " if n_ops > 1 else ""
    ann = c["total"] * KWH / 100
    cm = statistics.median([x["cur"]["total"] for x in bycanton[r["canton"]]])
    chg = ""
    if p:
        dd = round(c["total"], 2) - round(p["total"], 2); pc = dd / p["total"] * 100
        if dd == 0:
            chg = f'<div><div class="mut">Veränderung zu {PREV}</div><b>unverändert</b></div>'
        else:
            cls = "up" if dd > 0 else "dn"; sign = "+" if dd > 0 else "−"
            chg = f'<div><div class="mut">Veränderung zu {PREV}</div><div class="{cls}"><b>{sign}{fmt(abs(dd))} Rp.</b> ({sign}{fmt1(abs(pc))}%)</div></div>'
    pts = []
    for y in YEARS:
        row = main_op(r["id"], y)
        if row and row["total"] >= 5: pts.append((y, row["total"]))
    comps = [("Energie", c["energy"]), ("Netznutzung", c["grid"]), ("Messung", c["meter"]), ("Abgaben an Gemeinwesen", c["charge"]), ("Bundesabgaben (Netzzuschlag)", c["aid"])]
    tot = sum(v for _, v in comps) or 1
    brows = "".join(f'<tr><td>{n}</td><td class="n">{fmt(v)}</td><td><span class="bar" style="width:{max(2, v/tot*100):.0f}%"></span></td></tr>' for n, v in comps if v)
    gap = c["total"] - sum(v for _, v in comps)
    if abs(gap) > 0.05:
        brows += f'<tr><td>Weitere Bestandteile</td><td class="n">{fmt(gap)}</td><td></td></tr>'
    ops = "".join(f'<tr><td>{op_link(o)}</td><td>{esc(o["product"] or "")}</td><td class="n">{fmt(o["total"])}</td></tr>' for o in sorted(r["all"], key=lambda x: x["total"]))
    multi = f'<p class="mut">In {esc(r["name"])} sind mehrere Netzbetreiber tätig (je nach Ortsteil). Angezeigt wird der tiefste Tarif; Ihr Preis hängt vom zuständigen Betreiber ab.</p>' if n_ops > 1 else ""
    plz = ", ".join(r["plz"][:6])
    body = f"""<h1>Strompreis in {esc(r['name'])} ({esc(r['canton'])}) {CUR}</h1>
<p class="mut">Gültig für {CUR}{' · PLZ ' + esc(plz) if plz else ''}</p>
<div class="card"><div class="big">{pre}{fmt(c['total'])} <span class="u">Rp./kWh</span></div>
<p>Für einen Haushalt der ElCom-Kategorie H4 (4'500 kWh pro Jahr) ergibt das in {esc(r['name'])} rund <b>CHF {chf(ann)}</b> pro Jahr (Preis × 4'500 kWh).</p>{multi}</div>
<div class="row card"><div><div class="mut">Rang Schweiz</div><b>{rank_ch[r['id']]}</b> von {len(rec)} (1 = günstigster Preis; gleiche Preise teilen den Rang)</div>
<div><div class="mut">Rang Kanton {esc(r['canton'])}</div><b>{rank_c[r['id']]}</b> von {len(bycanton[r['canton']])}</div>{chg}</div>
<p>Der Preis liegt {rel(c['total'], CH_MED)} {'' if round(c['total'],2)==round(CH_MED,2) else 'dem '}Schweizer Median ({fmt(CH_MED)} Rp./kWh) und {rel(c['total'], cm)} {'' if round(c['total'],2)==round(cm,2) else 'dem '}Kantonsmedian ({fmt(cm)} Rp./kWh).</p>
<h2>Verlauf {pts[0][0] if pts else YEARS[0]}–{CUR}</h2><div class="card">{chart(pts)}</div>
<h2>Woraus sich der Preis zusammensetzt</h2><table><tr><th>Bestandteil</th><th class="n">Rp./kWh</th><th></th></tr>{brows}</table>
<h2>Stromanbieter in {esc(r['name'])}</h2><table><tr><th>Netzbetreiber</th><th>Produkt</th><th class="n">Rp./kWh</th></tr>{ops}</table>
<p><a href="{BASE}/kanton/{slug(r['canton'])}/">Alle Gemeinden im Kanton {esc(r['canton'])}</a></p>"""
    title = f"Strompreis {r['name']} {CUR}: {pre}{fmt(c['total'])} Rp./kWh"
    desc = f"Strompreis {r['name']} ({r['canton']}) {CUR}: {pre}{fmt(c['total'])} Rp./kWh, rund CHF {chf(ann)} pro Jahr (H4). Rang {rank_ch[r['id']]} von {len(rec)}, Verlauf, Anbieter und Kostenaufbau."
    schema = {"@context": "https://schema.org", "@type": "Dataset", "name": f"Strompreis {r['name']} {CUR}", "description": desc, "creator": {"@type": "Organization", "name": "ElCom"}, "spatialCoverage": f"{r['name']}, {r['canton']}, Schweiz"}
    pages[f"gemeinde/{r['slug']}/index.html"] = page(title, desc, body, f"gemeinde/{r['slug']}/", schema)

for cn, rs in bycanton.items():
    rs = sorted(rs, key=lambda x: x["cur"]["total"])
    rk = comp_rank(rs)
    rows = "".join(f'<tr><td>{rk[x["id"]]}</td><td><a href="{BASE}/gemeinde/{x["slug"]}/">{esc(x["name"])}</a></td><td class="n">{fmt(x["cur"]["total"])}</td></tr>' for x in rs)
    med = statistics.median(x["cur"]["total"] for x in rs)
    lo, hi = rs[0], rs[-1]
    if round(lo["cur"]["total"], 2) == round(hi["cur"]["total"], 2):
        ext = f"Alle {len(rs)} Gemeinden haben denselben Preis."
    else:
        ext = f"Günstigster Preis: <b>{esc(lo['name'])}</b> ({fmt(lo['cur']['total'])}), höchster: <b>{esc(hi['name'])}</b> ({fmt(hi['cur']['total'])})."
    body = f"""<h1>Strompreise im Kanton {esc(cn)} {CUR}</h1><p>Median im Kanton: <b>{fmt(med)} Rp./kWh</b> (Schweiz: {fmt(CH_MED)}). {ext}</p>
<table><tr><th>Rang</th><th>Gemeinde</th><th class="n">Rp./kWh</th></tr>{rows}</table>"""
    pages[f"kanton/{slug(cn)}/index.html"] = page(f"Strompreise Kanton {cn} {CUR}: alle Gemeinden", f"Strompreise {CUR} aller {len(rs)} Gemeinden im Kanton {cn}. Median {fmt(med)} Rp./kWh.", body, f"kanton/{slug(cn)}/")

srt = sorted(rec.values(), key=lambda x: x["cur"]["total"])
lst = lambda xs: "".join(f'<li><a href="{BASE}/gemeinde/{x["slug"]}/">{esc(x["name"])}</a> ({esc(x["canton"])}) <span class="mut">{fmt(x["cur"]["total"])}</span></li>' for x in xs)
cl = "".join(f'<li><a href="{BASE}/kanton/{slug(c)}/">{esc(c)}</a></li>' for c in sorted(bycanton))
body = f"""<h1>Strompreise in der Schweiz {CUR}: alle Gemeinden</h1>
<p>Was kostet Strom in Ihrer Gemeinde? Offizielle Tarife der ElCom für {len(rec)} Gemeinden, mit Rang, Verlauf seit {YEARS[0]} und Kostenaufbau. Schweizer Median {CUR}: <b>{fmt(CH_MED)} Rp./kWh</b>.</p>
<input id="q" type="search" aria-label="Gemeinde oder PLZ suchen" placeholder="Gemeinde oder PLZ suchen …" autocomplete="off"><ul id="r" class="l"></ul>
<h2>Günstigste Preise {CUR}</h2><ul class="l">{lst(srt[:12])}</ul><h2>Höchste Preise {CUR}</h2><ul class="l">{lst(srt[::-1][:12])}</ul>
<h2>Nach Kanton</h2><ul class="l">{cl}</ul>
<script>const I={json.dumps([[x['name'],x['canton'],x['slug'],' '.join(x['plz'])] for x in sorted(rec.values(), key=lambda x:x['name'])], ensure_ascii=False)};
const q=document.getElementById('q'),r=document.getElementById('r');q.addEventListener('input',()=>{{const t=q.value.trim().toLowerCase();r.innerHTML='';if(t.length<2)return;I.filter(i=>(i[0]+' '+i[3]).toLowerCase().includes(t)).slice(0,30).forEach(i=>{{const l=document.createElement('li'),a=document.createElement('a');a.href='{BASE}/gemeinde/'+i[2]+'/';a.textContent=i[0]+' ('+i[1]+')';l.appendChild(a);r.appendChild(l)}})}})</script>"""
pages["index.html"] = page(f"Strompreise Schweiz {CUR}: Tarife aller Gemeinden im Vergleich", f"Strompreis pro Gemeinde {CUR}: offizielle ElCom-Tarife für {len(rec)} Schweizer Gemeinden, Rang, Verlauf und Kostenaufbau. Median {fmt(CH_MED)} Rp./kWh.", body, "")

if os.path.isdir(OUT): shutil.rmtree(OUT)
for p, c in pages.items():
    fp = os.path.join(OUT, p); os.makedirs(os.path.dirname(fp), exist_ok=True)
    open(fp, "w", encoding="utf-8").write(c)
site = "https://neonwisp34.github.io"
urls = [f"{site}{BASE}/{p[:-10]}" for p in pages]
open(os.path.join(OUT, "sitemap.xml"), "w").write('<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">' + "".join(f"<url><loc>{u}</loc></url>" for u in urls) + "</urlset>")
open(os.path.join(OUT, "robots.txt"), "w").write(f"User-agent: *\nAllow: /\nSitemap: {site}{BASE}/sitemap.xml\n")
open(os.path.join(OUT, ".nojekyll"), "w").write("")
print(len(pages), "pages;", CUR, "CH median", round(CH_MED, 2), "| cheapest", srt[0]["name"], srt[0]["cur"]["total"], "| dearest", srt[-1]["name"], srt[-1]["cur"]["total"])
