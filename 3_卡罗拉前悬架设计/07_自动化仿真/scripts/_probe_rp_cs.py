# -*- coding: utf-8 -*-
r"""client: python _probe_rp_cs.py <port> <out.json>"""
import io, json, sys
from ansys.mechanical.core import connect_to_mechanical

port = int(sys.argv[1])
outp = sys.argv[2]
mech = connect_to_mechanical(port=port, transport_mode="insecure", cleanup_on_exit=False)
content = io.open(r"C:\Users\dth15\Desktop\ANSYS\automation\scripts\_probe_rp_cs_server.py", encoding="utf-8").read()
content = content.replace("__OUT__", outp)
r = mech.run_python_script(content)
print("RET:", str(r)[:200])
d = json.load(io.open(outp, encoding="utf-8"))
print("=== remote points stat ===", d.get("rp_stat"))
for r in d.get("rp_bad", []):
    print("  BAD RP:", json.dumps(r, ensure_ascii=False))
print("=== point masses ===")
for r in d.get("point_masses", []):
    print("  PM:", json.dumps(r, ensure_ascii=False))
print("=== coord systems stat ===", d.get("cs_stat"))
for r in d.get("cs_all", []):
    if r.get("state") != "FullyDefined":
        print("  CS(non-FD):", json.dumps(r, ensure_ascii=False))
