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

def dump(obj, maxlen=120):
    r = {}
    try:
        names = dir(obj)
    except:
        names = []
    for n in names:
        if n.startswith("_"):
            continue
        try:
            v = getattr(obj, n)
        except:
            continue
        if v is None:
            continue
        try:
            if callable(v):
                continue
        except:
            pass
        vs = None
        try:
            vs = s(v)
        except:
            continue
        if len(vs) > maxlen:
            vs = vs[:maxlen] + "..."
        r[n] = vs
    return r

out = {}

# target CS detail (objid 990/1025/1033), regardless of state
cs_detail = []
for cs in Model.CoordinateSystems.Children:
    try:
        oid = s(getattr(cs, "ObjectId", "?"))
    except:
        continue
    if oid in ("990", "1025", "1033"):
        r = dump(cs)
        for attr in ["OriginLocation", "PrimaryAxisLocation"]:
            try:
                v = getattr(cs, attr)
                try:
                    r[attr + "_Ids"] = [int(i) for i in v.Ids]
                except Exception as e:
                    r[attr + "_Ids"] = "ERR:%r" % e
            except Exception as e:
                r[attr + "_Ids"] = "GETERR:%r" % e
        cs_detail.append(r)
out["cs_detail"] = cs_detail

# spring CS refs
spr = None
for g in Model.Connections.Children:
    try:
        if "Spring" in s(g.GetType()):
            spr = g
            break
    except:
        pass
if spr is not None:
    r = {}
    for attr in ["ReferenceCoordinateSystem", "MobileCoordinateSystem"]:
        try:
            v = getattr(spr, attr)
            if v is None:
                r[attr] = None
            else:
                r[attr] = s(getattr(v, "Name", "?")) + "@" + s(getattr(v, "ObjectId", "?"))
        except Exception as e:
            r[attr] = "ERR:%r" % e
    out["spring_cs"] = r

# remote point CS ref
for rp in Model.RemotePoints.Children:
    try:
        if rp.Name.encode("utf-8").encode("hex") == "e8bf9ce7a88be782b9":
            r = {}
            try:
                v = rp.CoordinateSystem
                r["CoordinateSystem"] = s(getattr(v, "Name", "?")) + "@" + s(getattr(v, "ObjectId", "?"))
            except Exception as e:
                r["CoordinateSystem"] = "ERR:%r" % e
            out["rp_cs"] = r
            break
    except:
        pass

# point mass CS ref (scan props)
pm = None

def find_pm(o, depth=0):
    global pm
    if depth > 6:
        return
    try:
        kids = o.Children
    except:
        return
    for c in kids:
        try:
            cat = s(c.DataModelObjectCategory)
        except:
            cat = "?"
        if cat == "PointMass":
            if pm is None:
                pm = c
        else:
            find_pm(c, depth + 1)

find_pm(Model)
if pm is not None:
    r = {}
    for n in dir(pm):
        if "oordinate" in n or "Origin" in n or "Axis" in n:
            try:
                v = getattr(pm, n)
                if v is None:
                    continue
                try:
                    if callable(v):
                        continue
                except:
                    pass
                r[n] = s(v)[:120]
            except:
                pass
    out["pm_cs_props"] = r

with io.open(OUT, "w", encoding="utf-8") as f:
    f.write(json.dumps(out, ensure_ascii=False, indent=1))
print("PROBE CS TARGET DONE")
