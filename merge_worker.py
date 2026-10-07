import time
import pyautogui
import cv2
import numpy as np
from camoufox.sync_api import Camoufox

from worker.camoufox_worker import align_camoufox_windows

SIGN_IN_TOP = (1495, 127)
USERNAME_POS = (1138, 351)
PASSWORD_POS = (1158, 473)
SIGN_IN = (1190, 604)
SCREEN_WIDTH = 1536
SCREEN_HEIGHT = 750

# Fan Tan betting coordinates
BET_CHIP_10 = (823, 970)
BET_CHIP_25 = (881, 970)
BET_CHIP_50 = (934, 970)
BET_CHIP_250 = (987, 970)

ODD_BET = (742, 784)
EVEN_BET = (1220, 784)

BET_CLICK_DELAY = 0.08
MERGE_MIN_BET = 10

# Countdown ring region (screen coordinates)
COUNTDOWN_REGION = (737, 351, 456, 257)
OPEN_GREEN_PIXEL_THRESHOLD = 200
CLOSE_GREEN_PIXEL_THRESHOLD = 10
OPEN_CONFIRMATION_TIME = 0.30
CLOSE_CONFIRMATION_TIME = 0.80

GAME_URL = (
    "https://luckyxwire.org/game/450"
    "?type=8"
    "&p=xhM535"
    "&gameType=8"
    "&gid=110037"
    "&pid=4"
)

