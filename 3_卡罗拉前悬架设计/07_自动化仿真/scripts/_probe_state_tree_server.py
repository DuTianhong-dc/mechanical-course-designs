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

sets = []
m = Model.Mesh
for c in m.Children:
    r = {"name": s(c.Name), "type": s(c.GetType()).split(".")[-1]}
    try:
        r["state"] = s(c.ObjectState)
    except:
        pass
    for attr in ["Suppressed", "ElementSize", "Behavior", "Method", "GrowthRate", "Resolution"]:
        try:
            r[attr] = s(getattr(c, attr))
        except:
            pass
    ids = None
    for attr in ["Location", "Scoping"]:
        try:
            v = getattr(c, attr)
            try:
                ids = [int(i) for i in v.Ids]
                r["sel_attr"] = attr
                break
            except:
                try:
                    ids = [int(i) for i in v.Ids]
                    r["sel_attr"] = attr
                    break
                except:
                    pass
        except:
            pass
    r["ids"] = ids
    sets.append(r)
out["mesh_sets"] = sets

cl = []
try:
    for g in Model.Connections.Children:
        try:
            t = s(g.GetType()).split(".")[-1]
        except:
            t = "?"
        try:
            st = s(g.ObjectState)
        except:
            st = "?"
        cl.append("G %s [%s] %s" % (s(g.Name), t, st))
        try:
            for j in g.Children:
                try:
                    jt = s(j.GetType()).split(".")[-1]
                except:
                    jt = "?"
                try:
                    jst = s(j.ObjectState)
                except:
                    jst = "?"
                cl.append("  - %s [%s] %s" % (s(j.Name), jt, jst))
        except:
            pass
except Exception as e:
    out["conn_err"] = repr(e)
out["connections"] = cl

csl = []
try:
    for g in Model.CoordinateSystems.Children:
        try:
            st = s(g.ObjectState)
        except:
            st = "?"
        csl.append("%s [%s] %s" % (s(g.Name), s(g.GetType()).split(".")[-1], st))
except Exception as e:
    out["cs_err"] = repr(e)
out["coordsys"] = csl

rpl = []
try:
    for g in Model.RemotePoints.Children:
        try:
            st = s(g.ObjectState)
        except:
            st = "?"
        rpl.append("%s [%s] %s" % (s(g.Name), s(g.GetType()).split(".")[-1], st))
except Exception as e:
    out["rp_err"] = repr(e)
out["remote_points"] = rpl

try:
    vt = None
    for c in Model.Children:
        try:
            if "VirtualTopology" in s(c.GetType()):
                vt = c
                break
        except:
            pass
    if vt is None:
        out["vt_top"] = "NOT FOUND by type"
    else:
        out["vt_top_state"] = s(vt.ObjectState)
        kids = list(vt.Children)
        out["vt_top_count"] = len(kids)
        vst = {}
        for k in kids:
            try:
                st = s(k.ObjectState)
            except:
                st = "?"
            vst[st] = vst.get(st, 0) + 1
        out["vt_top_child_states"] = vst
except Exception as e:
    out["vt_top_err"] = repr(e)

with io.open(OUT, "w", encoding="utf-8") as f:
    f.write(json.dumps(out, ensure_ascii=False, indent=1))
print("PROBE STATE TREE DONE")
