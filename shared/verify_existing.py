import subprocess
import sys
import os

files = [
    "shared/translation.py",
    "shared/knowledge_gap.py", 
    "shared/plugin_system.py",
    "shared/analytics.py"
]
for f in files:
    fpath = os.path.join("D:/Projects/cuckoo-echo/cuckoo-echo", f)
    result = subprocess.run([sys.executable, "-m", "py_compile", fpath], capture_output=True, text=True)
    if result.returncode != 0:
        print(f"FAILED: {f}")
        print(result.stderr)
    else:
        print(f"OK: {f}")