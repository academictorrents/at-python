import argparse

from .academictorrents import get


def main():
    parser = argparse.ArgumentParser(
        description="Academic Torrents simple command line tool"
    )

    parser.add_argument(
        "hash",
        type=str,
        help="Info hash, magnet link, .torrent file path or .torrent URL to download",
    )

    parser.add_argument(
        "-o",
        "--datastore",
        type=str,
        default=".",
        help="Location where to place the files",
    )

    parser.add_argument(
        "-v",
        "--verbose",
        default=False,
        action="store_true",
        help="Show logs",
    )

    parser.add_argument(
        "--no-dht",
        default=False,
        action="store_true",
        help="Don't use the DHT to find peers",
    )

    args = parser.parse_args()

    get(
        args.hash,
        datastore=args.datastore,
        showlogs=args.verbose,
        dht=not args.no_dht,
    )

    print("Exiting...")


def cli():
    """Entry point for the command line tool."""
    try:
        main()
    except KeyboardInterrupt:
        print("\nExited on keyboard interrupt.")


if __name__ == "__main__":
    cli()
