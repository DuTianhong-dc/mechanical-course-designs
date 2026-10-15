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

out = {}

rp_detail = []
rp_stat = {}
for rp in Model.RemotePoints.Children:
    st = "?"
    try:
        st = s(rp.ObjectState)
    except:
        pass
    rp_stat[st] = rp_stat.get(st, 0) + 1
    if st != "FullyDefined":
        r = {"name": s(rp.Name), "state": st}
        try:
            r["type"] = s(rp.GetType()).split(".")[-1]
        except:
            pass
        for attr in ["SelectionType", "ScopingMethod", "Behavior", "Formulation", "MeshRegionId"]:
            try:
                r[attr] = s(getattr(rp, attr))
            except:
                pass
        try:
            r["ids"] = [int(i) for i in rp.Location.Ids]
        except:
            pass
        try:
            r["suppressed"] = s(rp.Suppressed)
        except:
            pass
        rp_detail.append(r)
out["rp_stat"] = rp_stat
out["rp_bad"] = rp_detail

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
            r = {"name": s(c.Name)}
            try:
                r["state"] = s(c.ObjectState)
            except:
                pass
            for attr in ["Mass", "Behavior", "AppliedBy", "Location"]:
                try:
                    v = getattr(c, attr)
                    if attr == "Location":
                        try:
                            r[attr + "_ids"] = [int(i) for i in v.Ids]
                        except:
                            pass
                    else:
                        r[attr] = s(v)
                except:
                    pass
            pm_list.append(r)
        else:
            walk(c, depth + 1)

walk(Model)
out["point_masses"] = pm_list

cs_list = []
cs_stat = {}
for cs in Model.CoordinateSystems.Children:
    st = "?"
    try:
        st = s(cs.ObjectState)
    except:
        pass
    cs_stat[st] = cs_stat.get(st, 0) + 1
    r = {"name": s(cs.Name), "state": st}
    try:
        r["suppressed"] = s(cs.Suppressed)
    except:
        pass
    try:
        r["type"] = s(cs.GetType()).split(".")[-1]
    except:
        pass
    if st != "FullyDefined":
        for attr in ["CoordinateSystemType", "OriginDefineBy", "Location", "Source"]:
            try:
                v = getattr(cs, attr)
                try:
                    r[attr] = [int(i) for i in v.Ids]
                except:
                    r[attr] = s(v)
            except:
                pass
    cs_list.append(r)
out["cs_stat"] = cs_stat
out["cs_all"] = cs_list

with io.open(OUT, "w", encoding="utf-8") as f:
    f.write(json.dumps(out, ensure_ascii=False, indent=1))
print("PROBE RP CS DONE")
