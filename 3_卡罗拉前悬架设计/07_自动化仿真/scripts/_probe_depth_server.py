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

def dump(obj, maxlen=150):
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

# 1) the special remote point (1023) + reference internal RP70
rp_ref = None
rp_tgt = None
for rp in Model.RemotePoints.Children:
    try:
        nmh = rp.Name.encode("utf-8").encode("hex")
    except:
        continue
    if nmh == "e8bf9ce7a88be782b9":
        rp_tgt = rp
    if nmh == "e58685e983a8e8bf9ce7a88be782b9 70":
        rp_ref = rp

for tag, rp in [("rp1023", rp_tgt), ("rp70", rp_ref)]:
    if rp is None:
        out[tag] = "NOT FOUND"
        continue
    r = {"name": s(rp.Name), "state": s(rp.ObjectState)}
    for attr in ["Ids", "MeshRegionId", "SelectionType", "ScopingMethod"]:
        try:
            r[attr] = s(getattr(rp, attr))
        except:
            pass
    try:
        r["Location_Ids"] = [int(i) for i in rp.Location.Ids]
    except Exception as e:
        r["Location_Ids"] = "ERR:%r" % e
    out[tag] = r

# 2) point mass full
pm_list = []
def walk(o, depth=0):
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
            r = {"name": s(c.Name), "state": s(c.ObjectState)}
            for attr in ["Mass", "Behavior", "AppliedBy"]:
                try:
                    r[attr] = s(getattr(c, attr))
                except:
                    pass
            try:
                r["Location_Ids"] = [int(i) for i in c.Location.Ids]
            except Exception as e:
                r["Location_Ids"] = "ERR:%r" % e
            pm_list.append(r)
        else:
            walk(c, depth + 1)
walk(Model)
out["point_masses"] = pm_list

# 3) detail dump for the 3 UD coordinate systems
cs_detail = []
for cs in Model.CoordinateSystems.Children:
    try:
        st = s(cs.ObjectState)
    except:
        continue
    if st == "UnderDefined":
        cs_detail.append(dump(cs))
out["cs_ud"] = cs_detail

with io.open(OUT, "w", encoding="utf-8") as f:
    f.write(json.dumps(out, ensure_ascii=False, indent=1))
print("PROBE DEPTH DONE")
