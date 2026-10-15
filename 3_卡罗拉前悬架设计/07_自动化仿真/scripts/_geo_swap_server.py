import io, json, time
OUT = r"C:\Users\dth15\Desktop\ANSYS\automation\logs\geo_swap_result.json"
NEW_XT = r"C:\Users\dth15\Desktop\ANSYS\automation\inbox\麦弗逊悬架_run04.x_t"

def s(x):
    try:
        return str(x)
    except Exception:
        try:
            return repr(x)
        except Exception:
            return "?"

out = {}

def flush():
    with io.open(OUT, "w", encoding="utf-8") as f:
        f.write(json.dumps(out, ensure_ascii=False))

# ---------- BEFORE snapshot ----------
def snapshot(tag):
    r = {}
    try:
        parts = 0
        bodies = 0
        for p in Model.Geometry.Children:
            parts += 1
            try:
                bodies += len(p.Children)
            except Exception:
                pass
        r["n_parts"] = parts
        r["n_bodies"] = bodies
    except Exception as e:
        r["geom_err"] = repr(e)
    try:
        r["geom_state"] = s(Model.Geometry.ObjectState)
    except Exception as e:
        r["geom_state"] = repr(e)
    try:
        js = []
        for g in Model.Connections.Children:
            for j in g.Children:
                rec = [s(j.Name)[:50]]
                for a in ["Type", "Suppressed", "ObjectState"]:
                    try:
                        rec.append(s(getattr(j, a)))
                    except Exception:
                        rec.append("ERR")
                js.append(rec)
        r["joints"] = js
        r["n_joints"] = len(js)
    except Exception as e:
        r["joints_err"] = repr(e)
    try:
        ns = []
        for x in (Model.NamedSelections.Children if Model.NamedSelections else []):
            rec = [s(x.Name)[:40]]
            try:
                rec.append(s(x.ObjectState))
            except Exception:
                rec.append("ERR")
            ns.append(rec)
        r["named_selections"] = ns
    except Exception as e:
        r["ns_err"] = repr(e)
    try:
        ac = []
        for a in Model.Analyses:
            for c in a.Children:
                rec = [s(c.DataModelObjectCategory), s(c.Name)[:40]]
                try:
                    rec.append(s(c.ObjectState))
                except Exception:
                    rec.append("ERR")
                ac.append(rec)
        r["analysis_children"] = ac
    except Exception as e:
        r["analysis_err"] = repr(e)
    out[tag] = r
    flush()

snapshot("before")

# ---------- source info ----------
try:
    src = Model.Geometry.Source
    out["source_before"] = s(src)[:300]
except Exception as e:
    out["source_before"] = "ERR:%r" % e
flush()

# ---------- SWAP ----------
t0 = time.time()
try:
    Model.Geometry.Source = NEW_XT
    out["set_source"] = "OK"
except Exception as e:
    out["set_source"] = "ERR:%r" % e
flush()

try:
    Model.Geometry.UpdateGeometryFromSource()
    out["update"] = "OK"
except Exception as e:
    out["update"] = "ERR:%r" % e
out["update_elapsed_s"] = round(time.time() - t0, 1)
flush()

# ---------- AFTER snapshot ----------
snapshot("after")

# part names after (to compare)
try:
    pn = []
    for p in Model.Geometry.Children:
        nb = 0
        try:
            nb = len(p.Children)
        except Exception:
            pass
        pn.append([s(p.Name)[:36], nb])
    out["part_names_after"] = pn
except Exception as e:
    out["part_names_err"] = repr(e)
flush()

out["stage"] = "GEO SWAP DONE"
flush()
print("GEO SWAP DONE")
