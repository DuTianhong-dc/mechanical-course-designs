# -*- coding: utf-8 -*-
r"""client: python _mesh_scope_fix.py <port> <gold_json> <out_json>"""
import io, json, ast, sys
from ansys.mechanical.core import connect_to_mechanical

port = int(sys.argv[1])
goldp = sys.argv[2]
outp = sys.argv[3]

d = json.load(io.open(goldp, encoding="utf-8"))
plan = []
for st in d["sets"]:
    names = []
    for e in st["resolved"]:
        nm = e["name"]
        if isinstance(nm, str) and (nm.startswith("u'") or nm.startswith('u"')):
            nm = ast.literal_eval(nm)
        names.append(nm.encode("utf-8").hex())
    plan.append(names)
print("plan sizes:", [len(x) for x in plan])
assert [len(x) for x in plan] == [1, 1, 9, 15, 3], "unexpected plan sizes"

template = io.open(r"C:\Users\dth15\Desktop\ANSYS\automation\scripts\_mesh_scope_fix_server.py", encoding="utf-8").read()
content = template.replace("__PLAN__", json.dumps(plan)).replace("__OUT__", outp)

mech = connect_to_mechanical(port=port, transport_mode="insecure", cleanup_on_exit=False)
r = mech.run_python_script(content)
print("RET:", str(r)[:300])

res = json.load(io.open(outp, encoding="utf-8"))
for rec in res.get("steps", []):
    print("set%d want=%s got=%s miss=%s set_loc=%s back_n=%s state=%s" % (
        rec.get("idx"), rec.get("want"), rec.get("got"),
        rec.get("miss"), rec.get("set_loc"), rec.get("back_n"), rec.get("state")))
print("mesh_state_after_set:", res.get("mesh_state_after_set"))
print("all_ok:", res.get("all_ok"))
print("elem_size_set:", res.get("elem_size_set"))
print("gen:", res.get("gen"), "gen_s:", res.get("gen_s"))
print("nodes:", res.get("nodes"), "elements:", res.get("elements"), "mesh_state:", res.get("mesh_state"))
print("save:", res.get("save"))
