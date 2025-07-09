# - Document Editing (Collaborative)
#     - Anlegen eines neuen Nutzers (User #2)
#     - Erstellen eines .odt Dokuments
#     - Sharing des Dokuments mit User #2
#     - Einpflegen von 10 Absätzen Text durch User #1
#     - Öffnen des Links durch User #2
#         - Validierung ob erwarteter Text enthalten ist
#         - Einpflegen von weiteren 2 Absätzen Text
#     - Validierung durch User #1 ob erwarteter Text enthalten ist

from pathlib import Path
import signal
import random
import string
import os
from playwright.sync_api import Playwright, sync_playwright, expect
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from helper_functions import log_note, get_random_text, login, timeout_handler, user_sleep, wait_and_click

DOMAIN = 'https://opencloud'
WRITE_DELAY = 0#1

text = ['# The Hitchhiker’s Guide to the Galaxy\n\n “The story so far: In the beginning the Universe was created. This has made a lot of people very angry and been widely regarded as a bad move.”\n — Douglas Adams', '\n\n## Overview \n\n *The Hitchhiker’s Guide to the Galaxy* is a comedic science fiction franchise created by Douglas Adams. It began as a BBC radio series and was later adapted into novels, a television series, stage plays, comic books, a computer game, and a feature film.', '\n\n## Series Reading Order \n\n1. **The Hitchhiker’s Guide to the Galaxy**\n2. **The Restaurant at the End of the Universe**\n3. **Life, the Universe and Everything**\n4. **So Long, and Thanks for All the Fish**\n5. **Mostly Harmless**\n\n *Note: The series is often humorously referred to as a "trilogy in five parts."*', '\n\n## Key Characters \n\n- **Arthur Dent**: The bewildered human protagonist.\n- **Ford Prefect**: Arthur’s alien friend and researcher for the Guide.\n- **Zaphod Beeblebrox**: Two-headed, eccentric ex-President of the Galaxy.\n- **Trillian (Tricia McMillan)**: The only other human survivor.\n- **Marvin the Paranoid Android**: A depressed robot with a "brain the size of a planet."', '\n\n## Important Concepts\n\n- **Don’t Panic**: The cover of the Guide is emblazoned with these reassuring words.\n- **Towel**: The most massively useful thing an interstellar hitchhiker can have.\n- **Answer to the Ultimate Question**: 42.\n- **Vogon Poetry**: Universally considered the third worst in the universe.', '\n\n## Origins and Adaptations \n\n- **Radio Series**: The original format, with the first two phases corresponding to the first two books.\n- **Novels**: Five main books, with the first two closely following the radio series.\n- **Computer Game**: 1984 interactive fiction game by Infocom, co-written by Adams.']
check = ['Universe', 'Douglas', 'Fish', 'brain', '42', 'Five']

assert len(text) == len(check), "Text and check lists must have the same length."

text2= ['''(Men) So long,
and thanks for all the fish,
So sad that it should come to this,
We tried to warn you all, but oh dear...
You may not share our intellect,
Which might explain your disrespect,
For all the natural wonders,
that grow a-round you!
So long, So long, and
thanks, for all the fish...''',
'''(Women)The worlds about to be destroyed,
Theres no point getting all annoyed,
Lie back and let the planet dissolve
around you,
''']
check2 = ['fish', 'planet']
assert len(text2) == len(check2), "Text2 and check2 lists must have the same length."


file_name = ''.join(random.choices(string.ascii_letters, k=5)) + '.odt'

USER2 = {
    'username': ''.join(random.choices(string.ascii_letters, k=5)),
    'username_long': ''.join(random.choices(string.ascii_letters, k=5)),
    'email': ''.join(random.choices(string.ascii_letters, k=5)) +'@testing.rofl',
    'password': ''.join(random.choices(string.ascii_letters, k=5)),
}


