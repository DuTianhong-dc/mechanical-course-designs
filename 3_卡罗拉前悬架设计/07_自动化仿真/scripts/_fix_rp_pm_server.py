import io, json

OUT = r"__OUT__"
FACE = __FACE__

def s(x):
    try:
        return str(x)
    except:
        try:
            return repr(x)
        except:
            return "?"

out = {}

def flush():
    with io.open(OUT, "w", encoding="utf-8") as f:
        f.write(json.dumps(out, ensure_ascii=False, indent=1))

rp = None
for r in Model.RemotePoints.Children:
    try:
        if r.Name.encode("utf-8").encode("hex") == "e8bf9ce7a88be782b9":
            rp = r
    except:
        pass

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

res = {}
if rp is not None:
    try:
        sel = ExtAPI.SelectionManager.CreateSelectionInfo(SelectionTypeEnum.GeometryEntities)
        sel.Ids = [FACE]
        rp.Location = sel
        res["rp_set"] = "OK"
    except Exception as e:
        res["rp_set"] = "ERR:%r" % e
    try:
        res["rp_loc_back"] = [int(i) for i in rp.Location.Ids]
    except:
        pass
    try:
        res["rp_state"] = s(rp.ObjectState)
    except:
        pass
    try:
        res["rp_ids"] = s(rp.Ids)
    except:
        pass

if pm is not None:
    try:
        sel = ExtAPI.SelectionManager.CreateSelectionInfo(SelectionTypeEnum.GeometryEntities)
        sel.Ids = [FACE]
        pm.Location = sel
        res["pm_set"] = "OK"
    except Exception as e:
        res["pm_set"] = "ERR:%r" % e
    try:
        res["pm_loc_back"] = [int(i) for i in pm.Location.Ids]
    except:
        pass
    try:
        res["pm_state"] = s(pm.ObjectState)
    except:
        pass

out["step1"] = res
flush()

if rp is not None and s(rp.ObjectState) != "FullyDefined":
    import time
    t0 = time.time()
    try:
        Model.Mesh.GenerateMesh()
        out["gen"] = "OK"
    except Exception as e:
        out["gen"] = "ERR:%r" % e
    out["gen_s"] = round(time.time() - t0, 1)
    try:
        out["rp_state2"] = s(rp.ObjectState)
        out["rp_ids2"] = s(rp.Ids)
        out["rp_loc2"] = [int(i) for i in rp.Location.Ids]
    except:
        pass
    try:
        out["pm_state2"] = s(pm.ObjectState)
    except:
        pass
    flush()

try:
    okrp = (rp is not None) and (s(rp.ObjectState) == "FullyDefined")
    okpm = (pm is not None) and (s(pm.ObjectState) == "FullyDefined")
    out["okrp"] = okrp
    out["okpm"] = okpm
    if okrp and okpm:
        ExtAPI.DataModel.Project.Save()
        out["save"] = "OK"
except Exception as e:
    out["save"] = "ERR:%r" % e
flush()

cs_ud = []
for cs in Model.CoordinateSystems.Children:
    try:
        st = s(cs.ObjectState)
    except:
        continue
    if st == "UnderDefined":
        r = {"name": s(cs.Name)}
        for attr in ["OriginDefineBy", "CoordinateSystemType"]:
            try:
                r[attr] = s(getattr(cs, attr))
            except:
                pass
        try:
            r["suppressed"] = s(cs.Suppressed)
        except:
            pass
        for attr in ["Location", "Source"]:
            try:
                v = getattr(cs, attr)
                try:
                    r[attr] = [int(i) for i in v.Ids]
                except:
                    r[attr] = s(v)
            except:
                pass
        try:
            r["objid"] = s(getattr(cs, "ObjectId", "?"))
        except:
            pass
        cs_ud.append(r)
out["cs_ud"] = cs_ud
flush()

print("FIX RP PM DONE")
