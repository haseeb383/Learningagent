import os
import re
import yaml
from playwright.sync_api import sync_playwright
from playwright_stealth import Stealth
from pypdf import PdfReader, PdfWriter

SUBJECT_YAML_PATH = "datapipline/pastpapers/subject.yaml"
OUTPUT_DIR = "datapipline/pastpapers/downlaods"

# Matches filenames like: 9709_m26_ms_22.pdf
FILENAME_PATTERN = re.compile(
    r"(?P<subject_code>\d{4})_"
    r"(?P<session_code>[a-z])(?P<yy>\d{2})_"
    r"(?P<doc_type>qp|ms)_"
    r"(?P<paper>\d)(?P<variant>\d)"
    r"\.pdf$",
    re.IGNORECASE,
)


# ---------- 1. Load subject config ----------

def load_subject(subject: str) -> dict:
    with open(SUBJECT_YAML_PATH, "r") as file:
        return yaml.safe_load(file)[subject]


# ---------- 2. Build the listing-page URL for one session ----------

def build_session_url(subject_slug: str, subject_code: str, year: int, session_name: str) -> str:
    URL_TEMPLATE = (
        "https://pastpapers.papacambridge.com/papers/caie/"
        "{subject_slug}-{subject_code}-{year}-{session_name}"
    )
    return URL_TEMPLATE.format(
        subject_slug=subject_slug,
        subject_code=subject_code,
        year=year,
        session_name=session_name,
    )


# ---------- 3. Extract all links from the listing page ----------

def extracter(context, target_url: str) -> list[str]:
    """
    Uses the shared browser context passed in from run_pipeline instead of
    launching its own Playwright instance — nesting two sync_playwright()
    calls is what caused the asyncio-loop error.
    """
    links = []
    page = context.new_page()
    try:
        page.goto(target_url, wait_until="networkidle", timeout=30000)
        href_links = page.locator("a").evaluate_all(
            "elements => elements.map(el => el.href)"
        )
        links = list(set([link for link in href_links if link]))
    except Exception as e:
        print(f"Error scraping {target_url}: {e}")
    finally:
        page.close()

    return links


# ---------- 4. Parse each link's filename into metadata ----------

def parse_link(url: str) -> dict | None:
    """
    Pulls subject_code, session_code, yy, doc_type, paper, variant out of
    the filename at the end of the download URL. Returns None if the URL
    isn't a real paper download.
    """
    match = FILENAME_PATTERN.search(url)
    if not match:
        return None

    data = match.groupdict()
    data["paper"] = int(data["paper"])
    data["variant"] = int(data["variant"])
    data["url"] = url
    return data


# ---------- 5. Group parsed links into qp/ms pairs by filename metadata ----------

def pair_qp_ms(links: list[str]) -> list[dict]:
    """
    Keys each parsed link by (subject_code, session_code, yy, paper, variant)
    so a qp and its matching ms land in the same pair, regardless of the
    order they appeared on the page.
    """
    grouped: dict[tuple, dict] = {}

    for url in links:
        parsed = parse_link(url)
        if parsed is None:
            continue

        key = (
            parsed["subject_code"],
            parsed["session_code"],
            parsed["yy"],
            parsed["paper"],
            parsed["variant"],
        )
        grouped.setdefault(key, {"qp": None, "ms": None})
        grouped[key][parsed["doc_type"]] = parsed

    pairs = list(grouped.values())

    for key, pair in zip(grouped.keys(), pairs):
        if pair["qp"] is None or pair["ms"] is None:
            print(f"Incomplete pair for {key}: {pair}")

    return pairs


# ---------- 6. Download one file via Playwright ----------

def download_with_playwright(context, url: str, filepath: str) -> bool:
    page = context.new_page()
    try:
        with page.expect_download(timeout=30000) as download_info:
            try:
                page.goto(url, timeout=30000)
            except Exception:
                # navigating straight to a file download often throws
                # net::ERR_ABORTED even though the download itself succeeds
                pass
        download = download_info.value
        download.save_as(filepath)
        return True
    except Exception as e:
        print(f"Failed to download {url}: {e}")
        return False
    finally:
        page.close()


# ---------- 7. Embed metadata into the downloaded PDF ----------

def add_metadata_to_pdf(filepath: str, metadata: dict) -> None:
    reader = PdfReader(filepath)
    writer = PdfWriter()
    writer.append(reader)

    writer.add_metadata({
        "/SubjectCode": metadata["subject_code"],
        "/SessionCode": metadata["session_code"],
        "/Year": f"20{metadata['yy']}",
        "/Paper": str(metadata["paper"]),
        "/Variant": str(metadata["variant"]),
        "/DocType": metadata["doc_type"],
    })

    tmp_path = filepath + ".tmp"
    with open(tmp_path, "wb") as f:
        writer.write(f)
    os.replace(tmp_path, filepath)


# ---------- 8. Download a session's paired files + tag metadata ----------

def download_pairs(context, pairs: list[dict], output_dir: str) -> None:
    os.makedirs(output_dir, exist_ok=True)

    for pair in pairs:
        for doc_type in ("qp", "ms"):
            link = pair.get(doc_type)
            if link is None:
                continue

            filename = f"{link['subject_code']}_{link['session_code']}{link['yy']}_{doc_type}_{link['paper']}{link['variant']}.pdf"
            filepath = os.path.join(output_dir, filename)

            ok = download_with_playwright(context, link["url"], filepath)
            if not ok:
                continue

            add_metadata_to_pdf(filepath, link)
            print(f"Downloaded + tagged: {filename}")


# ---------- 9. Main loop: all sessions for a subject/year ----------

def run_pipeline(subject: str, year: int) -> None:
    subject_data = load_subject(subject)

    with Stealth().use_sync(sync_playwright()) as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(accept_downloads=True)

        for session_code, session_name in subject_data["sessions"]:
            print(f"\n=== Session: {session_name} ({session_code}) ===")

            url = build_session_url(
                subject_slug=subject_data["subject_slug"],
                subject_code=subject_data["subject_code"],
                year=year,
                session_name=session_name,
            )

            raw_links = extracter(context, url)
            pairs = pair_qp_ms(raw_links)

            session_dir = os.path.join(OUTPUT_DIR, subject, str(year), session_code)
            download_pairs(context, pairs, session_dir)

        browser.close()


if __name__ == "__main__":
    run_pipeline(subject="mathematics_9709", year=2026)