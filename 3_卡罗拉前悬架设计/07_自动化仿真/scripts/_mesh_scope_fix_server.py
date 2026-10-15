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

name2id = {}

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
                key = c.Name.encode("utf-8").encode("hex")
                name2id[key] = int(c.GetGeoBody().Id)
            except:
                pass
        else:
            walk(c)

walk(Model.Geometry)

mesh_children = list(Model.Mesh.Children)
steps = []

for i in range(min(len(mesh_children), len(PLAN))):
    target = mesh_children[i]
    hexnames = PLAN[i]
    ids = []
    miss = []
    for h in hexnames:
        if h in name2id:
            ids.append(name2id[h])
        else:
            miss.append(hx(h))
    rec = {"idx": i, "want": len(hexnames), "got": len(ids), "miss": miss}
    if ids:
        try:
            sel = ExtAPI.SelectionManager.CreateSelectionInfo(SelectionTypeEnum.GeometryEntities)
            sel.Ids = ids
            target.Location = sel
            rec["set_loc"] = "OK"
        except Exception as e:
            rec["set_loc"] = "ERR:%r" % e
    try:
        back = [int(x) for x in target.Location.Ids]
        rec["back_n"] = len(back)
    except:
        rec["back_n"] = -1
    try:
        rec["state"] = s(target.ObjectState)
    except:
        rec["state"] = "?"
    steps.append(rec)

out["steps"] = steps
try:
    out["mesh_state_after_set"] = s(Model.Mesh.ObjectState)
except:
    pass

all_ok = all(rec.get("set_loc") == "OK" and rec.get("back_n") == rec.get("want") for rec in steps)
out["all_ok"] = all_ok

def flush():
    with io.open(OUT, "w", encoding="utf-8") as f:
        f.write(json.dumps(out, ensure_ascii=False, indent=1))

flush()

if all_ok:
    try:
        from Ansys.Core.Units import Quantity
        Model.Mesh.ElementSize = Quantity(10.0, "mm")
        out["elem_size_set"] = "OK"
    except Exception as e:
        out["elem_size_set"] = "ERR:%r" % e
    flush()
    import time
    t0 = time.time()
    try:
        Model.Mesh.GenerateMesh()
        out["gen"] = "OK"
    except Exception as e:
        out["gen"] = "ERR:%r" % e
    out["gen_s"] = round(time.time() - t0, 1)
    try:
        out["nodes"] = s(Model.Mesh.Nodes)
        out["elements"] = s(Model.Mesh.Elements)
        out["mesh_state"] = s(Model.Mesh.ObjectState)
    except:
        pass
    flush()
    try:
        nv = float(s(Model.Mesh.Nodes))
    except:
        nv = 0.0
    if out.get("gen") == "OK" and nv > 0:
        try:
            ExtAPI.DataModel.Project.Save()
            out["save"] = "OK"
        except Exception as e:
            out["save"] = "ERR:%r" % e
        flush()

print("MESH SCOPE FIX DONE")
