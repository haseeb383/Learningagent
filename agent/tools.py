from ddgs import DDGS
from playwright.sync_api import sync_playwright
from langchain_core.tools import tool
from playwright_stealth import Stealth

@tool
def searcher(query: str, max_results: int = 10):
    """Search the web and return top results with snippets."""
    results = []
    with DDGS() as ddgs:
        for r in ddgs.text(query, max_results=max_results):
            results.append({
                "url": r.get("href") or r.get("url"),
                "title": r.get("title"),
                "snippet": r.get("body") or r.get("snippet")
            })
    return results

# @tool
def extracter(target_url: str):
    """Extract full content from URLs. Returns markdown per URL."""
    extracted_data = {
        "url": target_url,
        "title": "",
        "text": "",
        "images": [],
        "links": [],
    }
    with Stealth().use_sync(sync_playwright()) as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()
        try:
            page.goto(target_url, wait_until="networkidle", timeout=30000)
            extracted_data["url"] = page.url
            extracted_data["title"] = page.title()
            extracted_data["text"] = page.locator("body").inner_text()
            img_srcs = page.locator("img").evaluate_all(
                "elements => elements.map(el => el.src)"
            )
            extracted_data["images"] = list(set([src for src in img_srcs if src]))
            href_links = page.locator("a").evaluate_all(
                "elements => elements.map(el => el.href)"
            )
            extracted_data["links"] = list(set([link for link in href_links if link]))

        except Exception as e:
            print(f"Error scraping {target_url}: {e}")
        finally:
            browser.close()

    return extracted_data

print(extracter("https://pastpapers.papacambridge.com/papers/caie/as-and-a-level-mathematics-9709-2025-oct-nov")['links'])