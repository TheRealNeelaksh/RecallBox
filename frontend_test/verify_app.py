
from playwright.sync_api import sync_playwright
import time

def verify_frontend():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        try:
            # Go to the app (using the port from the log)
            page.goto("http://localhost:5174")
            page.wait_for_selector("text=RecallBox", timeout=10000)

            # 1. Check Header & Config Button
            print("Verifying Header...")
            assert page.is_visible("text=Phase 1.5")

            # 2. Check Search Bar
            print("Verifying Search Bar...")
            assert page.is_visible("input[placeholder*='Search scenes']")

            # Take a screenshot of the initial state
            page.screenshot(path="frontend_test/initial_load.png")
            print("Screenshot saved to frontend_test/initial_load.png")

        except Exception as e:
            print(f"Verification failed: {e}")
            page.screenshot(path="frontend_test/error.png")
        finally:
            browser.close()

if __name__ == "__main__":
    verify_frontend()
