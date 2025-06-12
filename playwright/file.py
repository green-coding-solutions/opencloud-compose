import contextlib
import hashlib
import os
import shutil
import sys
import tempfile
from time import time_ns, sleep
import signal
import random
import string

from playwright.sync_api import Playwright, sync_playwright, expect

from helper_functions import log_note, get_random_text, login, timeout_handler, user_sleep

DOMAIN = 'https://opencloud'

GB_FILE_PATH = '/tmp/repo/downloads/largefile.bin'
HASH_FILE = '/tmp/repo/downloads/hashes.txt'
MOBY_FILE_PATH = '/tmp/repo/downloads/moby-dick.pdf'

USER2 = {
    'username': ''.join(random.choices(string.ascii_letters, k=5)),
    'username_long': ''.join(random.choices(string.ascii_letters, k=5)),
    'email': ''.join(random.choices(string.ascii_letters, k=5)) +'@testing.rofl',
    'password': ''.join(random.choices(string.ascii_letters, k=5)),
}

LARGE_FILE_NAME = ''.join(random.choices(string.ascii_letters, k=5)) + '.bin'
MOBY_FILE_NAME = ''.join(random.choices(string.ascii_letters, k=5)) + '.pdf'

def calculate_sha1(file_path):
    sha1_hash = hashlib.sha1()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b''):
            sha1_hash.update(chunk)
    return sha1_hash.hexdigest()

def load_expected_hashes(hash_file_path):
    expected_hashes = {}
    with open(hash_file_path, 'r') as f:
        for line in f:
            parts = line.strip().split(' *')
            if len(parts) == 2:
                expected_hashes[parts[1]] = parts[0]
    return expected_hashes

def second_user(playwright: Playwright, browser_name: str, headless=False) -> None:
    log_note(f"Launch user2 browser {browser_name}")
    if browser_name == "firefox":
        browser = playwright.firefox.launch(headless=False)
    else:
        browser = playwright.chromium.launch(headless=False, downloads_path=download_path, args=['--disable-gpu', '--disable-software-rasterizer', '--ozone-platform=wayland'])

    context = browser.new_context(ignore_https_errors=True)
    page = context.new_page()

    download_path = '/root/downloads' + USER2['username']
    os.makedirs(download_path, exist_ok=True)
    expected_hashes = load_expected_hashes(HASH_FILE)
    try:
        log_note("Opening login page")
        page.goto(f"{DOMAIN}/")

        log_note("Logging in")
        login(page, domain=DOMAIN, username=USER2['username'], password=USER2['password'])
        user_sleep()

        log_note("Searching")
        search_input_selector = 'div#files-global-search-bar input.oc-search-input'
        search_term = 'Carpet'

        user_sleep()

        page.wait_for_selector(search_input_selector, state='visible')
        page.fill(search_input_selector, search_term)

        user_sleep()

        page.press(search_input_selector, 'Enter')

        page.wait_for_selector('.oc-resource-details ', state='visible')

        user_sleep()

        log_note("Downloading files")

        page.click('a[data-nav-name="files-shares"]')

        context_menu_button_selector = (
            f'tr:has(span.oc-resource-name[data-test-resource-name="{LARGE_FILE_NAME}"]) '
            'button[aria-label="Show context menu"]'
        )

        download_button_selector = (
            'button.oc-files-actions-download-file-trigger:has-text("Download")'
        )

        page.wait_for_selector(context_menu_button_selector, state='visible')
        page.click(context_menu_button_selector)

        with page.expect_download() as download_info:
            page.wait_for_selector(download_button_selector, state='visible')
            page.click(download_button_selector)

            download = download_info.value

            downloaded_large_file_path = os.path.join(download_path, download.suggested_filename)
            download.save_as(downloaded_large_file_path)

            if os.path.exists(downloaded_large_file_path):
                log_note(f"Large file downloaded successfully: {downloaded_large_file_path}")

                calculated_hash = calculate_sha1(downloaded_large_file_path)
                expected_hash = expected_hashes.get('largefile.bin')
                if expected_hash and calculated_hash == expected_hash:
                    log_note(f"Large file hash verified: {calculated_hash}")
                else:
                    raise ValueError(f"Large file hash mismatch! Expected: {expected_hash}, Got: {calculated_hash}")
            else:
                raise FileNotFoundError(f"Large file download failed at {downloaded_large_file_path}")
            user_sleep()

        context_menu_button_selector = (
            f'tr:has(span.oc-resource-name[data-test-resource-name="{MOBY_FILE_NAME}"]) '
            'button[aria-label="Show context menu"]'
        )

        download_button_selector = (
            'button.oc-files-actions-download-file-trigger:has-text("Download")'
        )

        page.wait_for_selector(context_menu_button_selector, state='visible')
        page.click(context_menu_button_selector)

        user_sleep()

        with page.expect_download() as download_info:
            page.wait_for_selector(download_button_selector, state='visible')
            page.click(download_button_selector)

            download = download_info.value

            downloaded_moby_file_path = os.path.join(download_path, download.suggested_filename)
            download.save_as(downloaded_moby_file_path)

            if os.path.exists(downloaded_moby_file_path):
                log_note(f"Moby Dick file downloaded successfully: {downloaded_moby_file_path}")
                calculated_hash = calculate_sha1(downloaded_moby_file_path)
                expected_hash = expected_hashes.get('moby-dick.pdf')
                if expected_hash and calculated_hash == expected_hash:
                    log_note(f"Moby Dick file hash verified: {calculated_hash}")
                else:
                    raise ValueError(f"Moby Dick file hash mismatch! Expected: {expected_hash}, Got: {calculated_hash}")
            else:
                raise FileNotFoundError(f"Moby Dick file download failed at {downloaded_moby_file_path}")

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


