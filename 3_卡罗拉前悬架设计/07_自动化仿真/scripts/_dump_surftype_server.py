import io, json

OUT = r"C:\Users\dth15\Desktop\ANSYS\automation\logs\surftype_swap3.json"

def s(x):
    try:
        return str(x)
    except Exception:
        try:
            return repr(x)
        except Exception:
            return "?"

out = {}

def flush():
    with io.open(OUT, "w", encoding="utf-8") as f:
        f.write(json.dumps(out, ensure_ascii=False))

st = {}
cnt = {"bodies": 0, "faces": 0, "no_geo": 0}

def walk(o):
    try:
        kids = o.Children
    except Exception:
        return
    for c in kids:
        try:
            cat = s(c.DataModelObjectCategory)
        except Exception:
            cat = "?"
        if cat == "Body":
            cnt["bodies"] += 1
            try:
                gb = c.GetGeoBody()
                gid = str(int(gb.Id))
                rows = []
                for f in gb.Faces:
                    try:
                        cen = f.Centroid
                        cx, cy, cz = float(cen[0]), float(cen[1]), float(cen[2])
                    except Exception:
                        cx = cy = cz = None
                    tp = "?"
                    for attr in ("SurfaceType", "GeoSurfaceType", "Type"):
                        try:
                            v = getattr(f, attr)
                            tp = s(v)
                            if tp and tp != "?":
                                break
                        except Exception:
                            pass
                    rows.append([int(f.Id), round(float(f.Area), 9), cx, cy, cz, tp])
                    cnt["faces"] += 1
                if gid in st:
                    st[gid].extend(rows)
                else:
                    st[gid] = rows
            except Exception as e:
                cnt["no_geo"] += 1
                st["ERR_" + s(c.Name)[:18]] = ["%r" % e]
        walk(c)

walk(Model.Geometry)

out["geom_surftype"] = st
out.update(cnt)
flush()
out["stage"] = "SURFTYPE DUMP V2 DONE"
flush()
print("SURFTYPE DUMP V2 DONE")
