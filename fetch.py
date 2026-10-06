"""Fetch ElCom electricity prices (LINDAS SPARQL) -> data/prices.json + data/municipalities.json.
Run: python fetch.py   (idempotent; safe to re-run yearly/daily)
"""
import json, os, sys, time, urllib.parse, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
os.makedirs(DATA, exist_ok=True)
EP = "https://lindas.admin.ch/query"
E = "https://energy.ld.admin.ch/elcom/electricityprice/"

def run(q, tries=4):
    body = urllib.parse.urlencode({"query": q}).encode()
    for n in range(tries):
        try:
            req = urllib.request.Request(EP, data=body, headers={"Accept": "application/sparql-results+json", "User-Agent": "strompreise-ch-builder"})
            with urllib.request.urlopen(req, timeout=180) as r:
                return json.load(r)["results"]["bindings"]
        except Exception as e:
            print("retry", n, e, file=sys.stderr)
            time.sleep(5 * (n + 1))
    raise RuntimeError("SPARQL failed")

def periods():
    rows = run(f"SELECT DISTINCT ?p WHERE {{ ?o <{E}dimension/period> ?p }}")
    return sorted(int(float(r["p"]["value"])) for r in rows)

def prices(year, category="H4", product="standard", page=5000):
    out, off = [], 0
    while True:
        q = f"""SELECT ?m ?op ?total ?energy ?grid ?aid ?charge ?fix ?etype ?meter WHERE {{
          ?o <{E}dimension/category> <{E}category/{category}> ; <{E}dimension/product> <{E}product/{product}> ;
             <{E}dimension/period> ?p ; <{E}dimension/municipality> ?m ; <{E}dimension/operator> ?op ; <{E}dimension/total> ?total .
          FILTER(STR(?p)="{year}")
          OPTIONAL {{ ?o <{E}dimension/energy> ?energy }} OPTIONAL {{ ?o <{E}dimension/gridusage> ?grid }}
          OPTIONAL {{ ?o <{E}dimension/aidfee> ?aid }} OPTIONAL {{ ?o <{E}dimension/charge> ?charge }}
          OPTIONAL {{ ?o <{E}dimension/fixcosts> ?fix }} OPTIONAL {{ ?o <{E}dimension/meteringrate> ?meter }} OPTIONAL {{ ?o <{E}dimension/energyname> ?etype }}
        }} ORDER BY ?m ?op LIMIT {page} OFFSET {off}"""
        rows = run(q)
        out += rows
        if len(rows) < page:
            break
        off += page
    return out

def municipalities():
    q = """SELECT ?m ?name ?plz WHERE { ?m a <https://schema.ld.admin.ch/PoliticalMunicipality> ; <http://schema.org/name> ?name .
           OPTIONAL { ?m <http://schema.org/postalCode> ?plz } }"""
    return run(q)


def v(b, k):
    return b[k]["value"] if k in b else None

def fetch_all():
    ys = periods()
    hist = {}
    for y in ys:
        for b in prices(y):
            m = v(b, "m").rsplit("/", 1)[-1]
            op = v(b, "op").rsplit("/", 1)[-1]
            hist.setdefault(m, {}).setdefault(str(y), []).append({
                "op": op, "total": float(v(b, "total")),
                "energy": float(v(b, "energy") or 0), "grid": float(v(b, "grid") or 0),
                "aid": float(v(b, "aid") or 0), "charge": float(v(b, "charge") or 0),
                "fix": float(v(b, "fix") or 0), "meter": float(v(b, "meter") or 0), "product": v(b, "etype")})
        print("year", y, "done", flush=True)
    ops = {v(b, "op").rsplit("/", 1)[-1]: {"name": v(b, "name"), "url": v(b, "url")}
           for b in run(f'SELECT ?op ?name ?url WHERE {{ ?op a <http://schema.org/Organization> ; <http://schema.org/name> ?name . FILTER(STRSTARTS(STR(?op),"{E}operator/")) OPTIONAL{{?op <http://schema.org/url> ?url}} }}')}
    cantons = {v(b, "c").rsplit("/", 1)[-1]: v(b, "n") for b in run('SELECT ?c ?n WHERE { ?c a <https://schema.ld.admin.ch/Canton> ; <http://schema.org/name> ?n }')}
    muni = {}
    for b in run("""SELECT ?m ?name ?plz ?c WHERE { ?m a <https://schema.ld.admin.ch/PoliticalMunicipality> ; <http://schema.org/name> ?name ;
                    <http://schema.org/containedInPlace> ?c . FILTER(STRSTARTS(STR(?c),"https://ld.admin.ch/canton/"))
                    OPTIONAL { ?m <http://schema.org/postalCode> ?plz } }"""):
        k = v(b, "m").rsplit("/", 1)[-1]
        e = muni.setdefault(k, {"name": v(b, "name"), "canton": v(b, "c").rsplit("/", 1)[-1], "plz": []})
        if v(b, "plz") and v(b, "plz") not in e["plz"]:
            e["plz"].append(v(b, "plz"))
    json.dump({"history": hist, "operators": ops, "cantons": cantons, "municipalities": muni}, open(os.path.join(DATA, "all.json"), "w", encoding="utf-8"), ensure_ascii=False)
    print("saved", len(hist), "municipalities with prices;", len(muni), "munis;", len(cantons), "cantons;", len(ops), "operators")

if __name__ == "__main__":
    ys = periods()
    print("periods:", ys)
    fetch_all()
