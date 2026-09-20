"""Convertit les shapefiles de Vecteur/ en static/data/base.json (WGS84, 2D, Point/LineString).
Usage : python prepare_data.py Vecteur   (à relancer seulement si la base de départ change)"""
import sys, json, geopandas as gpd, shapely
src = sys.argv[1] if len(sys.argv) > 1 else "Vecteur"
# fichier: (catégorie, champ nom, champ type)
MAP = {"route_bon": ("voirie", "name", "fclass"), "caniveau_BON": ("assainissement", "name", "fclass"),
       "Lampadaire_BON": ("eclairage", "name", "fclass"), "Marcher_BON": ("marche_place", "name", "fclass"),
       "Place_publique_bon": ("marche_place", "name", "fclass"), "sante_bon": ("sante", "Nom_SAN", "Type"),
       "Enseignement_bon": ("education", "Nom_ENS", "Type")}
out = {}
for stem, (cat, fn, ft) in MAP.items():
    g = gpd.read_file(f"{src}/{stem}.shp").to_crs(4326)
    g.geometry = shapely.force_2d(g.geometry)
    g = g.explode(index_parts=False).reset_index(drop=True)
    if g.geom_type.iloc[0] == "LineString":
        g.geometry = g.geometry.simplify(0.00001)
    g.geometry = shapely.set_precision(g.geometry.values, 1e-6)
    feats = []
    for i, r in g.iterrows():
        if r.geometry is None or r.geometry.is_empty: continue
        nom = r[fn] if isinstance(r[fn], str) else None
        typ = r[ft] if isinstance(r[ft], str) else None
        feats.append({"type": "Feature", "geometry": json.loads(shapely.to_geojson(r.geometry)),
                      "properties": {"id": f"{stem.lower()}-{i}", "nom": nom, "type": typ}})
    out.setdefault(cat, {"type": "FeatureCollection", "features": []})["features"] += feats
    print(stem, cat, len(feats))
json.dump(out, open("static/data/base.json", "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
c = gpd.read_file(f"{src}/cotonou.shp").to_crs(4326)
c.geometry = shapely.force_2d(c.geometry)
c[["geometry"]].to_file("static/data/cotonou.json", driver="GeoJSON")
