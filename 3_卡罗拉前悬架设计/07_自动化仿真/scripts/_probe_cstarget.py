# -*- coding: utf-8 -*-
r"""client: python _probe_cstarget.py <port> <out.json>"""
import io, json, sys
from ansys.mechanical.core import connect_to_mechanical

port = int(sys.argv[1])
outp = sys.argv[2]
mech = connect_to_mechanical(port=port, transport_mode="insecure", cleanup_on_exit=False)
content = io.open(r"C:\Users\dth15\Desktop\ANSYS\automation\scripts\_probe_cstarget_server.py", encoding="utf-8").read()
content = content.replace("__OUT__", outp)
r = mech.run_python_script(content)
print("RET:", str(r)[:200])
d = json.load(io.open(outp, encoding="utf-8"))
print("spring_cs:", json.dumps(d.get("spring_cs"), ensure_ascii=False))
print("rp_cs:", json.dumps(d.get("rp_cs"), ensure_ascii=False))
print("pm_cs_props:", json.dumps(d.get("pm_cs_props"), ensure_ascii=False, indent=1))
print("=== cs_detail (990/1025/1033) ===")
for r in d.get("cs_detail", []):
    print("---- objid", r.get("ObjectId"), r.get("Name"), "state:", r.get("ObjectState"))
    for k in ["Origin", "XAxis", "YAxis", "OriginDefineBy", "PrimaryAxisDefineBy", "PrimaryAxis", "OriginLocation_Ids", "PrimaryAxisLocation_Ids", "Suppressed", "ScopingMode"]:
        if k in r:
            print("    %s = %s" % (k, r[k]))
