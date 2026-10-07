from camoufox.sync_api import Camoufox
import pyautogui
import time
import ctypes


SCREEN_WIDTH = 1536
SCREEN_HEIGHT = 750


# ============================================================
# Coordinate Configuration
# ============================================================

SIGN_IN_TOP = (1495, 127)

USERNAME_POS = (1138, 351)
PASSWORD_POS = (1158, 473)
SIGN_IN = (1190, 604)
EMPTY_SPACE = (1608, 858)
PROFILE_ICON = (1569, 130)
PROFILE_TAB = (1698, 357)

GIFT_CODE = (1592, 612)

CODE_INPUT = (911, 424)
SUBMIT = (1180, 422)
USE = (1189, 652)


# ============================================================
# Use Button Detection
# ============================================================

USE_REGION = (
    1100,
    610,
    1280,
    700
)


def use_button_visible():
    screenshot = pyautogui.screenshot(
        region=(
            USE_REGION[0],
            USE_REGION[1],
            USE_REGION[2] - USE_REGION[0],
            USE_REGION[3] - USE_REGION[1]
        )
    )

    width, height = screenshot.size

    green_pixels = 0

    for y in range(height):
        for x in range(width):
            r, g, b = screenshot.getpixel((x, y))

            if (
                g > 170
                and g > r * 1.15
                and g > b * 1.5
            ):
                green_pixels += 1

    print(
        f"[DETECT] Green pixels: {green_pixels}"
    )

    return green_pixels >= 50


def wait_for_use_button(timeout=10):
    print(
        f"[DETECT] Waiting for Use button "
        f"(timeout={timeout}s)..."
    )

    start_time = time.time()

    while time.time() - start_time < timeout:

        if use_button_visible():
            print("[DETECT] Use button FOUND!")
            return True

        time.sleep(0.25)

    print(
        "[DETECT] Use button NOT found "
        "within timeout."
    )

    return False


# ============================================================
# Mouse / Keyboard Helpers
# ============================================================

def click(position, times=1, delay=0.5):
    x, y = position

    for i in range(times):

        print(
            f"[MOUSE] Click {i + 1}/{times} "
            f"at ({x}, {y})"
        )

        pyautogui.click(x, y)

        if i < times - 1:
            time.sleep(delay)


def move_to(position, duration=0.2):
    x, y = position

    print(
        f"[MOUSE] Moving to "
        f"({x}, {y})"
    )

    pyautogui.moveTo(
        x,
        y,
        duration=duration
    )

def align_camoufox_windows(x=0, y=0):
    """
    Move all visible Camoufox/Firefox windows to the same
    screen position so PyAutoGUI coordinates remain aligned.
    """

    user32 = ctypes.windll.user32

    EnumWindowsProc = ctypes.WINFUNCTYPE(
        ctypes.c_bool,
        ctypes.c_void_p,
        ctypes.c_void_p
    )

    windows = []

    def callback(hwnd, lParam):
        if not user32.IsWindowVisible(hwnd):
            return True

        class_name = ctypes.create_unicode_buffer(256)
        user32.GetClassNameW(hwnd, class_name, 256)

        # Firefox / Camoufox top-level window
        if class_name.value == "MozillaWindowClass":
            windows.append(hwnd)

        return True

    user32.EnumWindows(EnumWindowsProc(callback), 0)

    for hwnd in windows:
        user32.SetWindowPos(
            hwnd,
            0,
            x,
            y,
            0,
            0,
            0x0001 | 0x0004 | 0x0010
        )

def type_at(position, text):
    x, y = position

    print(
        f"[MOUSE] Clicking input "
        f"at ({x}, {y})"
    )

    pyautogui.click(x, y)

    time.sleep(0.3)

    print("[KEYBOARD] Typing...")

    pyautogui.write(
        text,
        interval=0.03
    )

def browser_click(page, position):
    x, y = position

    print(f"[BROWSER] Clicking at ({x}, {y})")
    page.mouse.click(x, y)


def browser_type(page, position, text):
    x, y = position

    print(f"[BROWSER] Clicking input at ({x}, {y})")
    page.mouse.click(x, y)

    time.sleep(0.3)

    print("[BROWSER] Typing...")
    page.keyboard.type(text)

def pause(seconds=2):
    print(
        f"[WAIT] {seconds} seconds..."
    )

    time.sleep(seconds)


# ============================================================
# Prepared Account Registry
#
# IMPORTANT:
# Camoufox / Playwright sync objects NEVER leave this worker.
#
# account_id -> {
#     "browser": browser,
#     "page": page,
#     "username": username
# }
# ============================================================
worker_browser = None
prepared_accounts = {}


# ============================================================
# Prepare Account
# ============================================================

def get_worker_browser():
    """
    Get the single Camoufox browser owned by this worker.

    IMPORTANT:
    This function must only be called from the worker thread.
    """

    global worker_browser

    if worker_browser is not None:
        return worker_browser

    print("[BROWSER] Starting shared Camoufox...")

    worker_browser = Camoufox(
        headless=False,
        humanize=True,
        window=(SCREEN_WIDTH, SCREEN_HEIGHT)
    ).start()

    print("[BROWSER] Shared Camoufox started.")

    return worker_browser