def second_user(playwright: Playwright, browser_name: str, headless=False) -> None:
    log_note(f"Launch user2 browser {browser_name}")
    if browser_name == "firefox":
        browser = playwright.firefox.launch(headless=True)
    # else:
    #     browser = playwright.chromium.launch(headless=False, downloads_path=download_path, args=['--disable-gpu', '--disable-software-rasterizer', '--ozone-platform=wayland'])

    context = browser.new_context(ignore_https_errors=True, viewport={"width": 1280, "height": 720})

    page = context.new_page()

    download_path = '/root/downloads' + USER2['username']
    os.makedirs(download_path, exist_ok=True)
    try:
        log_note("Opening login page")
        page.goto(f"{DOMAIN}/")

        log_note("Logging in")
        login(page, domain=DOMAIN, username=USER2['username'], password=USER2['password'])
        user_sleep()

        page.get_by_role("link", name="Shares").click()

        page.locator('a[href*="' + file_name + '"]').first.click()

        log_note("- Öffnen des Links durch User #2")

        iframe_element = page.wait_for_selector("iframe[name='app-iframe']")
        frame = iframe_element.content_frame()

        # log_note(f"Frame 1: {frame}")

        # iframe_el = page.query_selector("iframe[name='app-iframe']")
        # frame = iframe_el.content_frame()

        # log_note(f"Frame 2: {frame}")

        # print("=== frames after load ===")
        # for f in page.frames:
        #     print(f.name, f.url)

        # user_sleep(100000)
        frame.wait_for_load_state("domcontentloaded")

        try:
            log_note("Waiting for welcome modal to appear")

            frame.wait_for_selector("iframe[name='iframe-welcome-form']")

            #iFrame in iFrame ;)
            wframe = frame.frame_locator("iframe[name='iframe-welcome-form']")
            #wframe.wait_for_load_state("domcontentloaded")

            wframe.locator("#user-welcome").wait_for(timeout=5_000)

            log_note("Welcome modal appeared, closing it")

            wframe.get_by_role("button", name="Close").click()

        except PlaywrightTimeoutError:
           pass

        editor_content_selector = '#canvas-container'
        frame.wait_for_selector(editor_content_selector)

        user_sleep()

        log_note("- Validierung ob erwarteter Text enthalten ist")
        with frame.page.expect_download() as download_info:
            log_note("Checking if the text that user1 added is present in the document")
            wait_and_click(frame, 'button#File-tab-label')
            wait_and_click(frame, 'button#downloadas-button')
            wait_and_click(frame, 'div.ui-combobox-entry:has-text("HTML File")')

        download = download_info.value
        rnd_file_name = ''.join(random.choices(string.ascii_letters, k=10)) + '.html'
        final_path = Path("/tmp") / rnd_file_name
        download.save_as(final_path)
        content = final_path.read_text(encoding="utf-8", errors="ignore")

        for word in check:
            if not word in content:
                raise Exception(f"Expected word '{word}' not found in text: {content}")

        user_sleep()

        log_note("- Einpflegen von weiteren 2 Absätzen Text")
        frame.locator(editor_content_selector).focus()
        frame.locator('#map').click()

        # log_note("Checking if the text that user1 added is present in the document")
        # frame.page.keyboard.press("Control+A")  # Use "Meta+C" on macOS
        # frame.page.keyboard.press("Control+C")  # Use "Meta+C" on macOS
        # clipboard_text = page.evaluate(
        #     """async () => await navigator.clipboard.readText()"""
        # )
        # for word in check:
        #     if not word in clipboard_text:
        #         raise Exception(f"Expected word '{word}' not found in clipboard text: {clipboard_text}")


        for i, t in enumerate(text2):
            log_note(f"Adding text block {i+1} of {len(text)}")
            frame.page.keyboard.type(t, delay=WRITE_DELAY)
            frame.page.keyboard.press('Enter')
            frame.page.keyboard.press('Enter')
            frame.page.keyboard.press('Control+End')

            user_sleep()

        log_note(f"All text blocks added successfully")

        wait_and_click(frame, 'button#save-button')

        page.close()
        log_note("Close browser")

    except Exception as e:
        if hasattr(e, 'message'): # only Playwright error class has this member
            log_note(f"Exception occurred: {e.message}")

        # set a timeout. Since the call to page.content() is blocking we need to defer it to the OS
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(20)
        #log_note(f"Page content was: {page.content()}")
        signal.alarm(0) # remove timeout signal

        raise e

    # ---------------------
    context.close()
    browser.close()


