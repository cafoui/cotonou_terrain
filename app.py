import os, json, base64, tempfile, zipfile
from datetime import datetime
from flask import Flask, request, jsonify, send_file, abort, Response
from flask_compress import Compress
import psycopg
from psycopg.types.json import Jsonb

app = Flask(__name__, static_folder="static", static_url_path="")
Compress(app)
app.config["MAX_CONTENT_LENGTH"] = 6 * 1024 * 1024
DB = os.environ.get("DATABASE_URL", "")
CODE = os.environ.get("ACCESS_CODE", "")  # code d'accès partagé (optionnel mais conseillé)
CATS = ["voirie", "assainissement", "eclairage", "point_eau", "marche_place", "sante", "education"]


def db():
    return psycopg.connect(DB, autocommit=True)


def init():
    with db() as c:
        c.execute("""CREATE TABLE IF NOT EXISTS records(
            key text PRIMARY KEY, cat text NOT NULL, geom jsonb,
            props jsonb NOT NULL DEFAULT '{}', photo bytea, updated_at timestamptz DEFAULT now())""")


if DB:
    init()


@app.before_request
def guard():
    p = request.path
    if CODE and p.startswith("/api/") and not p.startswith("/api/photo/"):
        if (request.headers.get("X-Code") or request.args.get("c")) != CODE:
            abort(401)


@app.get("/")
def index():
    return app.send_static_file("index.html")


@app.get("/data/base.json")
def base_json():  # servi en mémoire pour que la compression gzip s'applique (1,3 Mo -> ~350 Ko)
    return Response(open("static/data/base.json", "rb").read(), mimetype="application/json")


@app.get("/api/records")
def list_records():
    with db() as c:
        rows = c.execute("SELECT key,cat,geom,props,photo IS NOT NULL,updated_at FROM records").fetchall()
    return jsonify([dict(key=k, cat=ct, geom=g if k.startswith("new-") else None, props=p,
                         has_photo=hp, updated_at=u.isoformat()) for k, ct, g, p, hp, u in rows])


@app.post("/api/records")
def save():
    d = request.get_json()
    key, cat = d["key"], d["cat"]
    if cat not in CATS:
        abort(400)
    photo = base64.b64decode(d["photo"].split(",")[1]) if d.get("photo") else None
    geom = Jsonb(d["geom"]) if d.get("geom") else None
    with db() as c:
        c.execute("""INSERT INTO records(key,cat,geom,props,photo) VALUES(%s,%s,%s,%s,%s)
            ON CONFLICT(key) DO UPDATE SET props=EXCLUDED.props,
            photo=COALESCE(EXCLUDED.photo, records.photo),
            geom=COALESCE(EXCLUDED.geom, records.geom), updated_at=now()""",
                  (key, cat, geom, Jsonb(d["props"]), photo))
    return {"ok": True}


@app.delete("/api/records/<key>")
def delete(key):
    if not key.startswith("new-"):  # on ne supprime que les infrastructures ajoutées
        abort(400)
    with db() as c:
        c.execute("DELETE FROM records WHERE key=%s", (key,))
    return {"ok": True}


@app.get("/api/photo/<key>")
def photo(key):
    with db() as c:
        r = c.execute("SELECT photo FROM records WHERE key=%s", (key,)).fetchone()
    if not r or not r[0]:
        abort(404)
    return Response(bytes(r[0]), mimetype="image/jpeg")


def build(recs, base, base_url):
    """Fusionne la base de départ et les fiches d'enquête -> {catégorie: GeoDataFrame}."""
    import geopandas as gpd
    from shapely.geometry import shape
    recs = dict(recs)
    rows = {k: [] for k in CATS}

    def row(geom, r, **kw):
        d = dict(kw)
        if r:
            d.update(r[3])
            d["photo_url"] = f"{base_url}/api/photo/{r[0]}" if r[4] else None
        d["geometry"] = geom
        return d

    for cat, fc in base.items():
        for f in fc["features"]:
            p = f["properties"]
            r = recs.pop(p["id"], None)
            rows[cat].append(row(shape(f["geometry"]), r, id=p["id"], nom_base=p.get("nom"),
                                 type_base=p.get("type"), statut="verifie" if r else "non_visite"))
    for r in recs.values():  # infrastructures ajoutées sur le terrain
        if r[2]:
            rows[r[1]].append(row(shape(r[2]), r, id=r[0], statut="nouveau"))
    out = {}
    for cat, rs in rows.items():
        if rs:
            g = gpd.GeoDataFrame(rs, geometry="geometry", crs=4326)
            c = g.to_crs(32631).geometry.centroid
            g["x_utm31"], g["y_utm31"] = c.x.round(1), c.y.round(1)
            out[cat] = g
    return out


def write(out, fmt):
    tmp = tempfile.mkdtemp()
    stamp = datetime.now().strftime("%Y%m%d_%H%M")
    if fmt == "zip":
        for cat, g in out.items():
            g.to_file(f"{tmp}/{cat}.shp", encoding="utf-8")
        path = f"{tmp}/enquete_{stamp}.zip"
        with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
            for fn in os.listdir(tmp):
                if not fn.endswith(".zip"):
                    z.write(f"{tmp}/{fn}", fn)
        return path
    path = f"{tmp}/enquete_{stamp}.gpkg"
    for cat, g in out.items():
        g.to_file(path, layer=cat, driver="GPKG")
    return path


@app.get("/api/export")
def export():
    base = json.load(open("static/data/base.json", encoding="utf-8"))
    with db() as c:
        recs = {r[0]: r for r in c.execute(
            "SELECT key,cat,geom,props,photo IS NOT NULL FROM records").fetchall()}
    path = write(build(recs, base, request.host_url.rstrip("/")), request.args.get("fmt", "gpkg"))
    return send_file(path, as_attachment=True)
