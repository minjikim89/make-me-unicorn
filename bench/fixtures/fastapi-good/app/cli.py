import yaml
def banner(version: str, name: str) -> None:
    print(f"Update available: {version}")
    print(f"Select a plan for {name}")
def load_cfg(path):
    with open(path) as f:
        return yaml.load(f, yaml.SafeLoader)
