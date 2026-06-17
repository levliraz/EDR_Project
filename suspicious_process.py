import time
import subprocess
import os
import sys

# 1. תהליך אמיתי - Notepad
subprocess.Popen(["notepad.exe"])


# 2. תהליך CPU גבוה
# subprocess.Popen([
#     "python",
#     "-c",
#     """
# import time
# for _ in range(1000000):
#     pass
# time.sleep(10)
# """
# ])

# 3. תהליך זיכרון גבוה
subprocess.Popen([
    "python",
    "-c",
    """
a = []
for _ in range(10000):
    print("line 29")
    a.append('x'*1000)
    print("a:", a)
    import time
    time.sleep(0.001)
"""
])

# 4. תהליך שרץ מ-Downloads (חשוד אצלך ב-EDR)
subprocess.Popen(
    ["python", "-c", "while True: pass"],
    cwd=os.path.expanduser("~/Downloads")
)


# 5. תהליך נוסף מקובץ אמיתי
base_dir = os.path.dirname(os.path.abspath(__file__))
file_path = os.path.join(base_dir, "suspicious_process.py")

print("Looking for:", file_path)

subprocess.Popen([sys.executable, file_path])


# 🔥 להשאיר את התוכנית חיה כדי שתראה אותם רצים
while True:
    time.sleep(1)