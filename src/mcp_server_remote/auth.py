# auth.py
# Resolves authentication by returning an auth object to the FastMCP server

import sys
from fastmcp.server.auth.providers.jwt import StaticTokenVerifier

PLACEHOLDER = "paste your token here"
MIN_TOKEN_LENGTH = 32 # openssl rand -hex 32 should create a 64 character token

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
        print("\nGenerate a token: openssl rand -hex 32")
        print("\nPaste it into [auth] token in your local config.toml, then run again.\n")
        print("_"*50)
        sys.exit(1)

    if len(token) < MIN_TOKEN_LENGTH:
        print("_"*50)
        print("\n[ AUTHENTICATION TOKEN TOO WEAK ]")
        print(f"\nToken is {len(token)} characters. Good security needs at least {MIN_TOKEN_LENGTH}.")
        print("\nGenerate an official token: openssl rand -hex 32\n")
        print("_"*50)

    return StaticTokenVerifier(
        tokens={
            token: {
                "client_id": "mcp-client-console",
                "scopes": ["mcp:tools"],
                }
            }
        )

