import io, json

OUT = r"__OUT__"
PLAN = __PLAN__

def s(x):
    try:
        return str(x)
    except:
        try:
            return repr(x)
        except:
            return "?"

out = {}

cs_map = {}
for cs in Model.CoordinateSystems.Children:
    try:
        cs_map[s(getattr(cs, "ObjectId", "?"))] = cs
    except:
        pass

def flush():
    with io.open(OUT, "w", encoding="utf-8") as f:
        f.write(json.dumps(out, ensure_ascii=False, indent=1))

res = []
for item in PLAN["cs"]:
    oid = str(item["objid"])
    cs = cs_map.get(oid)
    r = {"objid": oid}
    if cs is None:
        r["err"] = "NOT FOUND"
        res.append(r)
        continue
    try:
        sel = ExtAPI.SelectionManager.CreateSelectionInfo(SelectionTypeEnum.GeometryEntities)
        sel.Ids = list(item["origin_ids"])
        cs.OriginLocation = sel
        r["origin_set"] = "OK"
    except Exception as e:
        r["origin_set"] = "ERR:%r" % e
    if item.get("axis_ids"):
        try:
            sel = ExtAPI.SelectionManager.CreateSelectionInfo(SelectionTypeEnum.GeometryEntities)
            sel.Ids = list(item["axis_ids"])
            cs.PrimaryAxisLocation = sel
            r["axis_set"] = "OK"
        except Exception as e:
            r["axis_set"] = "ERR:%r" % e
    try:
        r["origin_back"] = [int(i) for i in cs.OriginLocation.Ids]
    except:
        pass
    try:
        r["state"] = s(cs.ObjectState)
    except:
        pass
    res.append(r)

out["res"] = res
flush()

try:
    st = {}
    for cs in Model.CoordinateSystems.Children:
        st2 = s(cs.ObjectState)
        st[st2] = st.get(st2, 0) + 1
    out["cs_stats"] = st
except:
    pass
flush()

allok = all(r.get("state") == "FullyDefined" for r in res)
out["allok"] = allok
if allok:
    try:
        ExtAPI.DataModel.Project.Save()
        out["save"] = "OK"
    except Exception as e:
        out["save"] = "ERR:%r" % e
    flush()

print("FIX CS DONE")
