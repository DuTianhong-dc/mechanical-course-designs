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

def cnt(objs, name):
    st = {}
    for o in objs:
        try:
            k = s(o.ObjectState)
        except:
            k = "?"
        st[k] = st.get(k, 0) + 1
    out[name] = st

allc = []
for g in Model.Connections.Children:
    try:
        kids = list(g.Children)
    except:
        kids = []
    for c in (kids if kids else [g]):
        allc.append(c)
cnt(allc, "connections")

cnt(list(Model.RemotePoints.Children), "remote_points")
cnt(list(Model.CoordinateSystems.Children), "coordinate_systems")
cnt(list(Model.NamedSelections.Children), "named_selections")
cnt(list(Model.Mesh.Children), "mesh_children")

bb = []

def walk(o, d=0):
    if d > 6:
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
        if cat == "Body":
            bb.append(c)
        else:
            walk(c, d + 1)

walk(Model.Geometry)
cnt(bb, "bodies")

out["mesh_state"] = s(Model.Mesh.ObjectState)
out["mesh_nodes"] = s(Model.Mesh.Nodes)
out["mesh_elements"] = s(Model.Mesh.Elements)
out["geom_state"] = s(Model.Geometry.ObjectState)

try:
    out["conn_state"] = s(Model.Connections.ObjectState)
except:
    pass
try:
    out["cs_state"] = s(Model.CoordinateSystems.ObjectState)
except:
    pass
try:
    out["rp_state"] = s(Model.RemotePoints.ObjectState)
except:
    pass
try:
    out["ns_state"] = s(Model.NamedSelections.ObjectState)
except:
    pass

beh = {}
for b in bb:
    try:
        k = s(b.StiffnessBehavior)
    except:
        k = "?"
    beh[k] = beh.get(k, 0) + 1
out["beh"] = beh

# list any remaining non-FD connections
bad_conn = []
for c in allc:
    try:
        if s(c.ObjectState) not in ("FullyDefined",):
            bad_conn.append(s(c.Name))
    except:
        pass
out["bad_conn"] = bad_conn[:20]

with io.open(OUT, "w", encoding="utf-8") as f:
    f.write(json.dumps(out, ensure_ascii=False, indent=1))
print("FINAL CHECK DONE")
