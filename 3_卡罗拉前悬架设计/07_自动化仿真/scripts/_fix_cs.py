# -*- coding: utf-8 -*-
r"""client: python _fix_cs.py <port> <out.json>"""
import io, json, sys
from ansys.mechanical.core import connect_to_mechanical

port = int(sys.argv[1])
outp = sys.argv[2]

plan = {"cs": [
    {"objid": "990", "origin_ids": [5472], "axis_ids": [5472]},
    {"objid": "1025", "origin_ids": [5222]},
    {"objid": "1033", "origin_ids": [5222]},
]}

mech = connect_to_mechanical(port=port, transport_mode="insecure", cleanup_on_exit=False)
content = io.open(r"C:\Users\dth15\Desktop\ANSYS\automation\scripts\_fix_cs_server.py", encoding="utf-8").read()
content = content.replace("__PLAN__", json.dumps(plan)).replace("__OUT__", outp)
r = mech.run_python_script(content)
print("RET:", str(r)[:200])
d = json.load(io.open(outp, encoding="utf-8"))
for r in d.get("res", []):
    print("cs %s: origin_set=%s axis_set=%s origin_back=%s state=%s err=%s" % (
        r.get("objid"), r.get("origin_set"), r.get("axis_set"), r.get("origin_back"), r.get("state"), r.get("err")))
print("cs_stats:", d.get("cs_stats"))
print("allok:", d.get("allok"), "| save:", d.get("save"))
