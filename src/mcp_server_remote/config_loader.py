# config_loader.py
# Finds, creates, and loads the user config.toml file for remote server access

import sys
import tomllib
from pathlib import Path
from importlib.resources import files
from platformdirs import user_config_dir

APP_NAME = "mcp-server-remote"

### Defines destination filepath for Config File
def config_path() -> Path:
    folder = Path(user_config_dir(APP_NAME, appauthor=False)) # appauthor=False stops Windows from adding an ewhat is the factMCP schema for tools? is sxtra folder.
    file = folder / "config.toml"
    return file

### Creates Config File (from template) if does not exist
def config_create() -> Path:
    config_file = config_path()
    if not config_file.exists():
        config_file.parent.mkdir(parents=True, exist_ok=True)
        template = files("mcp_server_remote").joinpath("config_default.toml")
        text = template.read_text()
        config_file.write_text(text)
        config_file.chmod(0o600) # owner access only, security concerns as token lives in this file
        print(f"Created config: {config_file}")
        print(f"Edit the values, save, and run the package again to begin.")
        sys.exit(1)
    return config_file

### Load settings from Config File into Python dictionary
def config_load() -> dict:
    config_file = config_create()
    with open(config_file, "rb") as f: # note that tomllib needs to read in binary, hence "rb"
        config_dictionary = tomllib.load(f)
    return config_dictionary

if __name__ == "__main__":
    config = config_load()
    server = get_active_server(config)
    print("_" * 50)
    print(f"Server Config Loaded.")
    print(f"Name: {server['name']}")
    print(f"Destination: {server['host']}:{server['port']}{server['path']}")
    print(f"Active Server: {server['name']} @ {server['url']}")
    print("_" * 50)



