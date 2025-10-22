from playwright.sync_api import sync_playwright
from dotenv import load_dotenv
import os, csv

# Load environment variables
load_dotenv()

PROFILE_PATH = os.getenv("PROFILE_PATH")
TARGET_URL = os.getenv("TARGET_URL")
OUTPUT_CSV = os.getenv("OUTPUT_CSV", "grades.csv")

if not PROFILE_PATH or not TARGET_URL:
    raise ValueError("❌ Please set PROFILE_PATH and TARGET_URL in your .env file.")

def scrape_from_frame(frame):
    """Extract rows from a given frame."""
    results = []
    try:
        frame.wait_for_selector("tr", timeout=5000)
    except Exception:
        pass

    trs = frame.query_selector_all("tr")
    current_subject = ""

    for tr in trs:
        cls = tr.get_attribute("class") or ""
        if "sk_thead" in cls:
            th = tr.query_selector("th")
            if th:
                current_subject = th.inner_text().strip()
            continue

        title_el = tr.query_selector("td.result_title")
        credits_el = tr.query_selector("td.result-credits")
        value_el = tr.query_selector("td.result-value")

        if title_el or credits_el or value_el:
            title = title_el.inner_text().strip() if title_el else ""
            credits = credits_el.inner_text().strip() if credits_el else ""
            value = value_el.inner_text().strip() if value_el else ""
            if title or credits or value:
                results.append((current_subject, title, credits, value))
            continue

        tds = tr.query_selector_all("td")
        if tds:
            texts = [td.inner_text().strip() for td in tds]
            if len(texts) >= 3:
                title, credits, value = texts[0], texts[1], texts[2]
            elif len(texts) == 2:
                title, credits, value = texts[0], "", texts[1]
            else:
                title, credits, value = texts[0], "", ""
            if any([title, credits, value]):
                results.append((current_subject, title, credits, value))
    return results

def find_and_scrape_all_frames(page):
    """Scan main frame + child frames."""
    results = []
    main = page.main_frame
    results.extend(scrape_from_frame(main))
    for f in main.child_frames:
        results.extend(scrape_from_frame(f))
        for gf in f.child_frames:
            results.extend(scrape_from_frame(gf))
    return results

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch_persistent_context(user_data_dir=PROFILE_PATH, headless=False)
        page = browser.new_page()
        print("🌐 Opening:", TARGET_URL)
        page.goto(TARGET_URL, wait_until="networkidle")

        print("If you're not logged in, please do so in the opened browser window.")
        input("Press Enter when you can see your results table...")

        rows = find_and_scrape_all_frames(page)

        if not rows:
            print("⚠️ No rows found. Confirm you're logged in and that the table is visible.")
        else:
            with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["Subject", "Title", "Credits", "Value"])
                writer.writerows(rows)
            print(f"✅ Success! Saved {len(rows)} rows to {OUTPUT_CSV}")

        browser.close()

if __name__ == "__main__":
    main()
