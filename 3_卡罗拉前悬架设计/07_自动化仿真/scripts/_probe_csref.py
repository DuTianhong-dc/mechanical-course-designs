# -*- coding: utf-8 -*-
r"""client: python _probe_csref.py <port> <out.json>"""
import io, json, sys
from ansys.mechanical.core import connect_to_mechanical

port = int(sys.argv[1])
outp = sys.argv[2]
mech = connect_to_mechanical(port=port, transport_mode="insecure", cleanup_on_exit=False)
content = io.open(r"C:\Users\dth15\Desktop\ANSYS\automation\scripts\_probe_csref_server.py", encoding="utf-8").read()
content = content.replace("__OUT__", outp)
r = mech.run_python_script(content)
print("RET:", str(r)[:200])
d = json.load(io.open(outp, encoding="utf-8"))
print("=== CS list (name | state | objid) ===")
for r in d.get("cs", []):
    print("  %s | %s | %s | sup=%s" % (r.get("name"), r.get("state"), r.get("objid"), r.get("sup")))
print("=== joint CS refs ===")
for r in d.get("joint_cs_refs", []):
    if r.get("MobileCoordinateSystem") or r.get("ReferenceCoordinateSystem"):
        print("  ", json.dumps(r, ensure_ascii=False))
print("=== UD CS full ===")
for r in d.get("cs_ud_full", []):
    print("----")
    for k, v in r.items():
        print("   %s = %s" % (k, v))
