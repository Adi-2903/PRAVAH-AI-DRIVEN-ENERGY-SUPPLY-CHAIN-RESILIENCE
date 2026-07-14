import glob

for file in glob.glob(r"d:\Desktop\Hackathon\ET\hormuz\tests\**\*.py", recursive=True):
    with open(file, "r", encoding="utf-8") as f:
        content = f.read()
    if "from schemas." in content:
        new_content = content.replace("from schemas.", "from shared.contracts.")
        with open(file, "w", encoding="utf-8") as f:
            f.write(new_content)
