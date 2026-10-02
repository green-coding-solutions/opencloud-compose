# - Bilder-Verwaltung
#     - Anlegen eines neuen Spaces inkl. Beschreibung
#     - Hochladen von 10 Bildern
#     - Vorschau (Preview-Service) der Bilder
#         - Implizit: Search Indexing with Tika
#     - Löschen aller Dateien - Leeren des Papierkorbs

import signal
import random
import string

from playwright.sync_api import Playwright, sync_playwright, expect

from helper_functions import log_note, get_random_text, login, timeout_handler, user_sleep, NEW_BUTTON, resource_link

DOMAIN = 'https://cloud.opencloud.test'

DOWNLOAD_DIR = '/tmp/repo-copy/downloads/'

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

        log_note("- Anlegen eines neuen Spaces inkl. Beschreibung")
        page.locator('#_appSwitcherButton').click()

        user_sleep()

        page.wait_for_selector('a[data-test-id="app.admin-settings.menuItem"]')
        page.click('a[data-test-id="app.admin-settings.menuItem"]')

        user_sleep()
        page.wait_for_selector('a[data-nav-name="admin-settings-spaces"]')
        page.click('a[data-nav-name="admin-settings-spaces"]')
        page.wait_for_url('**/admin-settings/spaces**')

        page.wait_for_selector(NEW_BUTTON)
        page.click(NEW_BUTTON)

        new_space_name = ''.join(random.choices(string.ascii_letters, k=5))

        new_space_input = page.locator('input[value="New space"]')
        new_space_input.wait_for()
        new_space_input.fill(new_space_name)

        page.click('button:has-text("Create")')

        user_sleep()

        page.wait_for_selector('[data-test-space-name="' + new_space_name + '"]')
        expect(page.locator('[data-test-space-name="' + new_space_name + '"]')).to_have_count(1)

        log_note("- Hochladen von 10 Bildern ")

        page.locator('#_appSwitcherButton').click()
        page.wait_for_selector('a[data-test-id="app.files.menuItem"]')
        page.click('a[data-test-id="app.files.menuItem"]')

        user_sleep()

        spaces_link_selector = 'a[data-nav-name="files-spaces-projects"]'
        page.wait_for_selector(spaces_link_selector, state='visible')
        page.click(spaces_link_selector)

        user_sleep()

        selector = (
            f'div.oc-tile-card:has(span.oc-resource-name[data-test-resource-name="{new_space_name}"])'
        )

        page.wait_for_selector(selector, state='visible')
        page.locator(selector).click()

        random_filenames= {}

        for i in range(10):
            random_filename = ''.join(random.choices(string.ascii_letters, k=5)) + '.png'
            random_filenames[i] = random_filename

        all_file_payloads = []

        for i in range(10):
            local_source_file_path = f"{DOWNLOAD_DIR}{i}.png"

            with open(local_source_file_path, 'rb') as f:
                file_content = f.read()

            file_payload = {
                'name': random_filenames[i],
                'mimeType': 'image/png',
                'buffer': file_content,
            }
            all_file_payloads.append(file_payload)

        page.wait_for_selector(NEW_BUTTON)
        page.click(NEW_BUTTON)

        with page.expect_file_chooser() as fc_info:
            file_upload_button_selector = '#files-file-upload-button'
            page.wait_for_selector(file_upload_button_selector, state='visible')
            page.click(file_upload_button_selector)

            file_chooser = fc_info.value
            file_chooser.set_files(all_file_payloads)

        user_sleep(5)

        # The default tiles view is already sorted by name

        log_note("- Vorschau (Preview-Service) der Bilder")
        for filename in sorted(random_filenames.values()):
            locator = page.locator(
                f'span.oc-resource-name[data-test-resource-name="{filename}"]'
            )
            locator.scroll_into_view_if_needed()
            expect(locator).to_be_visible(timeout=5_000)

            log_note(f"Confirmed visibility of uploaded file: {filename}")


        log_note("- Löschen aller Dateien - Leeren des Papierkorbs")

        select_all_checkbox_selector = 'input#tiles-view-select-all[type="checkbox"]'
        page.wait_for_selector(select_all_checkbox_selector, state='visible')
        page.click(select_all_checkbox_selector)

        user_sleep()

        delete_button_selector = 'button.oc-files-actions-delete-trigger:has-text("Delete")'
        page.wait_for_selector(delete_button_selector, state='visible')
        page.click(delete_button_selector)

        user_sleep()

        page.click('a[data-nav-name="files-trash-overview"]')

        user_sleep()

        selector = resource_link(new_space_name)
        page.wait_for_selector(selector, state='visible')
        page.click(selector)

        user_sleep()

        selector = 'button.oc-files-actions-empty-trash-bin-trigger:has-text("Empty trash bin")'
        page.wait_for_selector(selector, state='visible')
        page.click(selector)

        user_sleep()

        selector = 'button.oc-modal-body-actions-confirm:has-text("Delete")'
        page.wait_for_selector(selector, state='visible')
        page.click(selector)

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