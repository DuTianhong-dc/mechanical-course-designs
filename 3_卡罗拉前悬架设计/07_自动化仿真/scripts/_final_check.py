# -*- coding: utf-8 -*-
r"""client: python _final_check.py <port> <out.json>"""
import io, json, sys
from ansys.mechanical.core import connect_to_mechanical

port = int(sys.argv[1])
outp = sys.argv[2]
mech = connect_to_mechanical(port=port, transport_mode="insecure", cleanup_on_exit=False)
content = io.open(r"C:\Users\dth15\Desktop\ANSYS\automation\scripts\_final_check_server.py", encoding="utf-8").read()
content = content.replace("__OUT__", outp)
r = mech.run_python_script(content)
print("RET:", str(r)[:200])
d = json.load(io.open(outp, encoding="utf-8"))
for k, v in d.items():
    if k == "bad_conn":
        print("bad_conn:", v)
    else:
        print("%s: %s" % (k, v))
