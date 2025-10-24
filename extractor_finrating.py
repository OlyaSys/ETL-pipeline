import json, hashlib
from pathlib import Path
from playwright.sync_api import sync_playwright, Page
import dateparser

from utils import logger

START_URL   = "https://credistory.ru/finrating"
STATE_FILE  = Path(__file__).with_name("state_reviews.json")
MAX_PAGES   = 10

CARD_SEL    = "mt-ugc-review-card"
TITLE_SEL   = ".p2-bold"
BODY_SEL    = "div.review-description"
RATING_SEL  = "div.d-flex.justify-content-between > div"
DATE_SEL    = ".p3.color-gray-strong-text"


def sha(s: str):
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def load_state():
    if STATE_FILE.exists():
        with open(STATE_FILE, 'r') as state_file:
            return json.load(state_file)
    return {"seen_ids": []}


def save_state(state: dict):
    with open(STATE_FILE, 'w') as state_file:
        json.dump(state, state_file)


def collect_reviews_on_page(page: Page):
    cards = page.locator(CARD_SEL)
    n = cards.count()
    reviews = []
    for i in range(n):
        card = cards.nth(i)

        title = card.locator(TITLE_SEL).first.inner_text(timeout=2000) if card.locator(TITLE_SEL).count() else ""
        rating = int(card.locator(RATING_SEL).last.inner_text().strip())
        desc = card.locator(BODY_SEL).first
        read_more = desc.locator("span.color-accent-strong", has_text="читать")
        if read_more.count():
            read_more.first.click()
            page.wait_for_load_state("load")
            page.wait_for_timeout(300)

        body = desc.inner_text().strip().replace("скрыть", "").strip()
        date_text = card.locator(DATE_SEL).first.inner_text(timeout=1500) if card.locator(DATE_SEL).count() else ""
        date = dateparser.parse(date_text).date()

        ext_id = sha((title or "") + "|" + (date_text or "") + "|" + (body[:50] if body else ""))
        item = {
            "ext_id": ext_id,
            "title": title,
            "body": body,
            "rating": rating,
            "date": date,
        }
        reviews.append(item)
    return reviews


def try_click_next(page: Page):
    btn = page.get_by_role("button", name="Показать ещё отзывы")
    if btn.count() and btn.is_enabled():
        btn.click()
        page.wait_for_timeout(2000)
        return True
    return False


def extract_reviews():
    logger.info("Start extracting reviews")
    reviews = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        context = browser.new_context()
        page = context.new_page()

        page.goto(START_URL, wait_until="domcontentloaded")
        page.wait_for_timeout(3000)

        logger.info(f"Start opening reviews {MAX_PAGES} time")
        for _ in range(MAX_PAGES - 1):
            if try_click_next(page):
                continue
        logger.info(f"End opening reviews")

        reviews = collect_reviews_on_page(page)

        browser.close()

    prev = load_state()
    prev_ids = set(prev.get("seen_ids", []))

    curr_ids = [x["ext_id"] for x in reviews if x.get("ext_id")]

    new_reviews = [x for x in reviews if x.get("ext_id") and x["ext_id"] not in prev_ids]

    save_state({"seen_ids": curr_ids})
    logger.info(reviews)
    logger.info("Stop extracting reviews")
    return new_reviews


if __name__ == "__main__":
    extract_reviews()
