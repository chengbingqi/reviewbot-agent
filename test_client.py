import json
import time
import argparse

import requests

from report_exporter import export_report

URL = "http://127.0.0.1:8000/review"


DEMO_CODE = """
def update_user(name, pwd):
    db_conn = f"mysql://root:{pwd}@localhost/users"
    print("User updated")
"""


def main() -> None:
    parser = argparse.ArgumentParser(description="Send demo code to ReviewBot API.")
    parser.add_argument("--save-report", action="store_true", help="Save Markdown and HTML report to reports/.")
    args = parser.parse_args()

    print("Sending demo code to ReviewBot...\n")
    response = requests.post(URL, json={"code": DEMO_CODE}, stream=True, timeout=120)
    response.raise_for_status()
    final_report = ""

    for line in response.iter_lines():
        if not line:
            continue
        decoded_line = line.decode("utf-8")
        if not decoded_line.startswith("data: "):
            continue
        data = json.loads(decoded_line[6:])
        event = data.get("event")
        if event == "node_end":
            print(data.get("message"))
            time.sleep(0.2)
        elif event == "error":
            print(f"[warning] {data.get('node')}: {data.get('message')}")
        elif event == "done":
            payload = data.get("data") or {}
            final_report = payload.get("report", "")
            print("\n================ Final Report ================\n")
            print(final_report)

    if args.save_report and final_report:
        exported = export_report(final_report)
        print(f"\nSaved Markdown: {exported.markdown_path}")
        print(f"Saved HTML: {exported.html_path}")


if __name__ == "__main__":
    main()
