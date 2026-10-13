import sys


def main() -> int:
    args = sys.argv[1:]
    if args and not args[0].startswith("-"):
        from comparativo.cli import main as cli_main

        return cli_main(args)
    from comparativo.server import main as server_main

    return server_main(args)


if __name__ == "__main__":
    raise SystemExit(main())
