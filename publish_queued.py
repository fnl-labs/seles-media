#!/usr/bin/env python3
"""
publish_queued.py — pubblica i post in coda quando arriva la loro ora.

Gira su GitHub Actions (vedi .github/workflows/pubblica.yml) ogni 10 minuti:
legge i file .json in coda/, e per ognuno che ha raggiunto l'orario previsto
pubblica su Instagram e/o Facebook, poi lo sposta in pubblicati/.

Un post in coda è un JSON così:
{
  "quando": "2026-09-27T00:00:00+02:00",   ora locale italiana
  "dove": ["ig", "fb"],
  "immagini": ["media/20260927-match-c11.jpg"],
  "didascalia": "testo del post..."
}

Il token della Pagina arriva dal secret META_PAGE_TOKEN.
Solo libreria standard: nessuna dipendenza da installare.
"""
import os, sys, json, time, pathlib, datetime, urllib.request, urllib.parse, urllib.error

ROOT = pathlib.Path(__file__).resolve().parent
CODA, FATTI = ROOT / "coda", ROOT / "pubblicati"
BASE_URL = "https://fnl-labs.github.io/seles-media"
VER = os.environ.get("META_API_VERSION", "v23.0")
API = f"https://graph.facebook.com/{VER}"
TOKEN = os.environ.get("META_PAGE_TOKEN", "")
PAGE = os.environ.get("META_PAGE_ID", "")
IG = os.environ.get("META_IG_USER_ID", "")

def api(method, path, **params):
    params["access_token"] = TOKEN
    data = urllib.parse.urlencode(params).encode()
    url = f"{API}/{path}"
    if method == "GET": url += "?" + data.decode(); data = None
    req = urllib.request.Request(url, data=data, method=method)
    try:
        with urllib.request.urlopen(req, timeout=90) as r: return json.load(r)
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"Meta {e.code}: {e.read().decode(errors='replace')[:400]}")

def attendi(cid):
    for _ in range(60):
        st = api("GET", cid, fields="status_code")
        if st.get("status_code") == "FINISHED": return
        if st.get("status_code") == "ERROR": raise RuntimeError(f"contenitore in errore: {cid}")
        time.sleep(4)
    raise RuntimeError("Instagram non ha finito di elaborare l'immagine")

def pubblica_ig(urls, caption):
    if len(urls) == 1:
        c = api("POST", f"{IG}/media", image_url=urls[0], caption=caption)
    else:
        figli = []
        for u in urls:
            k = api("POST", f"{IG}/media", image_url=u, is_carousel_item="true"); attendi(k["id"]); figli.append(k["id"])
        c = api("POST", f"{IG}/media", media_type="CAROUSEL", children=",".join(figli), caption=caption)
    attendi(c["id"])
    r = api("POST", f"{IG}/media_publish", creation_id=c["id"])
    return api("GET", r["id"], fields="permalink").get("permalink", r["id"])

def pubblica_fb(urls, caption):
    if len(urls) == 1:
        r = api("POST", f"{PAGE}/photos", url=urls[0], message=caption)
        pid = r.get("post_id") or r["id"]
    else:
        media = [api("POST", f"{PAGE}/photos", url=u, published="false")["id"] for u in urls]
        p = {"message": caption}
        for i, m in enumerate(media): p[f"attached_media[{i}]"] = json.dumps({"media_fbid": m})
        pid = api("POST", f"{PAGE}/feed", **p)["id"]
    return f"https://www.facebook.com/{pid}"

def main():
    if not (TOKEN and PAGE and IG):
        print("✗ mancano i secret META_PAGE_TOKEN / META_PAGE_ID / META_IG_USER_ID"); sys.exit(1)
    FATTI.mkdir(exist_ok=True)
    adesso = datetime.datetime.now(datetime.timezone.utc)
    fatti_ora = []
    for f in sorted(CODA.glob("*.json")):
        post = json.loads(f.read_text(encoding="utf-8"))
        quando = datetime.datetime.fromisoformat(post["quando"])
        if quando.tzinfo is None: quando = quando.replace(tzinfo=datetime.timezone.utc)
        if quando > adesso:
            print(f"· {f.name}: non ancora ({quando.isoformat()})"); continue
        urls = [f"{BASE_URL}/{p}" for p in post["immagini"]]
        cap = post.get("didascalia", "")
        esiti = {}
        for dove in post.get("dove", ["ig", "fb"]):
            try:
                esiti[dove] = pubblica_ig(urls, cap) if dove == "ig" else pubblica_fb(urls, cap)
                print(f"✓ {f.name} → {dove}: {esiti[dove]}")
            except Exception as e:
                esiti[dove] = f"ERRORE: {e}"; print(f"✗ {f.name} → {dove}: {e}")
        post["esiti"] = esiti
        post["pubblicato_il"] = adesso.isoformat()
        (FATTI / f.name).write_text(json.dumps(post, ensure_ascii=False, indent=2), encoding="utf-8")
        f.unlink(); fatti_ora.append(f.name)
        if any(str(v).startswith("ERRORE") for v in esiti.values()): sys.exit(1)
    if not fatti_ora: print("niente da pubblicare adesso")

if __name__ == "__main__": main()
