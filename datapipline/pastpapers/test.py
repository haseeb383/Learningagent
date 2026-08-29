"""
Checks a list of {qp_url, ms_url} dicts to see which URLs are broken.
"Broken" = request fails, non-200 status, OR page body contains "Paper not found".
"""
from create_urls import _create_url

import requests
import time
import json

NOT_FOUND_TEXT = "Paper not found"
TIMEOUT = 10          # seconds per request
DELAY = 0.5           # be polite to the server between requests
HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; paper-checker/1.0)"
}


def check_url(url: str) -> dict:
    """Returns a result dict describing whether this single URL is usable."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
    except requests.RequestException as e:
        return {"url": url, "ok": False, "reason": f"request_error: {e}"}

    if resp.status_code != 200:
        return {"url": url, "ok": False, "reason": f"status_{resp.status_code}"}

    if NOT_FOUND_TEXT in resp.text:
        return {"url": url, "ok": False, "reason": "paper_not_found"}

    return {"url": url, "ok": True, "reason": None}


def check_all(papers: list[dict]) -> dict:
    """
    papers: list of dicts, each with 'qp_url' and 'ms_url'.
    Returns {"broken": [...], "checked": total_count}
    """
    broken = []
    total = 0

    for record in papers:
        for key in ("qp_url", "ms_url"):
            url = record.get(key)
            if not url:
                continue

            total += 1
            result = check_url(url)
            print(f"[{'OK' if result['ok'] else 'FAIL'}] {key}: {url}")

            if not result["ok"]:
                broken.append({
                    "url": url,
                    "type": key,
                    "reason": result["reason"],
                })

            time.sleep(DELAY)

    return {"broken": broken, "checked": total}


if __name__ == "__main__":
    # Replace this with however you're loading your generated list
    papers = _create_url("mathematics_9709", 2026)

    results = check_all(papers)

    print("\n--- Summary ---")
    print(f"Checked: {results['checked']}")
    print(f"Broken:  {len(results['broken'])}")

    with open("broken_urls.json", "w") as f:
        json.dump(results["broken"], f, indent=2)

    print("Broken URLs written to broken_urls.json")