def run(playwright: Playwright, browser_name: str, headless=False) -> None:
    log_note(f"Launch browser {browser_name}")
    if browser_name == "firefox":
        browser = playwright.firefox.launch(headless=True)

    # else:
    #     browser = playwright.chromium.launch(headless=False, downloads_path=download_path, args=['--disable-gpu', '--disable-software-rasterizer', '--ozone-platform=wayland'])

    context = browser.new_context(ignore_https_errors=True, viewport={"width": 1280, "height": 720})
    page = context.new_page()

    try:
        log_note("Opening login page")
        page.goto(f"{DOMAIN}/")

        log_note("Logging in")
        login(page, domain=DOMAIN)
        user_sleep()

        log_note("- Anlegen eines neuen Nutzers (User #2)")

        page.locator('#_appSwitcherButton').click()

        wait_and_click(page, 'a[data-test-id="app.admin-settings.menuItem"]')

        user_sleep()

        wait_and_click(page, 'a[data-nav-name="admin-settings-users"]')

        user_sleep()

        page.wait_for_selector('#create-user-btn')
        page.click('#create-user-btn')

        user_sleep()

        page.locator('#create-user-input-user-name').fill(USER2['username'])
        page.locator('#create-user-input-display-name').fill(USER2['username_long'])
        page.locator('#create-user-input-email').fill(USER2['email'])
        page.locator('#create-user-input-password').fill(USER2['password'])
        page.locator('#create-user-input-password').press("Enter")

        user_sleep()

        user_selector = 'td.oc-table-data-cell-onPremisesSamAccountName:has-text("' + USER2['username'] + '")'
        page.wait_for_selector(user_selector)

        page.locator('#_appSwitcherButton').click()

        wait_and_click(page, 'a[data-test-id="app.files.menuItem"]')

        user_sleep()


        log_note("- Erstellen eines .odt Dokuments")
        wait_and_click(page, 'button#new-file-menu-btn:has-text("New")')

        wait_and_click(page, 'button:has-text("OpenDocument")')


        new_text_input = page.locator('input[value="New file.odt"]')
        new_text_input.wait_for()
        new_text_input.fill(file_name)
        page.click('button:has-text("Create")')

        page.wait_for_selector("iframe[name='app-iframe']")


        iframe_element = page.wait_for_selector("iframe[name='app-iframe']")
        frame = iframe_element.content_frame()

        frame.wait_for_load_state("domcontentloaded")  # or "load" if you prefer

        try:
            log_note("Waiting for welcome modal to appear")

            frame.wait_for_selector("iframe[name='iframe-welcome-form']")

            #iFrame in iFrame ;)
            wframe = frame.frame_locator("iframe[name='iframe-welcome-form']")
            #wframe.wait_for_load_state("domcontentloaded")

            wframe.locator("#user-welcome").wait_for(timeout=5_000)

            log_note("Welcome modal appeared, closing it")

            wframe.get_by_role("button", name="Close").click()

        except PlaywrightTimeoutError:
           pass

        user_sleep()

        log_note("- Einpflegen von 10 Absätzen Text durch User #1")
        editor_content_selector = '#canvas-container'
        frame.wait_for_selector(editor_content_selector)
        frame.locator(editor_content_selector).focus()
        frame.locator('#map').click()
        frame.page.keyboard.press('Control+End')
        frame.page.keyboard.press('Enter')
        frame.page.keyboard.press('Enter')

        for i, t in enumerate(text):
            log_note(f"Adding text block {i+1} of {len(text)}")
            frame.page.keyboard.type(t, delay=WRITE_DELAY)
            frame.page.keyboard.press('Enter')
            frame.page.keyboard.press('Enter')

            user_sleep()

        log_note(f"All text blocks added successfully")
        wait_and_click(frame, 'button#save-button')
        wait_and_click(page, 'button#oc-openfile-contextmenu-trigger')
        wait_and_click(page, 'button:has-text("Share")')

        log_note("- Sharing des Dokuments mit User #2")
        page.wait_for_selector('#files-share-invite-input')

        page.locator('#files-share-invite-input').fill(USER2['email'])

        user_sleep()

        selector = 'div.files-collaborators-search-user:has-text("' + USER2['email'] + '")'
        page.wait_for_selector(selector)
        page.click(selector)

        user_sleep()

        wait_and_click(page, 'button#files-collaborators-role-button-new')
        button=page.locator("button", has_text="Can edit")
        button.wait_for()
        button.click()

        page.click('#new-collaborators-form-create-button')

        user_sleep()

        page.wait_for_selector(f'span.files-collaborators-collaborator-name:has-text("' + USER2['username_long'] +'")')

        # This will download and check
        second_user(playwright, browser_name, headless)

        user_sleep(5)

        log_note("- Validierung durch User #1 ob erwarteter Text enthalten ist")
        with frame.page.expect_download() as download_info:
            log_note("Checking if the text that user2 added is present in the document")
            wait_and_click(frame, 'button#File-tab-label')
            wait_and_click(frame, 'button#downloadas-button')
            wait_and_click(frame, 'div.ui-combobox-entry:has-text("HTML File")')

        download = download_info.value
        rnd_file_name = ''.join(random.choices(string.ascii_letters, k=10)) + '.html'
        final_path = Path("/tmp") / rnd_file_name
        download.save_as(final_path)
        content = final_path.read_text(encoding="utf-8", errors="ignore")

        for word in check2:
            if not word in content:
                raise Exception(f"Expected word '{word}' not found in text: {content}")
        user_sleep()
        # wait_and_click(page, 'button#oc-openfile-contextmenu-trigger')
        # user_sleep()

        # delete_button_selector = 'button.oc-files-actions-delete-trigger:has-text("Delete")'
        # wait_and_click(page, delete_button_selector)
        # user_sleep()

        page.close()
        log_note("Close browser")

    except Exception as e:
        if hasattr(e, 'message'): # only Playwright error class has this member
            log_note(f"Exception occurred: {e.message}")

        # set a timeout. Since the call to page.content() is blocking we need to defer it to the OS
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(20)
        #log_note(f"Page content was: {page.content()}")
        signal.alarm(0) # remove timeout signal

        raise e

    # ---------------------
    context.close()
    browser.close()


if __name__ == "__main__":

    # if len(sys.argv) > 1:
    #     browser_name = sys.argv[1].lower()
    #     if browser_name not in ["chromium", "firefox"]:
    #         print("Invalid browser name. Please choose either 'chromium' or 'firefox'.")
    #         sys.exit(1)
    # else:
    #     browser_name = "firefox"

    with sync_playwright() as playwright:
        run(playwright, "firefox")