def prepare_account(
    account_id,
    url,
    username,
    password
):
    """
    Opens Camoufox, logs into the account,
    navigates to the Gift Code section,
    and keeps the browser/page alive inside
    this worker.

    IMPORTANT:
    The browser and page objects remain inside
    this worker registry. They are NOT returned
    to the asyncio side.
    """

    print("=" * 60)

    print(
        f"[PREPARE] Starting account: "
        f"{username}"
    )

    print("=" * 60)

    screen_size = pyautogui.size()

    print(
        f"[SCREEN] Detected: "
        f"{screen_size.width} x "
        f"{screen_size.height}"
    )

    if (
        screen_size.width != SCREEN_WIDTH
        or screen_size.height != SCREEN_HEIGHT
    ):
        print(
            "[WARNING] Screen resolution "
            "does not match configuration!"
        )

    try:
        browser = get_worker_browser()

        print(
            f"[BROWSER] Creating context for "
            f"account {account_id}..."
        )

        context = browser.new_context(
            viewport={
                "width": SCREEN_WIDTH,
                "height": SCREEN_HEIGHT,
            }
        )

        page = context.new_page()

        time.sleep(0.5)

        align_camoufox_windows(0, 0)

        page.bring_to_front()

        # ====================================================
        # 1. Open Website
        # ====================================================

        print(f"[1] Opening: {url}")

        page.goto(
            url,
            wait_until="domcontentloaded",
            timeout=120000
        )

        print("[1] Website loaded.")

        pause(13)

        # ====================================================
        # 2. Open Sign-in
        # ====================================================

        print(
            "[2] Closing popup / "
            "opening Sign-in..."
        )

        click(
            SIGN_IN_TOP,
            times=2,
            delay=0.5
        )

        time.sleep(0.5)

        # ====================================================
        # 3. Username
        # ====================================================

        print(
            "[3] Entering username..."
        )

        type_at(
            USERNAME_POS,
            username
        )

        time.sleep(0.5)

        # ====================================================
        # 4. Password
        # ====================================================

        print(
            "[4] Entering password..."
        )

        type_at(
            PASSWORD_POS,
            password
        )

        time.sleep(0.15)

        # ====================================================
        # 5. Login
        # ====================================================

        print("[5] Clicking Login...")

        click(SIGN_IN)

        time.sleep(2.25)

        # ====================================================
        # 6. Close Login Popup + Open Profile
        # ====================================================

        print(
            "[6] Closing post-login popup..."
        )
        
        click((1175, 170))

        time.sleep(0.35)

        print(
            "[6] Opening profile menu..."
        )

        click(EMPTY_SPACE)
        time.sleep(0.15)
        
        click(PROFILE_ICON)
        time.sleep(0.15)

        # ====================================================
        # 7. Profile Tab
        # ====================================================

        print(
            "[7] Moving to Profile tab..."
        )

        move_to(PROFILE_TAB)

        time.sleep(0.15)

        # ====================================================
        # 8. Scroll
        # ====================================================

        print(
            "[8] Scrolling to bottom..."
        )

        pyautogui.scroll(-1000)

        time.sleep(0.5)

        # ====================================================
        # 9. Gift Code
        # ====================================================

        print(
            "[9] Opening Gift Code..."
        )

        click(GIFT_CODE)

        time.sleep(0.5)

        # ====================================================
        # Store Browser Internally
        # ====================================================

        prepared_accounts[account_id] = {
            "browser": context,
            "page": page,
            "username": username
        }

        print("=" * 60)

        print(
            f"[PREPARE] ACCOUNT READY: "
            f"{username}"
        )

        print(
            f"[PREPARE] Account ID: "
            f"{account_id}"
        )

        print(
            "[PREPARE] Browser remains open "
            "inside worker registry."
        )

        print("=" * 60)

        return {
            "success": True,
            "username": username,
            "error_code": None,
            "error_message": None
        }

    except Exception as error:

        print("=" * 60)

        print(
            f"[PREPARE] ERROR for "
            f"{username}"
        )

        print(
            f"[PREPARE] "
            f"{type(error).__name__}: "
            f"{error}"
        )

        print("=" * 60)

        try:
            if "context" in locals() and context:
                context.close()
        except Exception as close_error:
            print(
                f"[PREPARE] Context cleanup error: "
                f"{type(close_error).__name__}: "
                f"{close_error}"
            )

        prepared_accounts.pop(account_id, None)

        return {
            "success": False,
            "username": username,
            "error_code": type(error).__name__,
            "error_message": str(error)
        }


# ============================================================
# Redeem Code
# ============================================================

