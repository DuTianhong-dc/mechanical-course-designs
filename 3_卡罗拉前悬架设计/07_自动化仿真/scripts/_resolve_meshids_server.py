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

body_map = {}
face_map = {}
for p in Model.Geometry.Children:
    try:
        pname = s(p.Name)
    except:
        pname = "?"
    try:
        blist = list(p.Children)
    except:
        continue
    for b in blist:
        try:
            gb = b.GetGeoBody()
        except:
            continue
        try:
            bid = int(gb.Id)
        except:
            bid = -1
        try:
            bname = s(b.Name)
        except:
            bname = "?"
        try:
            vol = float(s(gb.Volume).split()[0])
        except:
            vol = -1.0
        body_map[bid] = {"part": pname, "name": bname, "vol": vol}
        try:
            faces = list(gb.Faces)
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
                c = list(f.Centroid)
                cx, cy, cz = float(c[0]), float(c[1]), float(c[2])
            except:
                try:
                    c = list(f.Centroid())
                    cx, cy, cz = float(c[0]), float(c[1]), float(c[2])
                except:
                    pass
            face_map[fid] = {"body": bid, "area": area, "c": [cx, cy, cz]}

sets = []
m = Model.Mesh
for c in m.Children:
    r = {"name": s(c.Name), "type": s(c.GetType()).split(".")[-1], "state": s(c.ObjectState)}
    ids = None
    for attr in ["Location", "Scoping"]:
        try:
            v = getattr(c, attr)
            ids = [int(i) for i in v.Ids]
            break
        except:
            pass
    if ids is None:
        ids = []
    res = []
    for i in ids:
        e = {"id": i}
        if i in body_map:
            e["kind"] = "body"
            e.update(body_map[i])
        elif i in face_map:
            e["kind"] = "face"
            e["body"] = face_map[i]["body"]
            e["area"] = round(face_map[i]["area"], 9)
            e["c"] = [round(v, 6) for v in face_map[i]["c"]]
        else:
            e["kind"] = "unknown"
        res.append(e)
    r["resolved"] = res
    sets.append(r)

out = {"nbody": len(body_map), "nface": len(face_map), "sets": sets}
with io.open(OUT, "w", encoding="utf-8") as f:
    f.write(json.dumps(out, ensure_ascii=False, indent=1))
print("RESOLVE DONE")
