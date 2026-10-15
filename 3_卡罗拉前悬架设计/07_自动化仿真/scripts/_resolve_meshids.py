# -*- coding: utf-8 -*-
r"""client: python _resolve_meshids.py <port> <out.json>"""
import io, json, sys
from ansys.mechanical.core import connect_to_mechanical

port = int(sys.argv[1])
outp = sys.argv[2]
mech = connect_to_mechanical(port=port, transport_mode="insecure", cleanup_on_exit=False)
content = io.open(r"C:\Users\dth15\Desktop\ANSYS\automation\scripts\_resolve_meshids_server.py", encoding="utf-8").read()
content = content.replace("__OUT__", outp)
r = mech.run_python_script(content)
print("RET:", str(r)[:200])
d = json.load(io.open(outp, encoding="utf-8"))
print("bodies:", d.get("nbody"), "| faces:", d.get("nface"))
for st in d.get("sets", []):
    print("== %s [%s] %s" % (st.get("name"), st.get("type"), st.get("state")))
    for e in st.get("resolved", []):
        if e.get("kind") == "body":
            print("   id=%s BODY part=%s name=%s vol=%s" % (e.get("id"), e.get("part"), e.get("name"), e.get("vol")))
        elif e.get("kind") == "face":
            print("   id=%s FACE of-body-id=%s area=%s c=%s" % (e.get("id"), e.get("body"), e.get("area"), e.get("c")))
        else:
            print("   id=%s ???" % e.get("id"))
