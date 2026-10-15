# -*- coding: utf-8 -*-
r"""client: python _probe_state_tree.py <port> <out.json>"""
import io, json, sys
from ansys.mechanical.core import connect_to_mechanical

port = int(sys.argv[1])
outp = sys.argv[2]
mech = connect_to_mechanical(port=port, transport_mode="insecure", cleanup_on_exit=False)
content = io.open(r"C:\Users\dth15\Desktop\ANSYS\automation\scripts\_probe_state_tree_server.py", encoding="utf-8").read()
content = content.replace("__OUT__", outp)
r = mech.run_python_script(content)
print("RET:", str(r)[:200])
d = json.load(io.open(outp, encoding="utf-8"))
print("=== mesh sets ===")
for r in d.get("mesh_sets", []):
    n = r.get("name")
    print("name: %r" % n, "| type:", r.get("type"), "| state:", r.get("state"))
    print("   size:", r.get("ElementSize"), "| behavior:", r.get("Behavior"), "| method:", r.get("Method"), "| sel_attr:", r.get("sel_attr"))
    ids = r.get("ids")
    print("   ids:", (str(ids)[:160] + ("...(%d)" % len(ids) if ids and len(ids) > 20 else "")) if ids is not None else None)
print("=== connections ===")
for l in d.get("connections", []):
    print(l)
print("=== coordsys ===")
for l in d.get("coordsys", []):
    print(l)
print("=== remote points ===")
for l in d.get("remote_points", []):
    print(l)
print("=== vt top ===", d.get("vt_top_state"), d.get("vt_top_count"), d.get("vt_top_child_states"), d.get("vt_top_err"))