def run(playwright: Playwright, browser_name: str, headless=False) -> None:
    log_note(f"Launch browser {browser_name}")
    if browser_name == "firefox":
        browser = playwright.firefox.launch(headless=False)

    else:
        browser = playwright.chromium.launch(headless=False, downloads_path=download_path, args=['--disable-gpu', '--disable-software-rasterizer', '--ozone-platform=wayland'])

    context = browser.new_context(ignore_https_errors=True)
    page = context.new_page()

    try:
        log_note("Opening login page")
        page.goto(f"{DOMAIN}/")

        log_note("Logging in")
        login(page, domain=DOMAIN)
        user_sleep()

        log_note("Create new user")

        page.locator('#_appSwitcherButton').click()

        page.wait_for_selector('a[data-test-id="app.admin-settings.menuItem"]')
        page.click('a[data-test-id="app.admin-settings.menuItem"]')

        user_sleep()

        page.wait_for_selector('a[data-nav-name="admin-settings-users"]')
        page.click('a[data-nav-name="admin-settings-users"]')

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

        user_sleep()

        log_note("Create new space")

        page.click('a[data-nav-name="admin-settings-spaces"]')

        user_sleep()

        page.wait_for_selector('#new-space-menu-btn')
        page.click('#new-space-menu-btn')

        user_sleep()

        new_space_name = ''.join(random.choices(string.ascii_letters, k=5))

        new_space_input = page.locator('input[value="New space"]')
        new_space_input.wait_for()
        new_space_input.fill(new_space_name)

        page.click('button:has-text("Create")')

        user_sleep()

        page.wait_for_selector('[data-test-space-name="' + new_space_name + '"]')
        expect(page.locator('[data-test-space-name="' + new_space_name + '"]')).to_have_count(1)

        log_note("Upload File")

        page.locator('#_appSwitcherButton').click()
        page.wait_for_selector('a[data-test-id="app.files.menuItem"]')
        page.click('a[data-test-id="app.files.menuItem"]')

        user_sleep()

        page.wait_for_selector('button#upload-menu-btn')
        page.click('button#upload-menu-btn')

        user_sleep()

        large_file_path = '/root/' + LARGE_FILE_NAME


        shutil.copyfile(GB_FILE_PATH, large_file_path)

        with page.expect_file_chooser() as fc_info:
            page.wait_for_selector('#files-file-upload-button')
            page.click('#files-file-upload-button')

            file_chooser = fc_info.value

            file_chooser.set_files(large_file_path)

        page.wait_for_selector('div.upload-info-label.upload-info-success:has-text("1 item uploaded")', state='visible')
        page.wait_for_selector('span.oc-resource-name[data-test-resource-name="' + LARGE_FILE_NAME + '"]')

        page.wait_for_selector('button#upload-menu-btn')
        page.click('button#upload-menu-btn')


        with open(MOBY_FILE_PATH, 'rb') as f:
            file_content = f.read()

        file_payload = {
            'name': MOBY_FILE_NAME,
            'mimeType': 'text/plain',
            'buffer': file_content,
        }

        with page.expect_file_chooser() as fc_info:
            page.wait_for_selector('#files-file-upload-button')
            page.click('#files-file-upload-button')

            file_chooser = fc_info.value
            file_chooser.set_files(file_payload)
            user_sleep()


        page.wait_for_selector('span.oc-resource-name[data-test-resource-name="' + MOBY_FILE_NAME + '"]')

        user_sleep()

        log_note('Sharing files')

        moby_share_button_selector = (
            f'tr:has(span.oc-resource-name[data-test-resource-name="{MOBY_FILE_NAME}"]) '
            'button[aria-label="Share"]'
        )
        page.click(moby_share_button_selector)

        user_sleep()

        page.wait_for_selector('#files-share-invite-input')

        page.locator('#files-share-invite-input').fill(USER2['email'])

        user_sleep()

        selector = 'div.files-collaborators-search-user:has-text("' + USER2['email'] + '")'
        page.wait_for_selector(selector)
        page.click(selector)

        user_sleep()

        page.click('#new-collaborators-form-create-button')

        user_sleep()

        page.wait_for_selector(f'span.files-collaborators-collaborator-name:has-text("' + USER2['username_long'] +'")')


        large_share_button_selector = (
            f'tr:has(span.oc-resource-name[data-test-resource-name="{LARGE_FILE_NAME}"]) '
            'button[aria-label="Share"]'
        )
        page.click(large_share_button_selector)

        page.wait_for_selector('#files-share-invite-input')

        page.locator('#files-share-invite-input').fill(USER2['email'])

        user_sleep()

        selector = 'div.files-collaborators-search-user:has-text("' + USER2['email'] + '")'
        page.wait_for_selector(selector)
        page.click(selector)

        user_sleep()

        page.click('#new-collaborators-form-create-button')

        user_sleep()

        page.wait_for_selector(f'span.files-collaborators-collaborator-name:has-text("' + USER2['username_long'] +'")')

        # This will download and check
        second_user(playwright, browser_name, headless)


        log_note("Delete files")
        context_menu_button_selector = (
            f'tr:has(span.oc-resource-name[data-test-resource-name="{LARGE_FILE_NAME}"]) '
            'button[aria-label="Show context menu"]'
        )

        delete_button_selector = (
                'li.context-menu:has(button:has-text("Delete"))'
        )

        page.wait_for_selector(context_menu_button_selector, state='visible')
        page.click(context_menu_button_selector)

        user_sleep()

        page.wait_for_selector(delete_button_selector, state='visible')
        page.click(delete_button_selector)

        user_sleep()

        context_menu_button_selector = (
            f'tr:has(span.oc-resource-name[data-test-resource-name="{MOBY_FILE_NAME}"]) '
            'button[aria-label="Show context menu"]'
        )

        page.wait_for_selector(context_menu_button_selector, state='visible')
        page.click(context_menu_button_selector)

        user_sleep()

        page.wait_for_selector(delete_button_selector, state='visible')
        page.click(delete_button_selector)

        user_sleep()

        page.click('a[data-nav-name="files-trash-overview"]')

        selector = 'a.trash-bin-route:has-text("Personal")'
        page.wait_for_selector(selector, state='visible')
        page.click(selector)


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

    if len(sys.argv) > 1:
        browser_name = sys.argv[1].lower()
        if browser_name not in ["chromium", "firefox"]:
            print("Invalid browser name. Please choose either 'chromium' or 'firefox'.")
            sys.exit(1)
    else:
        browser_name = "firefox"

    with sync_playwright() as playwright:
        run(playwright, browser_name)