#!/usr/bin/env python3
"""
WA Agent — WhatsApp AI Auto-Reply Agent
Usage: python run.py [--port 3000] [--no-poller]
"""
import argparse, logging, os, signal, sys
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)

from wa_agent import db, poller, web

def main():
    parser = argparse.ArgumentParser(description="WA Agent")
    parser.add_argument("--port", type=int, default=int(os.environ.get("WA_AGENT_PORT", 3000)))
    parser.add_argument("--no-poller", action="store_true", help="Start web UI only, no message poller")
    args = parser.parse_args()

    db.init_db()

    if not args.no_poller:
        poller.start()

    def shutdown(sig, frame):
        print("\nShutting down...")
        poller.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    web.run(port=args.port)

if __name__ == "__main__":
    main()
