# auth.py
# Resolves authentication by returning an auth object to the FastMCP server

import sys
from fastmcp.server.auth.providers.jwt import StaticTokenVerifier

PLACEHOLDER = "paste your token here"
MIN_TOKEN_LENGTH = 64 # openssl rand -hex 32 should create a 64 character token

def _token_command() -> str:
    """
        Returns a command line the user can copy and paste to generate a bearer token, per OS.
    """
    if sys.platform == "win32":
        return 'python -c "import secrets; print(secrets.token_hex(32))"'
    return "openssl rand -hex 32"   # macOS and Linux both have openssl command preinstalled

def resolve_auth(config: dict) -> StaticTokenVerifier:
    """
        Returns a verified bearer token to the FastMCP server.
        Rejects attempt to start if no token/bad token.
        config = dictionary from config.toml file (formed by config_loader.py)
    """
    token = str(config.get("auth", {}).get("token", "")).strip()

    if not token or token == PLACEHOLDER:
        print("_"*50)
        print("\n[ AUTHENTICATION NOT CONFIGURED ]")
        print(f"\nGenerate an official token:\n")
        print(f"   {_token_command()}\n")
        print("\nPaste it into [auth] token in your local config.toml, then run again.\n")
        print("_"*50)
        sys.exit(1)

    if len(token) < MIN_TOKEN_LENGTH:
        print("_"*50)
        print("\n[ AUTHENTICATION TOKEN TOO WEAK ]")
        print(f"\nToken is {len(token)} characters. Good security needs at least {MIN_TOKEN_LENGTH}.")
        print(f"\nGenerate an official token:\n")
        print(f"   {_token_command()}\n")
        print("_"*50)
        sys.exit(1)

    return StaticTokenVerifier(
        tokens={
            token: {
                "client_id": "mcp-client-console",
                "scopes": ["mcp:tools"],
                }
            }
        )

