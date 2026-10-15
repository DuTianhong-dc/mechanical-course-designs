# -*- coding: utf-8 -*-
r"""client: python _export8.py <port> <out.json>"""
import io, json, sys
from ansys.mechanical.core import connect_to_mechanical

port = int(sys.argv[1])
outp = sys.argv[2]
mech = connect_to_mechanical(port=port, transport_mode="insecure", cleanup_on_exit=False)
content = io.open(r"C:\Users\dth15\Desktop\ANSYS\automation\scripts\_export8_server.py", encoding="utf-8").read()
content = content.replace("__OUT__", outp)
r = mech.run_python_script(content)
print("RET:", str(r)[:200])
try:
    d = json.load(io.open(outp, encoding="utf-8"))
    print("pre:", d.get("pre"))
    print("solve:", d.get("solve"), "| solve_s:", d.get("solve_s"))
    print("dfs_found:", d.get("dfs_found"), "| dfs_size:", d.get("dfs_size"))
    for f in d.get("files", []):
        print("   ", f)
except Exception as e:
    print("read err:", e)
