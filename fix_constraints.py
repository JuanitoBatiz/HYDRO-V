import os
import re
import hashlib

base_dir = r"c:\Users\jesus\OneDrive\Desktop\HYDRO-V\hydrov-backend\app\models"
for file in os.listdir(base_dir):
    if not file.endswith(".py"): continue
    path = os.path.join(base_dir, file)
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    def repl(m):
        constraint_text = m.group(1)
        # Fix missing names
        h = hashlib.md5(constraint_text.encode()).hexdigest()[:6]
        return f'CheckConstraint("{constraint_text}", name="chk_{file.replace(".py","")}_{h}")'

    new_content = re.sub(r'CheckConstraint\("([^"]+)"\)', repl, content)
    with open(path, "w", encoding="utf-8") as f:
        f.write(new_content)

print("Constraints named.")
