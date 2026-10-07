"""Fetch Swiss day-ahead spot prices (hourly) -> data/spot.json.
Source: Energy-Charts (Fraunhofer ISE), CC BY 4.0, data from ENTSO-E / Bundesnetzagentur | SMARD.de.
Keeps the old file if the API fails, so the site never breaks."""
import datetime as dt, json, os, sys, time, urllib.request, urllib.error

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "data", "spot.json")

def get(url, tries=5):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Strompreislupe/1.0 (github.com/Neonwisp34/strompreise)"})
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.load(r)
        except (urllib.error.URLError, json.JSONDecodeError, TimeoutError) as e:
            print("retry", i + 1, e, file=sys.stderr)
            time.sleep(20 * (i + 1))
    return None

today = dt.date.today()
d = get(f"https://api.energy-charts.info/price?bzn=CH&start={today - dt.timedelta(days=1)}&end={today + dt.timedelta(days=2)}")
if not d or not d.get("price") or len(d["price"]) != len(d["unix_seconds"]):
    print("spot fetch failed, keeping old file", file=sys.stderr)
    sys.exit(0)
pts = [[t, p] for t, p in zip(d["unix_seconds"], d["price"]) if p is not None]
json.dump({"unit": d.get("unit", "EUR / MWh"), "fetched": int(time.time()), "points": pts}, open(OUT, "w"))
print(len(pts), "hourly points", dt.datetime.utcfromtimestamp(pts[0][0]), "->", dt.datetime.utcfromtimestamp(pts[-1][0]))