class MergeWorker:

    def __init__(self):
        self.browser = None
        self.accounts = {}


    def start_browser(self):
        if self.browser is not None:
            return

        self.browser = Camoufox(
            headless=False,
            humanize=True,
            window=(SCREEN_WIDTH, SCREEN_HEIGHT)
        ).start()

    def open_account(self, account_id, username, url):
        """
        Opens one account in its own browser context/page.
        """

        if self.browser is None:
            self.start_browser()

        context = self.browser.new_context(
            viewport={
                "width": SCREEN_WIDTH,
                "height": SCREEN_HEIGHT
            }
        )

        page = context.new_page()
        time.sleep(0.15)
        align_camoufox_windows(0, 0)

        page.bring_to_front()

        page.goto(
            url,
            wait_until="domcontentloaded",
            timeout=120000
        )
        time.sleep(8)

        self.accounts[account_id] = {
            "username": username,
            "context": context,
            "page": page
        }

        return {
            "success": True,
            "account_id": account_id,
            "username": username
        }


    def login_account(
        self,
        account_id,
        password
    ):
        """
        Logs into an already-open Merge account
        and navigates it to the 
        Fan Tan game.
        """

        account = self.accounts.get(account_id)

        if not account:
            return {
                "success": False,
                "error": "Account not found."
            }

        page = account["page"]
        username = account["username"]

        print(
            f"[MERGE] Logging in: {username}"
        )

        try:

            # -------------------------
            # Open Sign-in
            # -------------------------

            page.bring_to_front()
            time.sleep(0.15)
            
            pyautogui.click(
                SIGN_IN_TOP[0],
                SIGN_IN_TOP[1],
                clicks=2,
                interval=0.5
            )

            time.sleep(1)

            # -------------------------
            # Username
            # -------------------------

            pyautogui.click(
                USERNAME_POS[0],
                USERNAME_POS[1]
            )

            pyautogui.write(
                username,
                interval=0.03
            )

            time.sleep(0.25)

            # -------------------------
            # Password
            # -------------------------

            pyautogui.click(
                PASSWORD_POS[0],
                PASSWORD_POS[1]
            )

            pyautogui.write(
                password,
                interval=0.03
            )

            time.sleep(0.15)

            # -------------------------
            # Login
            # -------------------------

            pyautogui.click(
                SIGN_IN[0],
                SIGN_IN[1]
            )

            time.sleep(1)

            # -------------------------
            # Go directly to Fan Tan
            # -------------------------

            page.goto(
                GAME_URL,
                wait_until="domcontentloaded",
                timeout=120000
            )

            time.sleep(3)

            print(
                f"[MERGE] Game opened: {username}"
            )

            return {
                "success": True,
                "account_id": account_id,
                "username": username
            }

        except Exception as error:

            print(
                f"[MERGE] Login failed for "
                f"{username}: "
                f"{type(error).__name__}: {error}"
            )

            return {
                "success": False,
                "account_id": account_id,
                "username": username,
                "error": str(error)
            }
            
    def get_balance(self, account_id):
        account = self.accounts.get(account_id)

        if not account:
            return {
                "success": False,
                "error": "Account not found."
            }

        page = account["page"]
        username = account["username"]

        try:
            balance_element = page.locator(
                "div.text-white.text-base.font-normal"
            ).first

            balance_element.wait_for(
                state="visible",
                timeout=15000
            )

            balance_text = balance_element.inner_text().strip()

            cleaned = (
                balance_text
                .replace(",", "")
                .replace("₱", "")
                .replace("PHP", "")
                .strip()
            )

            balance = float(cleaned)

            print(
                f"[MERGE] Balance read: "
                f"{username} = PHP {balance:.2f}"
            )

            return {
                "success": True,
                "account_id": account_id,
                "username": username,
                "balance": balance,
                "raw": balance_text
            }

        except Exception as error:
            print(
                f"[MERGE] Balance read failed for "
                f"{username}: "
                f"{type(error).__name__}: {error}"
            )

            return {
                "success": False,
                "account_id": account_id,
                "username": username,
                "error": str(error)
            }            

    def close_account(self, account_id):
        """
        Closes one account's browser context.
        """

        account = self.accounts.pop(account_id, None)

        if not account:
            print(
                f"[MERGE] ⚠️ Account {account_id} "
                f"was already closed or not found."
            )
            return

        username = account["username"]

        print(
            f"[MERGE] 🔴 CLOSING ELIMINATED ACCOUNT: "
            f"{username} (ID {account_id})"
        )

        try:
            account["context"].close()

            print(
                f"[MERGE] ✅ Account closed: "
                f"{username}"
            )

        except Exception as error:
            print(
                f"[MERGE] ❌ Error closing "
                f"{username}: "
                f"{type(error).__name__}: {error}"
            )


    def close_browser(self):
        """
        Closes all Merge accounts and
        the shared Camoufox browser.
        """

        print("[MERGE] Closing browser...")

        for account_id in list(
            self.accounts.keys()
        ):
            self.close_account(account_id)

        if self.browser is not None:

            try:
                self.browser.stop()

            except Exception as error:
                print(
                    f"[MERGE] Error stopping browser: "
                    f"{type(error).__name__}: {error}"
                )

            finally:
                self.browser = None

        print("[MERGE] Browser closed.")


    def get_account(self, account_id):
        return self.accounts.get(account_id)

    def switch_to_account(self, account_id):
        account = self.accounts.get(account_id)

        if not account:
            return False

        try:
            page = account["page"]
            page.bring_to_front()
            time.sleep(0.10)
            
            return True

        except Exception as error:
            print(
                f"[MERGE] Failed to switch to account "
                f"{account_id}: {type(error).__name__}: {error}"
            )
            return False

    def calculate_common_bet(self, balance_a, balance_b):
        """
        Calculate the shared wager.

        Both accounts wager the same amount, limited by the
        smaller balance and rounded down to the nearest PHP 10.
        """

        bet_a = int(balance_a // 10) * 10
        bet_b = int(balance_b // 10) * 10

        common_bet = min(bet_a, bet_b)

        return {
            "success": common_bet > 0,
            "common_bet": common_bet,
            "clicks": common_bet // 10
        }
        
    def calculate_chip_plan(self, amount):
        """
        Find an exact chip combination for the requested amount.

        Available chips:
            PHP 250
            PHP 50
            PHP 25
            PHP 10

        The planner prefers the combination requiring the
        fewest betting clicks.
        """

        chips = [
            (250, BET_CHIP_250),
            (50, BET_CHIP_50),
            (25, BET_CHIP_25),
            (10, BET_CHIP_10)
        ]

        if amount <= 0:
            return {
                "success": False,
                "error": "Bet amount must be greater than zero."
            }

        # Dynamic programming:
        # best[value] = best chip combination for that value.
        best = [None] * (amount + 1)
        best[0] = []

        for value in range(1, amount + 1):

            candidates = []

            for chip_value, chip_position in chips:

                if value < chip_value:
                    continue

                previous = best[value - chip_value]

                if previous is None:
                    continue

                candidate = previous + [
                    (chip_value, chip_position)
                ]

                candidates.append(candidate)

            if candidates:
                # Fewest total betting clicks wins.
                # If tied, fewer chip types wins.
                best[value] = min(
                    candidates,
                    key=lambda plan: (
                        len(plan),
                        len(set(chip[0] for chip in plan))
                    )
                )

        plan = best[amount]

        if plan is None:
            return {
                "success": False,
                "error": (
                    f"No exact chip combination found "
                    f"for PHP {amount:.2f}."
                )
            }

        # Convert the list into grouped chip counts.
        grouped = {}

        for chip_value, chip_position in plan:

            if chip_value not in grouped:
                grouped[chip_value] = {
                    "value": chip_value,
                    "position": chip_position,
                    "count": 0
                }

            grouped[chip_value]["count"] += 1

        grouped = list(grouped.values())

        print(
            f"[MERGE] CHIP PLAN → PHP {amount:.2f}: "
            + ", ".join(
                f"PHP {item['value']} x {item['count']}"
                for item in grouped
            )
            + f" | {len(plan)} bet clicks"
        )

        return {
            "success": True,
            "amount": amount,
            "clicks": len(plan),
            "chips": grouped
        }        

    def place_bet(self, account_id, position, amount):
        account = self.accounts.get(account_id)

        if not account:
            return {
                "success": False,
                "error": "Account not found."
            }

        if amount <= 0:
            return {
                "success": False,
                "error": "Bet amount must be greater than zero."
            }

        username = account["username"]

        try:

            # -----------------------------------------
            # Create optimized chip combination
            # -----------------------------------------

            chip_plan = self.calculate_chip_plan(amount)

            if not chip_plan["success"]:
                return chip_plan

            # -----------------------------------------
            # Switch to account
            # -----------------------------------------
            
            self.switch_to_account(account_id)
            time.sleep(0.7)

            # -----------------------------------------
            # Place optimized chips
            # -----------------------------------------

            for chip in chip_plan["chips"]:

                chip_value = chip["value"]
                chip_position = chip["position"]
                count = chip["count"]


                pyautogui.click(
                    *chip_position
                )
                time.sleep(0.10)

                print(
                    f"[MERGE] {username}: placing "
                    f"{count}x PHP {chip_value} "
                    f"at {position}"
                )

                for i in range(count):

                    pyautogui.click(
                        *position
                    )

                    if i < count - 1:
                        time.sleep(
                            BET_CLICK_DELAY
                        )

            print(
                f"[MERGE] {username}: optimized bet placed = "
                f"PHP {amount:.2f} "
                f"({chip_plan['clicks']} betting clicks)"
            )

            return {
                "success": True,
                "account_id": account_id,
                "username": username,
                "amount": amount,
                "clicks": chip_plan["clicks"],
                "chip_plan": chip_plan["chips"]
            }

        except Exception as error:

            print(
                f"[MERGE] Bet placement failed for "
                f"{username}: "
                f"{type(error).__name__}: {error}"
            )

            return {
                "success": False,
                "account_id": account_id,
                "username": username,
                "error": str(error)
            }

    def get_green_pixel_count(self, account_id):
        account = self.accounts.get(account_id)

        if not account:
            return 0

        # The visible browser window is aligned to the same screen
        # position, so this ROI is shared by the Merge accounts.
        screenshot = pyautogui.screenshot(
            region=COUNTDOWN_REGION
        )

        frame = np.array(screenshot)
        hsv = cv2.cvtColor(frame, cv2.COLOR_RGB2HSV)

        lower_green = np.array([35, 100, 100])
        upper_green = np.array([90, 255, 255])

        mask = cv2.inRange(
            hsv,
            lower_green,
            upper_green
        )

        return int(cv2.countNonZero(mask))

    def wait_for_betting_window(self, account_id, timeout=None):
        account = self.accounts.get(account_id)

        if not account:
            return False

        username = account["username"]

        print(
            f"[MERGE] Starting visual betting monitor: "
            f"{username}"
        )

        start_time = time.time()
        open_start = None
        last_state = None

        while True:
            now = time.time()

            if timeout is not None and now - start_time >= timeout:
                print(
                    f"[MERGE] Visual betting monitor timed out: "
                    f"{username}"
                )
                return False

            green_pixels = self.get_green_pixel_count(account_id)
            state = green_pixels >= OPEN_GREEN_PIXEL_THRESHOLD

            if state != last_state:
                print(
                    f"[MERGE] GREEN PIXELS: {green_pixels}"
                )
                print(
                    f"[MERGE] BETTING → "
                    f"{'OPEN 🟢' if state else 'CLOSED 🔴'}"
                )
                last_state = state

            if state:
                if open_start is None:
                    open_start = now
                elif now - open_start >= OPEN_CONFIRMATION_TIME:
                    print(
                        f"[MERGE] 🟢 BETTING WINDOW CONFIRMED FOR "
                        f"{username}"
                    )
                    return True
            else:
                open_start = None

            time.sleep(0.10)

    def wait_for_betting_window_close(self, account_id, timeout=None):
        account = self.accounts.get(account_id)

        if not account:
            return False

        username = account["username"]
        start_time = time.time()
        close_start = None
        last_state = None

        print(
            f"[MERGE] Waiting for betting window to close: "
            f"{username}"
        )

        while True:
            now = time.time()

            if timeout is not None and now - start_time >= timeout:
                print(
                    f"[MERGE] Betting-close monitor timed out: "
                    f"{username}"
                )
                return False

            green_pixels = self.get_green_pixel_count(account_id)
            state = green_pixels >= CLOSE_GREEN_PIXEL_THRESHOLD

            if state != last_state:
                print(
                    f"[MERGE] GREEN PIXELS: {green_pixels}"
                )
                print(
                    f"[MERGE] BETTING → "
                    f"{'OPEN 🟢' if state else 'CLOSED 🔴'}"
                )
                last_state = state

            if not state:
                if close_start is None:
                    close_start = now
                elif now - close_start >= CLOSE_CONFIRMATION_TIME:
                    print(
                        f"[MERGE] 🔴 BETTING WINDOW CONFIRMED CLOSED FOR "
                        f"{username}"
                    )
                    return True
            else:
                close_start = None

            time.sleep(0.10)
            
    def wait_for_next_betting_window(self, account_id, timeout=None):
        account = self.accounts.get(account_id)

        if not account:
            return False

        username = account["username"]

        print(
            f"[MERGE] Waiting for NEXT betting window: {username}"
        )

        start_time = time.time()

        while True:
            if timeout is not None:
                if time.time() - start_time >= timeout:
                    print("[MERGE] Timed out waiting for closed state.")
                    return False

            green_pixels = self.get_green_pixel_count(account_id)


            if green_pixels < CLOSE_GREEN_PIXEL_THRESHOLD:
                break

            time.sleep(0.10)

        print(
            "[MERGE] Betting is CLOSED. "
            "Now waiting for NEXT OPEN..."
        )

        # Now wait for the next actual OPEN state.
        open_start = None

        while True:
            if timeout is not None:
                if time.time() - start_time >= timeout:
                    print(
                        f"[MERGE] Next betting window timed out: "
                        f"{username}"
                    )
                    return False

            green_pixels = self.get_green_pixel_count(account_id)

            if green_pixels >= OPEN_GREEN_PIXEL_THRESHOLD:

                if open_start is None:
                    open_start = time.time()

                elif time.time() - open_start >= OPEN_CONFIRMATION_TIME:

                    print(
                        f"[MERGE] 🟢 NEXT BETTING WINDOW "
                        f"CONFIRMED OPEN FOR {username}"
                    )

                    return True

            else:
                open_start = None

            time.sleep(0.10)       

    def run_round(self, account_a=1, account_b=2, timeout=120, settlement_delay=1.0):
        """
        Run one complete Merge round.

        The winner is determined from the balance change after the
        betting window closes. The website remains responsible for
        the actual balance settlement.
        """
        first = self.accounts.get(account_a)
        second = self.accounts.get(account_b)

        if not first or not second:
            return {
                "success": False,
                "stage": "account_lookup",
                "error": "One or both Merge accounts were not found."
            }

        username_a = first["username"]
        username_b = second["username"]

        print(
            f"[MERGE] === ROUND START: {username_a} vs {username_b} ==="
        )

        # --------------------------------------------------
        # 1. Read balances before betting
        # --------------------------------------------------
        balance_a_result = self.get_balance(account_a)
        balance_b_result = self.get_balance(account_b)

        if not balance_a_result["success"]:
            return {
                "success": False,
                "stage": "balance_before_account_1",
                "error": balance_a_result.get("error", "Unknown error")
            }

        if not balance_b_result["success"]:
            return {
                "success": False,
                "stage": "balance_before_account_2",
                "error": balance_b_result.get("error", "Unknown error")
            }

        balance_a_before = balance_a_result["balance"]
        balance_b_before = balance_b_result["balance"]

        print(
            f"[MERGE] ROUND BALANCES BEFORE → "
            f"{username_a}=PHP {balance_a_before:.2f}, "
            f"{username_b}=PHP {balance_b_before:.2f}"
        )

        # --------------------------------------------------
        # 2. Create the common bet plan
        # --------------------------------------------------
        plan = self.calculate_common_bet(
            balance_a_before,
            balance_b_before
        )

        if not plan["success"]:
            return {
                "success": False,
                "stage": "bet_plan",
                "error": "Common bet is zero; one or both accounts cannot bet PHP 10."
            }

        # --------------------------------------------------
        # 3. Wait for betting window to open
        # --------------------------------------------------
        if not self.wait_for_next_betting_window(account_b, timeout=120):
            return {
                "success": False,
                "stage": "betting_open",
                "error": "Betting window did not open."
            }

        # --------------------------------------------------
        # 4. Place both bets
        # --------------------------------------------------
        bet_result = self.place_merge_bets(
            account_a,
            account_b,
            balance_a_before,
            balance_b_before
        )

        if not bet_result["success"]:
            return {
                "success": False,
                "stage": "bet_placement",
                "error": bet_result.get("error", "Bet placement failed."),
                "bet_result": bet_result
            }

        # --------------------------------------------------
        # 5. Wait for betting window to close
        # --------------------------------------------------
        # The second account is the last page we interacted with, so make
        # it the active visible game before monitoring the shared screen ROI.
        self.switch_to_account(account_b)

        if not self.wait_for_betting_window_close(account_b, timeout=timeout):
            return {
                "success": False,
                "stage": "betting_close",
                "error": "Betting window did not close."
            }

        # Give the website a short moment to settle the balances.
        # 6. Wait for the NEXT betting window to open.
        # Closing the current betting window does NOT mean
        # the round has settled yet.

        if not self.wait_for_next_betting_window(account_b, timeout=120):
            return {
                "success": False,
                "stage": "next_betting_open",
                "error": "Next betting window did not open."
            }

        print(
            f"[MERGE] Next betting window opened. "
            f"Waiting {settlement_delay:.2f}s for balance settlement..."
        )

        time.sleep(settlement_delay)

        # --------------------------------------------------
        # 7. Read balances after settlement
        # --------------------------------------------------
        balance_a_result = self.get_balance(account_a)
        balance_b_result = self.get_balance(account_b)

        if not balance_a_result["success"]:
            return {
                "success": False,
                "stage": "balance_after_account_1",
                "error": balance_a_result.get("error", "Unknown error")
            }

        if not balance_b_result["success"]:
            return {
                "success": False,
                "stage": "balance_after_account_2",
                "error": balance_b_result.get("error", "Unknown error")
            }

        balance_a_after = balance_a_result["balance"]
        balance_b_after = balance_b_result["balance"]

        change_a = balance_a_after - balance_a_before
        change_b = balance_b_after - balance_b_before

        print(
            f"[MERGE] ROUND BALANCES AFTER → "
            f"{username_a}=PHP {balance_a_after:.2f} "
            f"({change_a:+.2f}), "
            f"{username_b}=PHP {balance_b_after:.2f} "
            f"({change_b:+.2f})"
        )

        # --------------------------------------------------
        # 7. Determine winner from balance changes
        # --------------------------------------------------
        winner = None
        loser = None
        result_state = "unknown"

        if change_a > 0 and change_b <= 0:
            winner = username_a
            loser = username_b
            result_state = "account_1_win"
        elif change_b > 0 and change_a <= 0:
            winner = username_b
            loser = username_a
            result_state = "account_2_win"
        elif change_a == 0 and change_b == 0:
            result_state = "no_balance_change"
        else:
            result_state = "unexpected_balance_change"

        print(
            f"[MERGE] ROUND RESULT → {result_state}"
        )

        print("[MERGE] ========================================")
        print(f"[MERGE] ROUND SUMMARY: {username_a} vs {username_b}")
        print(f"[MERGE] BET: PHP {plan['common_bet']:.2f}")
        print(f"[MERGE] {username_a}: PHP {balance_a_before:.2f} → PHP {balance_a_after:.2f} ({change_a:+.2f})")
        print(f"[MERGE] {username_b}: PHP {balance_b_before:.2f} → PHP {balance_b_after:.2f} ({change_b:+.2f})")
        if winner:
            print(f"[MERGE] 🏆 WINNER: {winner}")
            print(f"[MERGE] ❌ LOSER: {loser}")
        else:
            print("[MERGE] ⚠️ WINNER: UNDETERMINED")
        print("[MERGE] ========================================")

        return {
            "success": winner is not None,
            "result_state": result_state,
            "winner": winner,
            "loser": loser,
            "account_1": {
                "account_id": account_a,
                "username": username_a,
                "before": balance_a_before,
                "after": balance_a_after,
                "change": change_a
            },
            "account_2": {
                "account_id": account_b,
                "username": username_b,
                "before": balance_b_before,
                "after": balance_b_after,
                "change": change_b
            },
            "bet": bet_result.get("common_bet", plan["common_bet"]),
            "clicks": bet_result.get("clicks", plan["clicks"])
        }
        
    def run_merge_chain(
        self,
        usernames,
        password,
        url,
        batch_size=3,
        round_timeout=120,
        settlement_delay=1.0
    ):
            """
            Run the complete sequential Merge chain.

            Rules:
            - Maximum of `batch_size` accounts are prepared at once.
            - Accounts are processed sequentially.
            - The current survivor fights the next account.
            - Losers are closed immediately.
            - No new accounts are prepared while the current batch
            is still being processed.
            - The survivor carries into the next batch.
            - Account IDs 1..batch_size are reused between batches.
            """

            print("[MERGE] ========================================")
            print("[MERGE] STARTING MERGE CHAIN")
            print(f"[MERGE] Total usernames: {len(usernames)}")
            print(f"[MERGE] Batch size: {batch_size}")
            print("[MERGE] ========================================")

            if not usernames:
                return {
                    "success": False,
                    "stage": "validation",
                    "error": "No usernames provided."
                }

            if len(usernames) < 2:
                return {
                    "success": False,
                    "stage": "validation",
                    "error": "At least 2 usernames are required."
                }

            if batch_size < 2:
                return {
                    "success": False,
                    "stage": "validation",
                    "error": "Batch size must be at least 2."
                }

            # Keep a complete history of every round.
            round_history = []

            # A round error gets one recovery attempt. A successful round
            # resets this counter, so later errors get their own retry.
            consecutive_round_errors = 0

            # Username pointer.
            next_username_index = 0

            # The surviving account from the previous batch.
            survivor_account_id = None
            survivor_username = None

            round_number = 0

            try:

                while next_username_index < len(usernames):

                    print()
                    print("[MERGE] ----------------------------------------")
                    print(
                        f"[MERGE] Preparing next batch "
                        f"(starting index: {next_username_index})"
                    )
                    print("[MERGE] ----------------------------------------")

                    # ==================================================
                    # 1. PREPARE CURRENT BATCH
                    # ==================================================

                    batch_accounts = []

                    # If we already have a survivor from the previous
                    # batch, that survivor occupies the first slot.
                    if survivor_account_id is not None:
                        batch_accounts.append({
                            "account_id": 1,
                            "username": survivor_username,
                            "existing_survivor": True
                        })

                        # The survivor's actual account ID may have been
                        # different in the previous batch.
                        if survivor_account_id != 1:
                            account = self.accounts.get(
                                survivor_account_id
                            )

                            if account is None:
                                return {
                                    "success": False,
                                    "stage": "survivor_lookup",
                                    "error": (
                                        f"Survivor account "
                                        f"{survivor_account_id} "
                                        f"was not found."
                                    ),
                                    "round_history": round_history
                                }

                            # Move the survivor into slot 1.
                            self.accounts[1] = account

                            del self.accounts[survivor_account_id]

                            survivor_account_id = 1

                    # Fill the remaining batch slots.
                    while (
                        len(batch_accounts) < batch_size
                        and next_username_index < len(usernames)
                    ):

                        username = usernames[next_username_index]
                        next_username_index += 1

                        account_id = len(batch_accounts) + 1

                        batch_accounts.append({
                            "account_id": account_id,
                            "username": username,
                            "existing_survivor": False
                        })

                    print(
                        f"[MERGE] Batch contains "
                        f"{len(batch_accounts)} accounts."
                    )

                    # ==================================================
                    # 2. OPEN + LOGIN NEW ACCOUNTS IN THIS BATCH
                    # ==================================================
                    #
                    # Accounts with a starting balance below the minimum
                    # bet are closed immediately and replaced by the next
                    # username, so they never consume a merge slot.

                    batch_slot_index = 0

                    while batch_slot_index < len(batch_accounts):

                        account_info = batch_accounts[batch_slot_index]

                        account_id = account_info["account_id"]
                        username = account_info["username"]

                        # Survivor is already logged in and ready.
                        if account_info["existing_survivor"]:
                            print(
                                f"[MERGE] Keeping survivor alive: "
                                f"{username}"
                            )
                            batch_slot_index += 1
                            continue

                        print(
                            f"[MERGE] Preparing account "
                            f"{account_id}: {username}"
                        )

                        open_result = self.open_account(
                            account_id,
                            username,
                            url
                        )

                        if not open_result["success"]:
                            return {
                                "success": False,
                                "stage": "open_account",
                                "account_id": account_id,
                                "username": username,
                                "error": open_result.get(
                                    "error",
                                    "Failed to open account."
                                ),
                                "round_history": round_history
                            }

                        login_result = self.login_account(
                            account_id,
                            password
                        )

                        if not login_result["success"]:

                            self.close_account(account_id)

                            return {
                                "success": False,
                                "stage": "login_account",
                                "account_id": account_id,
                                "username": username,
                                "error": login_result.get(
                                    "error",
                                    "Failed to login account."
                                ),
                                "round_history": round_history
                            }

                        # --------------------------------------------------
                        # NEW ACCOUNT BALANCE PRE-CHECK
                        # --------------------------------------------------
                        # An account below the minimum bet can never
                        # participate in a round. Close it immediately and
                        # replace it with the next username.
                        initial_balance_result = self.get_balance(account_id)

                        if not initial_balance_result["success"]:

                            self.close_account(account_id)

                            return {
                                "success": False,
                                "stage": "initial_balance_check",
                                "account_id": account_id,
                                "username": username,
                                "error": initial_balance_result.get(
                                    "error",
                                    "Failed to read initial account balance."
                                ),
                                "round_history": round_history
                            }

                        initial_balance = initial_balance_result["balance"]

                        print(
                            f"[MERGE] Initial balance: "
                            f"{username}=PHP {initial_balance:.2f}"
                        )

                        if initial_balance < MERGE_MIN_BET:

                            print(
                                f"[MERGE] ⚠️ SKIPPING ACCOUNT: "
                                f"{username} "
                                f"(PHP {initial_balance:.2f} < PHP {MERGE_MIN_BET})"
                            )

                            self.close_account(account_id)

                            # Replace this batch slot with the next username.
                            if next_username_index < len(usernames):

                                replacement_username = usernames[
                                    next_username_index
                                ]
                                next_username_index += 1

                                print(
                                    f"[MERGE] Replacing skipped account "
                                    f"with: {replacement_username}"
                                )

                                batch_accounts[batch_slot_index] = {
                                    "account_id": account_id,
                                    "username": replacement_username,
                                    "existing_survivor": False
                                }

                                # Do not advance the slot. The replacement
                                # must be prepared and checked immediately.
                                continue

                            # No usernames remain. Remove this unusable slot.
                            batch_accounts.pop(batch_slot_index)
                            continue

                        print(
                            f"[MERGE] Account ready: "
                            f"{username}"
                        )

                        batch_slot_index += 1

                    print(
                        f"[MERGE] Batch contains "
                        f"{len(batch_accounts)} usable accounts."
                    )

                    # ==================================================
                    # 3. DETERMINE INITIAL SURVIVOR
                    # ==================================================

                    if survivor_account_id is None:

                        survivor_account_id = batch_accounts[0][
                            "account_id"
                        ]

                        survivor_username = batch_accounts[0][
                            "username"
                        ]

                        print(
                            f"[MERGE] Initial survivor: "
                            f"{survivor_username}"
                        )

                    # ==================================================
                    # 4. SEQUENTIAL ELIMINATION
                    # ==================================================

                    for account_info in batch_accounts:

                        opponent_id = account_info["account_id"]
                        opponent_username = account_info["username"]

                        # Never fight ourselves.
                        if opponent_id == survivor_account_id:
                            continue

                        # Make sure both accounts still exist.
                        if survivor_account_id not in self.accounts:
                            return {
                                "success": False,
                                "stage": "survivor_missing",
                                "error": (
                                    f"Survivor account "
                                    f"{survivor_account_id} "
                                    f"is no longer available."
                                ),
                                "round_history": round_history
                            }

                        if opponent_id not in self.accounts:
                            return {
                                "success": False,
                                "stage": "opponent_missing",
                                "error": (
                                    f"Opponent account "
                                    f"{opponent_id} "
                                    f"is no longer available."
                                ),
                                "round_history": round_history
                            }

                        # --------------------------------------------------
                        # Keep playing THIS PAIR until one account can no
                        # longer place the minimum bet.
                        #
                        # IMPORTANT:
                        # A round winner is NOT automatically the survivor.
                        # The survivor is determined only by the post-round
                        # balance threshold.
                        # --------------------------------------------------
                        while True:

                            survivor_account = self.accounts.get(
                                survivor_account_id
                            )
                            opponent_account = self.accounts.get(
                                opponent_id
                            )

                            if not survivor_account or not opponent_account:
                                return {
                                    "success": False,
                                    "stage": "pair_account_missing",
                                    "error": (
                                        "One of the accounts in the "
                                        "current pair disappeared."
                                    ),
                                    "round_history": round_history
                                }

                            survivor_balance_result = self.get_balance(
                                survivor_account_id
                            )
                            opponent_balance_result = self.get_balance(
                                opponent_id
                            )

                            if not survivor_balance_result["success"]:
                                return {
                                    "success": False,
                                    "stage": "survivor_balance_check",
                                    "error": survivor_balance_result.get(
                                        "error",
                                        "Failed to read survivor balance."
                                    ),
                                    "round_history": round_history
                                }

                            if not opponent_balance_result["success"]:
                                return {
                                    "success": False,
                                    "stage": "opponent_balance_check",
                                    "error": opponent_balance_result.get(
                                        "error",
                                        "Failed to read opponent balance."
                                    ),
                                    "round_history": round_history
                                }

                            survivor_balance = survivor_balance_result["balance"]
                            opponent_balance = opponent_balance_result["balance"]

                            print(
                                f"[MERGE] PAIR BALANCES → "
                                f"{survivor_username}=PHP {survivor_balance:.2f}, "
                                f"{opponent_username}=PHP {opponent_balance:.2f}"
                            )

                            # One account is already below the minimum.
                            # No new round should be started.
                            if survivor_balance < MERGE_MIN_BET:
                                print(
                                    f"[MERGE] ❌ ELIMINATED: "
                                    f"{survivor_username} "
                                    f"(PHP {survivor_balance:.2f} < PHP {MERGE_MIN_BET})"
                                )
                                print(
                                    f"[MERGE] 🏆 SURVIVOR: "
                                    f"{opponent_username}"
                                )

                                self.close_account(survivor_account_id)
                                survivor_account_id = opponent_id
                                survivor_username = opponent_username
                                break

                            if opponent_balance < MERGE_MIN_BET:
                                print(
                                    f"[MERGE] ❌ ELIMINATED: "
                                    f"{opponent_username} "
                                    f"(PHP {opponent_balance:.2f} < PHP {MERGE_MIN_BET})"
                                )
                                print(
                                    f"[MERGE] 🏆 SURVIVOR: "
                                    f"{survivor_username}"
                                )

                                self.close_account(opponent_id)
                                break

                            round_number += 1

                            print()
                            print("[MERGE] ========================================")
                            print(
                                f"[MERGE] ROUND {round_number}"
                            )
                            print(
                                f"[MERGE] {survivor_username} "
                                f"vs "
                                f"{opponent_username}"
                            )
                            print("[MERGE] ========================================")

                            # ----------------------------------------------
                            # Run one round.
                            # ----------------------------------------------
                            round_result = self.run_round(
                                account_a=survivor_account_id,
                                account_b=opponent_id,
                                timeout=round_timeout,
                                settlement_delay=settlement_delay
                            )

                            if not round_result["success"]:

                                consecutive_round_errors += 1

                                print(
                                    "[MERGE] ❌ Round failed."
                                )
                                print(
                                    f"[MERGE] Consecutive round errors: "
                                    f"{consecutive_round_errors}/2"
                                )

                                # First error: sacrifice this attempt, wait
                                # for the next betting window, then retry the
                                # same pair using the existing run_round().
                                if consecutive_round_errors < 2:
                                    print(
                                        "[MERGE] ⚠️ First round error. "
                                        "Waiting for the next betting window "
                                        "before retrying..."
                                    )

                                    if not self.wait_for_next_betting_window(
                                        opponent_id,
                                        timeout=round_timeout
                                    ):
                                        consecutive_round_errors += 1
                                        print(
                                            "[MERGE] ❌ Failed to recover "
                                            "to the next betting window."
                                        )
                                        print(
                                            f"[MERGE] Consecutive round "
                                            f"errors: {consecutive_round_errors}/2"
                                        )

                                        return {
                                            "success": False,
                                            "stage": "round_recovery",
                                            "round_number": round_number,
                                            "error": (
                                                "Round failed, and the "
                                                "next betting window could "
                                                "not be reached."
                                            ),
                                            "round_result": round_result,
                                            "round_history": round_history,
                                            "survivor": survivor_username
                                        }

                                    continue

                                # Second consecutive error: stop the merge.
                                print(
                                    "[MERGE] ❌ Second consecutive round "
                                    "error. Stopping merge automation."
                                )

                                return {
                                    "success": False,
                                    "stage": "round",
                                    "round_number": round_number,
                                    "error": round_result.get(
                                        "error",
                                        "Merge round failed twice "
                                        "consecutively."
                                    ),
                                    "round_result": round_result,
                                    "round_history": round_history,
                                    "survivor": survivor_username
                                }

                            # A successful round clears the error streak.
                            consecutive_round_errors = 0

                            # Save every round, including rounds where the
                            # winner does NOT yet determine elimination.
                            round_history.append({
                                "round_number": round_number,
                                "survivor_before": survivor_username,
                                "opponent": opponent_username,
                                "result": round_result
                            })

                            winner = round_result.get("winner")
                            loser = round_result.get("loser")

                            print(
                                f"[MERGE] ROUND WINNER: "
                                f"{winner or 'UNDETERMINED'}"
                            )

                            # IMPORTANT: Do NOT eliminate anyone based only
                            # on the round winner. The next loop iteration
                            # checks the actual post-round balances.
                            if winner == survivor_username:
                                print(
                                    f"[MERGE] {survivor_username} won the round, "
                                    f"but the pair continues if both can still bet."
                                )
                            elif winner == opponent_username:
                                print(
                                    f"[MERGE] {opponent_username} won the round, "
                                    f"but the pair continues if both can still bet."
                                )
                            else:
                                print(
                                    "[MERGE] ⚠️ Winner could not be determined."
                                )

                                return {
                                    "success": False,
                                    "stage": "winner_detection",
                                    "round_number": round_number,
                                    "error": (
                                        "Round completed but winner was undetermined."
                                    ),
                                    "round_result": round_result,
                                    "round_history": round_history
                                }

                    # ==================================================
                    # 5. CURRENT BATCH FINISHED
                    # ==================================================

                    print()
                    print("[MERGE] ----------------------------------------")
                    print(
                        f"[MERGE] BATCH FINISHED"
                    )
                    print(
                        f"[MERGE] Survivor: "
                        f"{survivor_username}"
                    )
                    print("[MERGE] ----------------------------------------")

                    # If there are no usernames left, we're completely done.
                    if next_username_index >= len(usernames):

                        print()
                        print("[MERGE] ========================================")
                        print(
                            f"[MERGE] 🏆 FINAL WINNER: "
                            f"{survivor_username}"
                        )
                        print("[MERGE] ========================================")

                        # Read final balance.
                        final_balance_result = self.get_balance(
                            survivor_account_id
                        )

                        final_balance = None

                        if final_balance_result["success"]:
                            final_balance = (
                                final_balance_result["balance"]
                            )

                        return {
                            "success": True,
                            "final_winner": survivor_username,
                            "final_account_id": survivor_account_id,
                            "final_balance": final_balance,
                            "rounds": round_number,
                            "round_history": round_history
                        }

                    # ==================================================
                    # 6. NEXT BATCH
                    # ==================================================

                    print(
                        "[MERGE] More accounts remain."
                    )

                    print(
                        f"[MERGE] Keeping survivor alive: "
                        f"{survivor_username}"
                    )

                    # The current survivor stays open.
                    #
                    # The next batch will place the survivor into
                    # account slot 1 and fill slots 2..batch_size
                    # with fresh accounts.

            except Exception as error:

                print(
                    "[MERGE] ❌ MERGE CHAIN FAILED: "
                    f"{type(error).__name__}: {error}"
                )

                return {
                    "success": False,
                    "stage": "merge_chain",
                    "error": str(error),
                    "round_history": round_history,
                    "rounds": round_number,
                    "survivor": survivor_username
                }        

    def place_merge_bets(self, account_a, account_b, balance_a, balance_b):

        plan = self.calculate_common_bet(
            balance_a,
            balance_b
        )

        if not plan["success"]:
            print(
                f"[MERGE] Cannot create bet plan: "
                f"balances={balance_a}, {balance_b}"
            )
            return plan

        common_bet = plan["common_bet"]

        print(
            f"[MERGE] BET PLAN → "
            f"common bet=PHP {common_bet:.2f}"
        )

        # -----------------------------------------
        # Account 1 → ODD
        # -----------------------------------------

        first_result = self.place_bet(
            account_a,
            ODD_BET,
            common_bet
        )

        if not first_result["success"]:
            return {
                "success": False,
                "stage": "account_1",
                "error": first_result.get(
                    "error",
                    "Unknown error"
                )
            }

        # -----------------------------------------
        # Account 2 → EVEN
        # -----------------------------------------

        second_result = self.place_bet(
            account_b,
            EVEN_BET,
            common_bet
        )

        if not second_result["success"]:
            return {
                "success": False,
                "stage": "account_2",
                "error": second_result.get(
                    "error",
                    "Unknown error"
                )
            }

        return {
            "success": True,
            "common_bet": common_bet,
            "clicks": (
                first_result["clicks"]
                + second_result["clicks"]
            ),
            "account_1": first_result,
            "account_2": second_result
        }

    def is_betting_open(self, account_id):
        account = self.accounts.get(account_id)

        if not account:
            return False

        page = account["page"]

        try:
            container = page.locator(
                '[data-role="footer-perspective-container"]'
            )

            if container.count() == 0:
                return False

            collapsed = container.get_attribute(
                "data-is-collapsed"
            )

            print(
                f"[MERGE] Betting state for "
                f"{account['username']}: "
                f"collapsed={collapsed}"
            )

            return collapsed == "false"

        except Exception as error:
            print(
                f"[MERGE] Betting state check failed: "
                f"{type(error).__name__}: {error}"
            )

            return False


    def wait_for_betting(self, account_id, timeout=None):
        account = self.accounts.get(account_id)

        if not account:
            return False

        username = account["username"]

        print(
            f"[MERGE] Monitoring betting state: "
            f"{username}"
        )

        start_time = time.time()
        last_state = None

        while True:

            # Optional timeout
            if timeout is not None:
                if time.time() - start_time >= timeout:
                    print(
                        f"[MERGE] Betting monitor timed out: "
                        f"{username}"
                    )
                    return False

            state = self.is_betting_open(account_id)

            # Only print when state changes
            if state != last_state:

                print(
                    f"[MERGE] BETTING STATE → "
                    f"{'OPEN 🟢' if state else 'CLOSED 🔴'}"
                )

                last_state = state

            # Betting window opened
            if state:
                print(
                    f"[MERGE] Betting window detected! "
                    f"{username}"
                )

                return True

            time.sleep(0.05)

merge_worker = MergeWorker()