#!/usr/bin/env python

"""Run the Qth registration server."""

import argparse
import asyncio
import logging

from qth_registrar import QthRegistrar, __version__


def main(args=None):
    """Command-line launcher for the server.

    The server may be cleanly terminated using a keyboard interrupt (e.g.
    ctrl+c).

    Parameters
    ----------
    args : [arg, ...]
        The command-line arguments passed to the program.
    """
    parser = argparse.ArgumentParser(
        description="Start the Qth registration server.")
    parser.add_argument("--version", "-V", action="version",
                        version="%(prog)s {}".format(__version__))
    parser.add_argument("--host",
                        default=None,
                        help="The hostname of the MQTT broker.")
    parser.add_argument("--port",
                        default=None, type=int,
                        help="The port number for the MQTT broker.")
    parser.add_argument("--keepalive",
                        default=10, type=int,
                        help="The MQTT keepalive interval.")
    parser.add_argument("--load-time",
                        default=3.0, type=float,
                        help="The number of seconds to wait for all existing "
                             "listings and client registrations to be "
                             "received after startup.")
    parser.add_argument("--quiet", "-q", action="store_true",
                        help="hide non-error output")
    args = parser.parse_args(args)

    if not args.quiet:
        logging.basicConfig(level=logging.INFO)

    loop = asyncio.get_event_loop()
    reg = QthRegistrar(host=args.host, port=args.port,
                       keepalive=args.keepalive,
                       load_time=args.load_time,
                       loop=loop)
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        loop.run_until_complete(reg.close())

    return 0


if __name__ == "__main__":  # pragma: no cover
    import sys
    sys.exit(main())
