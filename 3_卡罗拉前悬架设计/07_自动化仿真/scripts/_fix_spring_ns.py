# -*- coding: utf-8 -*-
r"""client: python _fix_spring_ns.py <port> <out.json>"""
import io, json, sys
from ansys.mechanical.core import connect_to_mechanical

port = int(sys.argv[1])
outp = sys.argv[2]

ref_hex = "减振器壳_下弹簧座".encode("utf-8").hex()
mob_hex = "上弹簧座".encode("utf-8").hex()

ns_plan = [
    ("顶胶螺栓孔内圆柱面", [5257, 5259, 5260]),
    ("衬套铆接内圆柱面", [5522, 5531]),
    ("横拉杆外端球头面", [6291]),
]
plan = {
    "ref_hex": ref_hex,
    "mob_hex": mob_hex,
    "ns": [[n.encode("utf-8").hex(), ids] for n, ids in ns_plan],
}

template = io.open(r"C:\Users\dth15\Desktop\ANSYS\automation\scripts\_fix_spring_ns_server.py", encoding="utf-8").read()
content = template.replace("__PLAN__", json.dumps(plan)).replace("__OUT__", outp)

mech = connect_to_mechanical(port=port, transport_mode="insecure", cleanup_on_exit=False)
r = mech.run_python_script(content)
print("RET:", str(r)[:200])

res = json.load(io.open(outp, encoding="utf-8"))
print("spring:", json.dumps(res.get("spring", {}), ensure_ascii=False, indent=1))
print("conn_state:", res.get("conn_state"))
for r in res.get("ns", []):
    print("NS %s: set=%s back_ids=%s state=%s seltype=%s err=%s" % (
        r.get("name"), r.get("set"), r.get("back_ids"), r.get("state"), r.get("seltype"), r.get("err")))
print("save:", res.get("save"))
