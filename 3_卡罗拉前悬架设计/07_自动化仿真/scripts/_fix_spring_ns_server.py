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

def hx(h):
    return h.decode("hex").decode("utf-8")

out = {}

def find_body(hexname):
    hits = []

    def walk(o):
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
                try:
                    if c.Name.encode("utf-8").encode("hex") == hexname:
                        hits.append(c)
                except:
                    pass
                walk(c)
            else:
                walk(c)

    walk(Model.Geometry)
    return hits

spring = None
for g in Model.Connections.Children:
    try:
        if "Spring" in s(g.GetType()):
            spring = g
            break
    except:
        pass

res = {}
if spring is not None:
    for side, hexn in [("ReferenceBody", PLAN["ref_hex"]), ("MobileBody", PLAN["mob_hex"])]:
        hits = find_body(hexn)
        r = {"hits": len(hits)}
        if hits:
            try:
                setattr(spring, side, hits[0])
                r["set"] = "OK"
            except Exception as e:
                r["set"] = "ERR:%r" % e
                try:
                    setattr(spring, side, hits[0].InternalObject)
                    r["set2"] = "OK"
                except Exception as e2:
                    r["set2"] = "ERR:%r" % e2
            try:
                r["back"] = s(getattr(spring, side))
            except:
                pass
        res[side] = r
    try:
        res["state"] = s(spring.ObjectState)
    except:
        pass
out["spring"] = res

ns_res = []
for nhex, ids in PLAN["ns"]:
    ns = None
    for cand in Model.NamedSelections.Children:
        try:
            if cand.Name.encode("utf-8").encode("hex") == nhex:
                ns = cand
                break
        except:
            pass
    r = {"name": hx(nhex), "ids": ids}
    if ns is None:
        r["err"] = "NOT FOUND"
        ns_res.append(r)
        continue
    try:
        sel = ExtAPI.SelectionManager.CreateSelectionInfo(SelectionTypeEnum.GeometryEntities)
        sel.Ids = ids
        ns.Location = sel
        r["set"] = "OK"
    except Exception as e:
        r["set"] = "ERR:%r" % e
    try:
        r["back_ids"] = [int(i) for i in ns.Location.Ids]
    except:
        r["back_ids"] = None
    try:
        r["state"] = s(ns.ObjectState)
    except:
        pass
    try:
        r["seltype"] = s(ns.SelectionType)
    except:
        pass
    ns_res.append(r)
out["ns"] = ns_res

try:
    out["conn_state"] = s(Model.Connections.ObjectState)
except:
    pass

with io.open(OUT, "w", encoding="utf-8") as f:
    f.write(json.dumps(out, ensure_ascii=False, indent=1))

if all(r.get("set") == "OK" or r.get("set2") == "OK" for r in [res.get("ReferenceBody", {}), res.get("MobileBody", {})]) and all(r.get("set") == "OK" for r in ns_res):
    try:
        ExtAPI.DataModel.Project.Save()
        out["save"] = "OK"
    except Exception as e:
        out["save"] = "ERR:%r" % e
    with io.open(OUT, "w", encoding="utf-8") as f:
        f.write(json.dumps(out, ensure_ascii=False, indent=1))

print("FIX SPRING NS DONE")
