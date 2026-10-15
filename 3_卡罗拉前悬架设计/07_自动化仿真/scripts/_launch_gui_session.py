# -*- coding: utf-8 -*-
r"""启动可见 GUI 会话（port 10504）——用于打开 suspension_geoswap_repaired.mechdb 人工提交
注意：结尾 sys.exit(0)（绝不用 os._exit）"""
import json
import sys

from ansys.mechanical.core import launch_mechanical

PORT = 10504

mech = launch_mechanical(
    batch=False,                # GUI 可见
    port=PORT,
    start_instance=True,
    transport_mode="insecure",
    cleanup_on_exit=False,
    start_timeout=300,
    allow_input=False,
)

info = {
    "port": PORT,
    "usage": "可见会话——打开 suspension_geoswap_repaired.mechdb 人工提交/生成",
    "note": "由 _launch_gui_session.py 启动",
}
with open(
    r"C:\Users\dth15\Desktop\ANSYS\automation\logs\session_info_gui.json",
    "w",
    encoding="utf-8",
) as f:
    json.dump(info, f, ensure_ascii=False, indent=2)

print("GUI SESSION READY: port", PORT)
sys.stdout.flush()
sys.exit(0)
