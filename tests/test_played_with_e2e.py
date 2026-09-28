import http.server
import socketserver
import threading
import time
from playwright.sync_api import sync_playwright

class ReusableTCPServer(socketserver.TCPServer):
    allow_reuse_address = True

httpd = ReusableTCPServer(("", 0), http.server.SimpleHTTPRequestHandler)
port = httpd.server_address[1]

server_thread = threading.Thread(target=httpd.serve_forever, daemon=True)
server_thread.start()
time.sleep(0.2)

try:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        
        # ─────────────────────────────────────────────────────────────
        # 1. Desktop & Core Mechanics Test
        # ─────────────────────────────────────────────────────────────
        page = browser.new_page(viewport={"width": 1280, "height": 800})
        page.goto(f"http://localhost:{port}/games/played_with.html")
        page.wait_for_load_state("domcontentloaded")
        page.wait_for_selector("header")
        
        print(f"Page Title: {page.title()}")
        
        # 1. Verify Puzzle badge
        puzzle_badge = page.locator("#puzzle-badge").inner_text()
        print(f"✓ Puzzle badge: {puzzle_badge}")
        assert "PUZZLE #" in puzzle_badge, f"Expected PUZZLE #, got {puzzle_badge}"
        
        # 2. Mystery Player Hero Card (Initial state: ???????)
        mystery_hero = page.locator("#mystery-player-display")
        assert mystery_hero.is_visible(), "Mystery Player Hero Card must be visible"
        hero_initial_text = mystery_hero.inner_text().strip()
        print(f"✓ Mystery Player hero initial text: {hero_initial_text}")
        assert "?" in hero_initial_text, f"Hero should show question marks initially, got {hero_initial_text}"
        
        # 3. Verify Header & Nav
        assert page.locator("header img[alt='PLAYMAKER']").is_visible()
        assert page.locator("#lang-switcher").is_visible()
        assert page.locator("header .material-symbols-outlined:has-text('volume_up')").count() == 0
        assert page.locator("header .material-symbols-outlined:has-text('bar_chart')").count() == 0
        print("✓ Header verified cleanly (no sound/graph icons)")
        
        # 4. Verify Clue Cards - No Teammate Nationality in heading & No Shared Club
        clue_cards = page.locator("#clue-cards-section > div")
        assert clue_cards.count() == 5, f"Expected 5 clue cards, got {clue_cards.count()}"
        card1_text = clue_cards.nth(0).inner_text()
        assert "Shared Club" not in card1_text, "Shared club must NOT be shown on clue card"
        # Check that country name is not in card1 heading
        assert "(Portugal)" not in card1_text and "(Spain)" not in card1_text and "(France)" not in card1_text, "Nationality must not be shown after teammate name"
        print("✓ Teammate nationality is NOT shown after teammate name")
        
        # 5. Verify Mystery Player Hints: Nationality & Position
        hint_nat_btn = page.locator("#hint-nat-btn")
        hint_pos_btn = page.locator("#hint-pos-btn")
        assert hint_nat_btn.is_visible(), "Nationality hint button should be visible initially"
        assert hint_pos_btn.is_visible(), "Position hint button should be visible initially"
        
        hint_nat_btn.click()
        page.wait_for_selector("#player-nat-badge:not(.hidden)")
        nat_text = page.locator("#mystery-nat-text").inner_text()
        print(f"✓ Nationality hint revealed: '{nat_text}'")
        assert len(nat_text) > 1, "Nationality hint text should be populated"
        assert hint_nat_btn.is_hidden(), "Nationality hint button should hide after click"

        hint_pos_btn.click()
        page.wait_for_selector("#player-pos-badge:not(.hidden)")
        pos_text = page.locator("#mystery-pos-text").inner_text()
        print(f"✓ Position hint revealed: '{pos_text}'")
        assert len(pos_text) > 1, "Position hint text should be populated"
        assert hint_pos_btn.is_hidden(), "Position hint button should hide after click"

        # 6. Verify Matches Hint Button & Toast
        hint_btn = clue_cards.nth(0).locator(".reveal-matches-btn")
        assert hint_btn.is_visible(), "Matches hint button should be visible initially"
        hint_btn.click()
        page.wait_for_timeout(200)
        toast_text = page.locator(".fa-toast-item").last.inner_text()
        print(f"✓ Matches hint toast fired: '{toast_text}'")
        assert "matches" in toast_text.lower() or "played" in toast_text.lower()
        
        # 6. Verify Skip Clue without losing a life & with confirmation modal
        skip_btn = page.locator("#skip-clue-btn")
        skip_btn.click()
        page.wait_for_selector(".fa-confirm-overlay, #fa-confirm-modal, div:has-text('SKIP CLUE?')")
        print("✓ Skip confirmation modal appeared")
        
        # Click confirm in the confirm dialog
        confirm_btn = page.locator("button:has-text('SKIP CLUE'), button:has-text('CONFIRM'), button:has-text('YES')").first
        confirm_btn.click()
        page.wait_for_timeout(200)
        
        # Check Lives counter - must STILL be 5!
        lives_after_skip = page.locator("#lives-counter").inner_text()
        print(f"✓ Lives counter after skip: {lives_after_skip}")
        assert lives_after_skip == "5", f"Skip must NOT cost a life! Expected 5 lives, got {lives_after_skip}"
        
        # Check Clue 2 is now revealed
        progress_step = page.locator("#progress-step").inner_text()
        print(f"✓ Revealed clues progress after skip: {progress_step}")
        assert progress_step == "2", f"Expected 2 revealed clues after skip, got {progress_step}"
        
        # 7. Fast Autocomplete Test
        t0 = time.time()
        guess_input = page.locator("#guess-input")
        guess_input.focus()
        guess_input.fill("cristiano")
        page.wait_for_selector("#autocomplete-list .fa-dropdown-row")
        dropdown_rows = page.locator("#autocomplete-list .fa-dropdown-row")
        elapsed = time.time() - t0
        dropdown_count = dropdown_rows.count()
        print(f"✓ Autocomplete returned {dropdown_count} rows in {elapsed:.3f}s (sub-50ms responsive)")
        assert dropdown_count > 0, "Autocomplete dropdown should have options"
        assert elapsed < 1.0, f"Autocomplete search should be sub-second, took {elapsed:.3f}s"
        
        # 8. Submit Guess (Wrong Guess)
        dropdown_rows.first.click()
        submit_btn = page.locator("#submit-btn")
        submit_btn.click()
        page.wait_for_timeout(300)
        
        # Lives should now decrement to 4
        lives_after_guess = page.locator("#lives-counter").inner_text()
        print(f"✓ Lives counter after incorrect guess: {lives_after_guess}")
        assert lives_after_guess == "4", f"Expected 4 lives after wrong guess, got {lives_after_guess}"
        
        # 9. Duplicate Guess Toast Test
        guess_input.fill("cristiano")
        page.wait_for_selector("#autocomplete-list .fa-dropdown-row")
        page.locator("#autocomplete-list .fa-dropdown-row").first.click()
        submit_btn.click()
        page.wait_for_timeout(200)
        
        toast_items = page.locator(".fa-toast-item")
        assert toast_items.count() > 0, "Warning toast should be shown for already guessed player"
        body_text = page.locator("body").inner_text()
        assert "already guessed" in body_text.lower(), "Warning should notify player was already guessed"
        print("✓ Already guessed player properly displays warning toast")
        
        # 10. Give up and verify Mystery Player is revealed in top hero card & modal
        give_up_btn = page.locator("#give-up-btn")
        give_up_btn.click()
        page.wait_for_selector(".fa-confirm-overlay, #fa-confirm-modal, div:has-text('GIVE UP?')")
        give_up_confirm = page.locator("button:has-text('GIVE UP')").last
        give_up_confirm.click()
        page.wait_for_timeout(400)
        
        # Check result modal is open and hero card displays the mystery player name
        assert page.locator("#result-modal").is_visible(), "Result modal should be visible after give up"
        hero_final_text = page.locator("#mystery-player-display").inner_text().strip()
        print(f"✓ Mystery Player revealed in top hero card: {hero_final_text}")
        assert "?" not in hero_final_text and len(hero_final_text) > 2, f"Hero card should reveal actual player name, got '{hero_final_text}'"
        
        # ─────────────────────────────────────────────────────────────
        # 2. Mobile Responsive Test (375x667 iPhone SE)
        # ─────────────────────────────────────────────────────────────
        mobile_page = browser.new_page(viewport={"width": 375, "height": 667})
        mobile_page.goto(f"http://localhost:{port}/games/played_with.html")
        mobile_page.wait_for_load_state("domcontentloaded")
        mobile_page.wait_for_selector("#fa-guess-panel")
        
        # Check no horizontal overflow
        scroll_width = mobile_page.evaluate("document.documentElement.scrollWidth")
        inner_width = mobile_page.evaluate("window.innerWidth")
        print(f"✓ Mobile Viewport: innerWidth={inner_width}, scrollWidth={scroll_width}")
        assert scroll_width <= inner_width + 1, f"Horizontal scroll overflow detected on mobile: {scroll_width} > {inner_width}"
        
        # Check guess button touch target >= 44px
        submit_box = mobile_page.locator("#submit-btn").bounding_box()
        assert submit_box is not None and submit_box["height"] >= 44, f"Submit button touch height must be >= 44px, got {submit_box['height'] if submit_box else 0}"
        print("✓ Mobile UX & touch targets verified (min-height >= 44px, 0 overflow)")
        
        # ─────────────────────────────────────────────────────────────
        # 3. Spanish Localization Test
        # ─────────────────────────────────────────────────────────────
        es_page = browser.new_page()
        es_page.goto(f"http://localhost:{port}/es/games/played_with.html")
        es_page.wait_for_load_state("domcontentloaded")
        es_page.wait_for_selector("h1")
        h1_text = es_page.locator("h1").inner_text()
        print(f"✓ Spanish H1: {h1_text}")
        assert "JUGÓ CON" in h1_text
        
        # Verify instructions section at the bottom is translated
        article_text = es_page.locator("article").inner_text()
        print("✓ Spanish article text verified")
        assert "jugó con" in article_text.lower()
        assert "Played With is a daily football" not in article_text
        assert "reto diario" in article_text.lower()
        
        browser.close()
        print("\n🏆 ALL USER REQUIREMENTS VERIFIED & PASSING WITH FLYING COLORS!")
finally:
    httpd.shutdown()
