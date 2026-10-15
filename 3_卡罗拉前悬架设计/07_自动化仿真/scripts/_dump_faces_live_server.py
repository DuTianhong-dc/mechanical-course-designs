import io, json

OUT = r"__OUT__"

def s(x):
    try:
        return str(x)
    except:
        try:
            return repr(x)
        except:
            return "?"

rows = []

def walk_part(o):
    try:
        kids = o.Children
    except:
        return
    for c in kids:
        try:
            cat = s(c.DataModelObjectCategory)
        except:
            cat = "?"
        if cat == "Body":
            bid = None
            bname = None
            try:
                bid = int(c.GetGeoBody().Id)
            except:
                pass
            try:
                bname = c.Name.encode("utf-8").encode("hex")
            except:
                pass
            try:
                faces = list(c.GetGeoBody().Faces)
            except:
                faces = []
            for f in faces:
                try:
                    fid = int(f.Id)
                except:
                    continue
                try:
                    area = float(f.Area)
                except:
                    area = -1.0
                cx = cy = cz = 0.0
                try:
                    cpt = list(f.Centroid)
                    cx, cy, cz = float(cpt[0]), float(cpt[1]), float(cpt[2])
                except:
                    pass
                try:
                    ftype = s(f.SurfaceType).split(".")[-1]
                except:
                    ftype = "?"
                rows.append([bid, bname, fid, round(area, 12), round(cx, 9), round(cy, 9), round(cz, 9), ftype])
        else:
            walk_part(c)

walk_part(Model.Geometry)
out = {"n": len(rows), "faces": rows}
with io.open(OUT, "w", encoding="utf-8") as f:
    f.write(json.dumps(out, ensure_ascii=False))
print("DUMP FACES LIVE DONE n=" + str(len(rows)))
