# -*- coding: utf-8 -*-
r"""client: python _probe_depth.py <port> <out.json>"""
import io, json, sys
from ansys.mechanical.core import connect_to_mechanical

port = int(sys.argv[1])
outp = sys.argv[2]
mech = connect_to_mechanical(port=port, transport_mode="insecure", cleanup_on_exit=False)
content = io.open(r"C:\Users\dth15\Desktop\ANSYS\automation\scripts\_probe_depth_server.py", encoding="utf-8").read()
content = content.replace("__OUT__", outp)
r = mech.run_python_script(content)
print("RET:", str(r)[:200])
d = json.load(io.open(outp, encoding="utf-8"))
print("rp1023:", json.dumps(d.get("rp1023"), ensure_ascii=False))
print("rp70:", json.dumps(d.get("rp70"), ensure_ascii=False))
for r in d.get("point_masses", []):
    print("PM:", json.dumps(r, ensure_ascii=False))
print("=== UD coordinate systems ===")
for r in d.get("cs_ud", []):
    print("----")
    for k, v in r.items():
        print("   %s = %s" % (k, v))
