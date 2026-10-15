import sys
from ansys.mechanical.core import launch_mechanical
mech = launch_mechanical(batch=True, port=10505, start_instance=True, transport_mode="insecure", cleanup_on_exit=False, start_timeout=300)
print("BATCH 10505 READY")
sys.stdout.flush()
sys.exit(0)
