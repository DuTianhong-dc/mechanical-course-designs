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

cs_list = []
for cs in Model.CoordinateSystems.Children:
    r = {"name": s(cs.Name)}
    try:
        r["state"] = s(cs.ObjectState)
    except:
        pass
    try:
        r["objid"] = s(getattr(cs, "ObjectId", "?"))
    except:
        pass
    try:
        r["sup"] = s(cs.Suppressed)
    except:
        pass
    cs_list.append(r)
out["cs"] = cs_list

joint_refs = []
for g in Model.Connections.Children:
    try:
        kids = list(g.Children)
    except:
        kids = []
    targets = kids if kids else [g]
    for ch in targets:
        try:
            name = s(ch.Name)
        except:
            continue
        rr = {"joint": name}
        for attr in ["MobileCoordinateSystem", "ReferenceCoordinateSystem"]:
            try:
                v = getattr(ch, attr)
                if v is None:
                    rr[attr] = None
                else:
                    rr[attr] = s(getattr(v, "Name", "?")) + "@" + s(getattr(v, "ObjectId", "?"))
            except:
                pass
        joint_refs.append(rr)
out["joint_cs_refs"] = joint_refs

ud_full = []
for cs in Model.CoordinateSystems.Children:
    try:
        if s(cs.ObjectState) == "UnderDefined":
            ud_full.append(dump(cs))
    except:
        pass
out["cs_ud_full"] = ud_full

with io.open(OUT, "w", encoding="utf-8") as f:
    f.write(json.dumps(out, ensure_ascii=False, indent=1))
print("PROBE CS REF DONE")
