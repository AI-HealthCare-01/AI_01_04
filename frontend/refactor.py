import os
import re

directory = "/Users/admin/Desktop/1/AI_01_04/frontend"
files = ["chatbot.html", "medications.html", "health.html", "profile.html", "scans.html"]

for f in files:
    path = os.path.join(directory, f)
    if not os.path.exists(path):
        continue
    with open(path, encoding="utf-8") as file:
        content = file.read()

    if "bootstrap.bundle.min.js" not in content:
        content = re.sub(
            r"</body>",
            '    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js"></script>\n</body>',
            content,
        )
        with open(path, "w", encoding="utf-8") as file:
            file.write(content)
        print(f"Added bootstrap to {f}")
