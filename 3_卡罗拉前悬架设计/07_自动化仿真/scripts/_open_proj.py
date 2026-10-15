# -*- coding: utf-8 -*-
r"""通用开项目客户端：python _open_proj.py <port> <mechdb路径>"""
import io, json, sys
from ansys.mechanical.core import connect_to_mechanical

port = int(sys.argv[1])
path = sys.argv[2]
mech = connect_to_mechanical(port=port, transport_mode="insecure", cleanup_on_exit=False)
content = io.open(r"C:\Users\dth15\Desktop\ANSYS\automation\scripts\_open_proj_server.py", encoding="utf-8").read()
content = content.replace("__PATH__", path)
r = mech.run_python_script(content)
print("run:", str(r)[:60])
d = json.load(io.open(r"C:\Users\dth15\Desktop\ANSYS\automation\logs\open_tmp.json", encoding="utf-8"))
print("open:", d.get("open"))
