# -*- coding: utf-8 -*-
r"""client: python _export9.py <port> <out.json>"""
import io, json, sys
from ansys.mechanical.core import connect_to_mechanical

port = int(sys.argv[1])
outp = sys.argv[2]
mech = connect_to_mechanical(port=port, transport_mode="insecure", cleanup_on_exit=False)
content = io.open(r"C:\Users\dth15\Desktop\ANSYS\automation\scripts\_export9_server.py", encoding="utf-8").read()
content = content.replace("__OUT__", outp)
r = mech.run_python_script(content)
print("RET:", str(r)[:200])
try:
    d = json.load(io.open(outp, encoding="utf-8"))
    print("save:", d.get("save"))
    print("solve:", d.get("solve"), "| solve_s:", d.get("solve_s"))
    print("dfs_found:", d.get("dfs_found"), "| dfs_size:", d.get("dfs_size"))
    print("analysis children:")
    for h, st in d.get("analysis_children", []):
        print("   %s | %s" % (h, st))
except Exception as e:
    print("read err:", e)
