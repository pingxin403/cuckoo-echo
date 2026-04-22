import subprocess
import sys

result = subprocess.run(
    [sys.executable, "-m", "py_compile", "shared/rbac.py"],
    capture_output=True,
    text=True,
    cwd="D:/Projects/cuckoo-echo/cuckoo-echo"
)
print("STDOUT:", result.stdout)
print("STDERR:", result.stderr)
print("Return code:", result.returncode)