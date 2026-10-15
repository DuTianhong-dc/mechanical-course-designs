# -*- coding: utf-8 -*-
r"""client: python _spring_facefix.py <port> <out.json>"""
import io, json, sys
from ansys.mechanical.core import connect_to_mechanical

port = int(sys.argv[1])
outp = sys.argv[2]

plan = {
    "mobile_face": 5343,   # 上弹簧座
    "ref_face": 2659,      # 减振器壳_下弹簧座
}
template = io.open(r"C:\Users\dth15\Desktop\ANSYS\automation\scripts\_spring_facefix_server.py", encoding="utf-8").read()
content = template.replace("__PLAN__", json.dumps(plan)).replace("__OUT__", outp)

mech = connect_to_mechanical(port=port, transport_mode="insecure", cleanup_on_exit=False)
r = mech.run_python_script(content)
print("RET:", str(r)[:200])
res = json.load(io.open(outp, encoding="utf-8"))
for k, v in res.items():
    print("%s: %s" % (k, v))
