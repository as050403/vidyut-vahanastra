from pathlib import Path


folders = [
    "data",
    "modules",
    "utils",
    "assets",
    "assets/screenshots",
    "docs",
    ".streamlit"
]


for folder in folders:
    Path(folder).mkdir(parents=True, exist_ok=True)
    print(f"OK: {folder}")