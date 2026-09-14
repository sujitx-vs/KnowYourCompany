"""Explicit setup and maintenance commands; no tasks are scheduled automatically."""
import argparse
import json
from dotenv import load_dotenv
from backend.config import validate_configuration


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["check-config", "setup-storage", "metrics", "cleanup"])
    parser.add_argument("--retention-days", type=int, default=30)
    parser.add_argument("--apply", action="store_true", help="Required to remove expired database records")
    args = parser.parse_args()
    load_dotenv()
    validate_configuration()
    if args.command == "check-config":
        print("Configuration is valid. No provider connectivity was tested.")
    elif args.command == "setup-storage":
        from backend.supabase_client import ensure_bucket_exists
        if not ensure_bucket_exists():
            raise SystemExit("Storage setup failed. Check server configuration and permissions.")
        print("Private report bucket is available.")
    else:
        from backend.store import Store
        store = Store()
        if args.command == "metrics":
            from backend.main import summary
            print(json.dumps(summary(store.recent()), indent=2))
        else:
            if args.retention_days < 1:
                parser.error("Retention must be at least one day")
            if not args.apply:
                print("No changes made. Add --apply to remove expired database records. Stored PDFs are not deleted by this command.")
                return
            print(f"Removed {store.cleanup(args.retention_days)} expired research records. Configure separate PDF retention in storage.")


if __name__ == "__main__":
    main()
