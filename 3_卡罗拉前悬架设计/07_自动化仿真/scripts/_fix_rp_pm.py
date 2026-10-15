# -*- coding: utf-8 -*-
r"""client: python _fix_rp_pm.py <port> <out.json>"""
import io, json, sys
from ansys.mechanical.core import connect_to_mechanical

port = int(sys.argv[1])
outp = sys.argv[2]
face = int(sys.argv[3]) if len(sys.argv) > 3 else 5396

mech = connect_to_mechanical(port=port, transport_mode="insecure", cleanup_on_exit=False)
content = io.open(r"C:\Users\dth15\Desktop\ANSYS\automation\scripts\_fix_rp_pm_server.py", encoding="utf-8").read()
content = content.replace("__FACE__", str(face)).replace("__OUT__", outp)
r = mech.run_python_script(content)
print("RET:", str(r)[:200])
d = json.load(io.open(outp, encoding="utf-8"))
print("step1:", json.dumps(d.get("step1", {}), ensure_ascii=False, indent=1))
for k in ["gen", "gen_s", "rp_state2", "rp_ids2", "rp_loc2", "pm_state2", "okrp", "okpm", "save"]:
    if k in d:
        print("%s: %s" % (k, d[k]))
print("cs_ud:")
for r in d.get("cs_ud", []):
    print("   ", json.dumps(r, ensure_ascii=False))
