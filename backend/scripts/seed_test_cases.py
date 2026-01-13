import argparse
import json
import sys
from pathlib import Path
import httpx


def main() -> int:
    parser = argparse.ArgumentParser(description="Seed test cases via the API")
    parser.add_argument("--api", default="http://localhost:8001", help="Base API URL")
    parser.add_argument("--file", default="backend/sample_data/test_cases.json", help="Path to JSON test cases")
    args = parser.parse_args()

    file_path = Path(args.file)
    if not file_path.exists():
        print(f"File not found: {file_path}")
        return 1

    data = json.loads(file_path.read_text())
    if not isinstance(data, list):
        print("Expected a list of test cases")
        return 1

    created = 0
    with httpx.Client(timeout=30) as client:
        for item in data:
            resp = client.post(f"{args.api}/api/test-cases/", json=item)
            if resp.status_code >= 300:
                print(f"Failed: {resp.status_code} {resp.text}")
                return 1
            created += 1

    print(f"Created {created} test cases")
    return 0


if __name__ == "__main__":
    sys.exit(main())
