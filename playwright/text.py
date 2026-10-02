# - Simples Dokumenten-Editing + Dokumenten-Versionierung
#     - Anlegen eines neuen Textdokuments
#     - Einpflegen von 10 Absätzen Text
#     - Speichern und Schließen
#     - Dokument erneut öffnen
#     - Validierung ob erwarteter Text enthalten ist
#     - Hinzufügen eines weiteren Paragraphs
#     - Speichern und Schließen
#     - Dokument erneut öffnen
#     - Validierung ob erwarteter Text enthalten ist
#     - Schließen
#     - Dokument auf initiale Version zurücksetzen mit lediglich 10 Absätzen Text
#     - Dokument erneut öffnen
#     - Validierung ob erwarteter Text enthalten ist
#     - Schließen
#     - Löschen aller Dateien - Leeren des Papierkorbs

import re
import signal
import random
import string

from playwright.sync_api import Playwright, sync_playwright, expect

from helper_functions import log_note, get_random_text, login, timeout_handler, user_sleep, wait_and_click, NEW_BUTTON, resource_link

DOMAIN = 'https://cloud.opencloud.test'

text = ['# The Hitchhiker’s Guide to the Galaxy\n\n “The story so far: In the beginning the Universe was created. This has made a lot of people very angry and been widely regarded as a bad move.”\n — Douglas Adams', '\n\n## Overview \n\n *The Hitchhiker’s Guide to the Galaxy* is a comedic science fiction franchise created by Douglas Adams. It began as a BBC radio series and was later adapted into novels, a television series, stage plays, comic books, a computer game, and a feature film.', '\n\n## Series Reading Order \n\n1. **The Hitchhiker’s Guide to the Galaxy**\n2. **The Restaurant at the End of the Universe**\n3. **Life, the Universe and Everything**\n4. **So Long, and Thanks for All the Fish**\n5. **Mostly Harmless**\n\n *Note: The series is often humorously referred to as a "trilogy in five parts."*', '\n\n## Key Characters \n\n- **Arthur Dent**: The bewildered human protagonist.\n- **Ford Prefect**: Arthur’s alien friend and researcher for the Guide.\n- **Zaphod Beeblebrox**: Two-headed, eccentric ex-President of the Galaxy.\n- **Trillian (Tricia McMillan)**: The only other human survivor.\n- **Marvin the Paranoid Android**: A depressed robot with a "brain the size of a planet."', '\n\n## Important Concepts\n\n- **Don’t Panic**: The cover of the Guide is emblazoned with these reassuring words.\n- **Towel**: The most massively useful thing an interstellar hitchhiker can have.\n- **Answer to the Ultimate Question**: 42.\n- **Vogon Poetry**: Universally considered the third worst in the universe.', '\n\n## Origins and Adaptations \n\n- **Radio Series**: The original format, with the first two phases corresponding to the first two books.\n- **Novels**: Five main books, with the first two closely following the radio series.\n- **Computer Game**: 1984 interactive fiction game by Infocom, co-written by Adams.']

check = ['Universe', 'Douglas', 'Fish', 'brain', '42', 'Five']

assert len(text) == len(check), "Text and check lists must have the same length."

# Since web v7 the markdown editor is WYSIWYG (tiptap) instead of CodeMirror. Pressing Enter inside a list already
# starts the next item, so typing the marker again creates a nested empty item that the editor drops on reload.
# Like a user would, we do not type the markers of the following list items. The resulting document is the same.
def wysiwyg_keystrokes(t: str) -> str:
    return re.sub(r'(?<=[^\n])\n(- |\d+\. )', '\n', t)

def run(playwright: Playwright, browser_name: str, headless=False) -> None:
    log_note(f"Launch browser {browser_name}")
    if browser_name == "firefox":
        browser = playwright.firefox.launch(headless=False)

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

        log_note("- Anlegen eines neuen Textdokuments")
        wait_and_click(page, NEW_BUTTON)

        wait_and_click(page, 'button.new-file-btn-md:has-text("Markdown file")')

        file_name = ''.join(random.choices(string.ascii_letters, k=5)) + '.md'
        new_text_input = page.locator('input[value="New file.md"]')
        new_text_input.wait_for()
        new_text_input.fill(file_name)
        page.click('button:has-text("Create")')

        user_sleep()

        # Since web v7 the markdown editor is tiptap (WYSIWYG) instead of CodeMirror
        editor_content_selector = '.oc-text-editor [contenteditable="true"]'
        page.wait_for_selector(editor_content_selector)
        log_note("- Einpflegen von 10 Absätzen Text")
        for i, t in enumerate(text):
            log_note(f"Adding text block {i+1} of {len(text)}")
            page.focus(editor_content_selector)
            page.keyboard.press('Control+End')
            page.type(editor_content_selector, wysiwyg_keystrokes(t), delay=1)
            user_sleep()
            wait_and_click(page, 'button#app-save-action')
            wait_and_click(page, 'button#app-top-bar-close')
            user_sleep()

            wait_and_click(page, resource_link(file_name))
            user_sleep()
            page.wait_for_selector(editor_content_selector)

            expect(page.locator(editor_content_selector)).to_contain_text(check[i])
            log_note(f"All text blocks added successfully in loop {i}")

        wait_and_click(page, 'button#oc-openfile-contextmenu-trigger')
        user_sleep()

        delete_button_selector = 'button.oc-files-actions-delete-trigger:has-text("Delete")'
        wait_and_click(page, delete_button_selector)
        user_sleep()

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