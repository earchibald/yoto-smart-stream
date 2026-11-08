"""``yoto-mcp``: run the MCP server (default), or set up, log in and run live checks.

yoto-mcp setup                 store the Yoto app's client id and secret in the keychain
yoto-mcp login NAME            log in through the browser and link the account as NAME
yoto-mcp accounts              list linked accounts
yoto-mcp default NAME          make NAME the default account
yoto-mcp check icons|resume    run a live check against the default (or --account) account
yoto-mcp serve                 run the stdio MCP server (what the plugin launches)
"""

from __future__ import annotations

import argparse
import getpass
import json
import sys

from . import vault


def _setup(args) -> None:
    cid = args.client_id or input("Yoto client id: ").strip()
    secret = args.client_secret or getpass.getpass("Yoto client secret (hidden; blank if none): ").strip()
    vault.save_client(cid, secret or None)
    if args.redirect_uri:
        from . import paths

        f = paths.home() / "settings.json"
        settings = json.loads(f.read_text()) if f.exists() else {}
        settings["redirect_uri"] = args.redirect_uri
        f.write_text(json.dumps(settings, indent=1))
    print("Saved to the keychain (service 'yoto-mcp'). Next: yoto-mcp login <name>")


def _login(args) -> None:
    from .session import Session

    s = Session()
    url = s.start_login(args.name, open_browser=not args.no_browser)
    print(f"Log in to Yoto in the browser (or open this URL):\n  {url}\n", flush=True)
    flow, _ = s.pending_logins[args.name]
    try:
        flow.wait(timeout=600)
    finally:
        for msg in s.finish_logins():
            print(msg)


def _accounts(_args) -> None:
    items = vault.accounts()
    if not items:
        print("No accounts linked. Run: yoto-mcp login <name>")
    for a in items:
        print(f"{'*' if a.default else ' '} {a.name}")


def _default(args) -> None:
    print(f"Default account is now {vault.set_default(args.name).name!r}.")


def _check(args) -> None:
    from .checks import CHECKS
    from .session import Session

    s = Session()
    for name in args.which:
        print(json.dumps(CHECKS[name](s, args.account), indent=1))


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(
        prog="yoto-mcp", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    sub = ap.add_subparsers(dest="cmd")
    p = sub.add_parser("setup", help="store client id/secret in the keychain")
    p.add_argument("--client-id")
    p.add_argument("--client-secret")
    p.add_argument("--redirect-uri", help=f"registered callback URL (default {vault.DEFAULT_REDIRECT_URI})")
    p.set_defaults(fn=_setup)
    p = sub.add_parser("login", help="link a Yoto account under a short name")
    p.add_argument("name")
    p.add_argument("--no-browser", action="store_true")
    p.set_defaults(fn=_login)
    sub.add_parser("accounts", help="list linked accounts").set_defaults(fn=_accounts)
    p = sub.add_parser("default", help="set the default account")
    p.add_argument("name")
    p.set_defaults(fn=_default)
    p = sub.add_parser("check", help="live checks for open questions")
    p.add_argument("which", nargs="+", choices=["icons", "resume"])
    p.add_argument("--account")
    p.set_defaults(fn=_check)
    sub.add_parser("serve", help="run the stdio MCP server")
    args = ap.parse_args(argv)
    if args.cmd in (None, "serve"):
        from .server import run

        run()
        return
    try:
        args.fn(args)
    except (LookupError, ValueError, RuntimeError) as exc:
        sys.exit(f"yoto-mcp: {exc}")


if __name__ == "__main__":
    main()