def submit_code(
    account_id,
    username,
    code
):

    print("=" * 60)
    print(
        f"[SUBMIT] Submitting code "
        f"for {username}"
    )
    print("=" * 60)

    account = prepared_accounts.get(account_id)

    if not account:
        return {
            "success": False,
            "username": username,
            "error_code": "ACCOUNT_NOT_FOUND",
            "error_message": "Prepared account was not found."
        }

    page = account["page"]

    try:
        # ====================================================
        # 1. Bring Account Forward
        # ====================================================

        page.bring_to_front()
        time.sleep(0.15)

        # ====================================================
        # 2. Enter Code
        # ====================================================       
        
        print("[1] Entering redeem code...")
        click(
            CODE_INPUT,
            times=1,
            delay=0.1
        )
        
        type_at(
            CODE_INPUT,
            code
        )

        time.sleep(0.10)

        # ====================================================
        # 3. Submit
        # ====================================================

        print("[2] Clicking Submit...")

        click(SUBMIT)

        time.sleep(0.10)

        # ====================================================
        # Submitted Successfully
        # ====================================================

        print("=" * 60)
        print("[SUBMIT] Code submitted.")
        print(f"[SUBMIT] Account: {username}")
        print("=" * 60)

        return {
            "success": True,
            "username": username,
            "error_code": None,
            "error_message": None
        }

    except Exception as error:

        print("=" * 60)
        print(
            f"[SUBMIT] ERROR for "
            f"{username}"
        )

        print(
            f"[SUBMIT] "
            f"{type(error).__name__}: "
            f"{error}"
        )

        print("=" * 60)

        return {
            "success": False,
            "username": username,
            "error_code": type(error).__name__,
            "error_message": str(error)
        }


def confirm_code(
    account_id,
    username
):
    """
    Detects the Use button and clicks it.

    This is the second pass after all accounts
    have already submitted their code.
    """

    print("=" * 60)
    print(
        f"[CONFIRM] Checking code "
        f"for {username}"
    )
    print("=" * 60)

    account = prepared_accounts.get(account_id)

    if not account:
        return {
            "success": False,
            "username": username,
            "error_code": "ACCOUNT_NOT_FOUND",
            "error_message": "Prepared account was not found."
        }

    page = account["page"]

    try:
        # ====================================================
        # 1. Bring Account Forward
        # ====================================================

        page.bring_to_front()
        time.sleep(0.15)

        # ====================================================
        # 2. Detect Use Button
        # ====================================================

        print(
            "[1] Checking whether "
            "code was accepted..."
        )

        use_found = wait_for_use_button(
            timeout=10
        )

        if not use_found:

            print("=" * 60)
            print("[RESULT] CODE FAILED")
            print(f"[RESULT] Account: {username}")
            print("=" * 60)

            return {
                "success": False,
                "username": username,
                "error_code": "CODE_FAILED",
                "error_message":
                    "Use button was not detected."
            }

        # ====================================================
        # 3. Click Use
        # ====================================================

        pyautogui.click(USE[0], USE[1])
        time.sleep(0.15)

        # ====================================================
        # Success
        # ====================================================

        print("=" * 60)
        print("[RESULT] SUCCESS")
        print(f"[RESULT] Account: {username}")
        print("=" * 60)

        return {
            "success": True,
            "username": username,
            "error_code": None,
            "error_message": None
        }

    except Exception as error:

        print("=" * 60)
        print(
            f"[CONFIRM] ERROR for "
            f"{username}"
        )

        print(
            f"[CONFIRM] "
            f"{type(error).__name__}: "
            f"{error}"
        )

        print("=" * 60)

        return {
            "success": False,
            "username": username,
            "error_code": type(error).__name__,
            "error_message": str(error)
        }
# ============================================================
# Close Account
# ============================================================

def close_account(account_id):
    """
    Closes only the browser context belonging to one account.

    The shared Camoufox browser remains alive while other
    accounts are still prepared.
    """

    account = prepared_accounts.pop(account_id, None)

    if not account:
        print(
            f"[CLOSE] Account {account_id} "
            f"not found."
        )
        return

    context = account.get("browser")

    if context is None:
        return

    try:

        print(
            f"[CLOSE] Closing account "
            f"{account_id} context..."
        )

        context.close()

        print(
            f"[CLOSE] Account {account_id} "
            f"context closed."
        )

    except Exception as error:

        print(
            f"[CLOSE] Error closing account "
            f"{account_id}: "
            f"{type(error).__name__}: {error}"
        )

# ============================================================
# Close Shared Browser
# ============================================================

def close_worker_browser():
    """
    Closes all prepared account contexts and then
    shuts down the shared Camoufox browser.
    """

    global worker_browser

    print("[BROWSER] Shutting down worker browser...")

    # Close remaining account contexts
    for account_id in list(prepared_accounts.keys()):
        close_account(account_id)

    if worker_browser is not None:

        try:
            worker_browser.stop()

            print(
                "[BROWSER] Shared Camoufox closed."
            )

        except Exception as error:

            print(
                f"[BROWSER] Error stopping Camoufox: "
                f"{type(error).__name__}: {error}"
            )

        finally:
            worker_browser = None

# ============================================================
# Close All Accounts
# ============================================================

def close_all_accounts():
    close_worker_browser()