import os
import glob

# Rename shared/schemas to shared/contracts
os.rename(r"d:\Desktop\Hackathon\ET\hormuz\shared\schemas", r"d:\Desktop\Hackathon\ET\hormuz\shared\contracts")

# Delete local models.py
for agent in ["scenario-engine", "procurement-agent", "spr-agent"]:
    p = rf"d:\Desktop\Hackathon\ET\hormuz\{agent}\models.py"
    if os.path.exists(p):
        os.remove(p)

# Global replace shared.contracts to shared.contracts
for ext in ["**/*.py", "**/*.md"]:
    for file in glob.glob(rf"d:\Desktop\Hackathon\ET\hormuz\{ext}", recursive=True):
        if "node_modules" in file or ".next" in file or ".git" in file:
            continue
        with open(file, "r", encoding="utf-8") as f:
            content = f.read()
        if "shared.contracts" in content:
            new_content = content.replace("shared.contracts", "shared.contracts")
            with open(file, "w", encoding="utf-8") as f:
                f.write(new_content)
