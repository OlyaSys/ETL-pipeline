import random
import os
import time
import json
from pathlib import Path
from playwright.sync_api import sync_playwright, TimeoutError, Page, BrowserContext

from utils import logger

MICROLOANS_URL = "https://credistory.ru/market/microloans"
OUTPUT_RAW = Path("./data/microloans.json")
COOKIE_FILE = Path("./data/cookies.json")


def action_log(description: str):
    def decorator(action):
        def wrapper(*args, **kwargs):
            logger.info(f"[ACTION] {description}...")
            try:
                result = action(*args, **kwargs)
                logger.info(f"[OK] {description} completed successfully.")
                return result
            except Exception as e:
                logger.info(f"[ERROR] {description} failed: {e}")
                raise
        return wrapper
    return decorator


@action_log("Move mouse in browser")
def move_mouse(page: Page):
    width, height = page.viewport_size["width"], page.viewport_size["height"]
    for _ in range(random.randint(2, 5)):
        x = random.randint(int(width * 0.1), int(width * 0.9))
        y = random.randint(int(height * 0.1), int(height * 0.9))
        page.mouse.move(x, y, steps=random.randint(10, 30))
        time.sleep(random.uniform(0.2, 0.6))


@action_log("Scroll page in browser")
def scroll_page(page: Page, max_idle_rounds=3):
    curr_height = 0

    container = page.locator("mp-four-column-grid section > div").first
    total_h = page.evaluate("(el) => el.scrollHeight", container.element_handle())

    while True:
        scroll_y = page.evaluate("window.scrollY")

        if scroll_y >= total_h:
            curr_height += 1
        else:
            curr_height = 0

        if curr_height >= max_idle_rounds:
            logger.info("Achieve end of sector, stop scrolling.")
            break

        step = random.randint(100, 150)
        page.evaluate(f"window.scrollBy(0, {step})")
        time.sleep(random.uniform(0.5, 0.7))


def human_actions(page: Page):
    move_mouse(page)
    scroll_page(page)


def prepare_rows_for_db(offers: dict):
    rows = []
    card_index = 0
    for offer in offers.get("offers", []):
        card_index += 1
        law_psk_rate = offer.get("law_psk_rate")[:-1].replace(',', '.')
        total_cost_min, total_cost_max = map(float, law_psk_rate.split(" - "))
        row = {
            "card_index": card_index,
            "offer_name": offer.get("ad_label").strip(),
            "available_amount": offer.get("ad_sum_value"),
            "repayment_period": offer.get("ad_sum_description"),
            "total_cost": offer.get("law_psk_rate"),
            "avail_amount_min": offer.get("short", {}).get("min_sum"),
            "avail_amount_max": offer.get("short", {}).get("max_sum"),
            "repayment_period_min": offer.get("short", {}).get("min_term"),
            "repayment_period_max": offer.get("short", {}).get("max_term"),
            "total_cost_min": total_cost_min,
            "total_cost_max": total_cost_max,
        }
        rows.append(row)
    return rows


def load_cookies(ctx: BrowserContext):
    if os.path.exists(COOKIE_FILE):
        logger.info("Start loading cookies from file")
        try:
            with open(COOKIE_FILE) as f:
                ctx.add_cookies(json.load(f))
                logger.info("End loading cookies from file")
                return
        except Exception as e:
            logger.warning(f"Failed to load cookies.json: {e}")
    logger.info("File cookies.json does not exist")


def save_cookies(cookies: list):
    if cookies and not os.path.exists(COOKIE_FILE):
        try:
            with open(COOKIE_FILE, "w") as f:
                json.dump(cookies, f)
        except Exception as e:
            logger.warning(f"Failed to save cookies.json: {e}")


def extract_microloans():
    with sync_playwright() as p:
        with p.chromium.launch(headless=True) as browser:
            context = browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/141.0.0.0 Safari/537.36"
                )
            )

            load_cookies(context)

            page = context.new_page()

            resp_content = []

            def on_response(resp):
                try:
                    if "mpl_offers_light" in resp.url and resp.status == 200:
                        try:
                            data = resp.json()
                            resp_content.append((resp.url, data))
                            logger.info(f"Loaded JSON from {resp.url[:120]} ...")
                        except Exception:
                            logger.warning(f"Response is not JSON: {resp.url[:120]}")
                except Exception:
                    pass

            page.on("response", on_response)

            logger.info("Open page with microloans in browser")
            try:
                page.goto(MICROLOANS_URL, wait_until="domcontentloaded", timeout=60000)
                page.wait_for_load_state("domcontentloaded")
                time.sleep(3)
                cookies = context.cookies()
            except TimeoutError:
                logger.error(f"Loading page {MICROLOANS_URL} time exceeded")
                cookies = []

            logger.info("Start saving cookies to cookies.file for next sessions")
            save_cookies(cookies)
            logger.info("End saving cookies to cookies.file for next sessions")

            logger.info("Start performing browser action that simulates a human")
            human_actions(page)

            offers = {"offers": []}
            seen_ids = set()

            for _, data in resp_content:
                if not isinstance(data, dict):
                    continue
                for new_offer in data.get("offers", []):
                    offer_id = new_offer.get("offer_id")
                    if offer_id in seen_ids:
                        continue
                    seen_ids.add(offer_id)
                    offers["offers"].append(new_offer)

            context.close()
            if offers["offers"]:
                with open(OUTPUT_RAW, 'w') as out_raw:
                    json.dump(offers, out_raw)
                logger.info(f"Saved raw JSON to {OUTPUT_RAW}")

                return prepare_rows_for_db(offers)

            logger.info("No offers to save")
            return []


if __name__ == "__main__":
    extract_microloans()
