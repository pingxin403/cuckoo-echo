import subprocess
import sys
import os

files = ["shared/rbac.py", "shared/customer_success.py", "shared/api_marketplace.py"]
for f in files:
    fpath = os.path.join("D:/Projects/cuckoo-echo/cuckoo-echo", f)
    result = subprocess.run([sys.executable, "-m", "py_compile", fpath], capture_output=True, text=True)
    if result.returncode != 0:
        print(f"FAILED: {f}")
        print(result.stderr)
    else:
        print(f"OK: {f}")