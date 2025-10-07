from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent  # adjust depth to reach repo root
print(f"PROJECT_ROOT = {PROJECT_ROOT}")
GIT_REPO_ROOT = PROJECT_ROOT.parents[
    1
]  # assuming this is one level up from the project root
print(f"GIT_REPO_ROOT = {GIT_REPO_ROOT}")
CONFIG_DIR = Path(GIT_REPO_ROOT, "config")
print(f"CONFIG_DIR = {CONFIG_DIR}")
