"""Small CLI client for the same durable workflow used by the website."""
import json
import secrets
import time
import httpx

def main():
    name = input("Company name: ").strip()
    if not name:
        return
    token = secrets.token_urlsafe(32)
    with httpx.Client(base_url="http://127.0.0.1:8000", headers={"Authorization": f"Bearer {token}"}, timeout=30) as client:
        response = client.post("/runs", json={"company_name": name})
        response.raise_for_status()
        run = response.json()
        print("Session token (keep private to recover this research):", token)
        last = ""
        while True:
            run = client.get(f"/runs/{run['id']}").json()
            if run["message"] != last:
                last = run["message"]
                print(last)
            if run["status"] == "needs_company_confirmation":
                if input(f"Research {run['identity']['name']}? [y/N] ").lower() != "y":
                    client.post(f"/runs/{run['id']}/cancel")
                    return
                client.post(f"/runs/{run['id']}/confirm").raise_for_status()
            elif run["status"] == "awaiting_domain_selection":
                choices = run["company_brief"]["domains"]
                for i, domain in enumerate(choices, 1):
                    print(f"{i}. {domain['name']}")
                selection = input("Domain number: ")
                if not selection.isdigit() or not 1 <= int(selection) <= len(choices):
                    print("Please choose a listed number.")
                    continue
                client.post(f"/runs/{run['id']}/domain", json={"selected_domain": choices[int(selection)-1]["name"]}).raise_for_status()
            elif run["status"] in {"completed", "failed", "insufficient_evidence", "cancelled", "export_failed"}:
                print(json.dumps(run.get("domain_brief") or run.get("company_brief"), indent=2))
                return
            time.sleep(2)

if __name__ == "__main__":
    main()
