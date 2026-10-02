import random
import string
from time import time_ns, sleep
from playwright.sync_api import TimeoutError

# Since web v7 the separate New/Upload/create buttons are merged into one "New" button in the sidebar.
# What it does depends on the app and route (files: create/upload menu, admin users: create user, admin spaces: create space)
NEW_BUTTON = 'button.oc-app-floating-action-button'


def resource_link(name):
    # Files are shown as tiles by default since web v7. A tile has two links (preview and name), so use the first
    return f'a.oc-resource-link:has(span.oc-resource-name[data-test-resource-name="{name}"]) >> nth=0'


def context_menu_button(name):
    # Works in tiles and table view
    return f'button[data-test-context-menu-resource-name="{name}"]'


def login(page, username='admin', password='admin', domain='https://cloud.opencloud.test'):
    page.goto(f"{domain}/login")
    page.locator('#oc-login-username').fill(username)
    page.locator('#oc-login-password').fill(password)
    page.locator('#oc-login-password').press("Enter")


def get_random_text(size_in_bytes)  -> str:
    characters = string.ascii_letters + string.digits
    return ''.join(random.choice(characters) for _ in range(size_in_bytes))

def log_note(message: str) -> None:
    timestamp = str(time_ns())[:16]
    print(f"{timestamp} {message}")


# def close_modal(page) -> None:
#     with contextlib.suppress(TimeoutError):
#         user_sleep() # Sleep to make sure the modal has time to appear before continuing navigation
#         page.locator('#firstrunwizard .modal-container__content button[aria-label=Close]').click(timeout=15_000)


def timeout_handler(signum, frame):
    raise TimeoutError("Page.content() timed out")

def user_sleep(delay=1):
    log_note(f"Sleeping for {delay}s")
    sleep(delay)

def wait_and_click(page, selector, timeout=30_000):
    page.wait_for_selector(selector, timeout=timeout, state='visible')
    page.click(selector)
