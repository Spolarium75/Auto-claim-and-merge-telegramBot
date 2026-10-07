from concurrent.futures import ThreadPoolExecutor

import asyncio


class MergeManager:

    def __init__(self):

        # One active Merge job per Telegram user.
        self.jobs = {}

        # Async task for each active Merge job.
        self.tasks = {}

        # Stop signal for each active Merge job.
        self.stop_events = {}
        
        self.executor = ThreadPoolExecutor(
        max_workers=1,
        thread_name_prefix="merge_worker"
    )

    # =========================
    # Start Merge
    # =========================

    def start_merge(
        self,
        telegram_id,
        usernames
    ):

        # Prevent duplicate Merge jobs.
        if telegram_id in self.jobs:

            return None


        if len(usernames) < 2:

            return None


        # Initial Merge state.
        state = {

            "telegram_id": telegram_id,

            "status": "queued",

            "usernames": list(usernames),

            "current_index": 0,

            "current_account": (
                usernames[0]
            ),

            "opponent": (
                usernames[1]
            ),

            "round_number": 0,

            "total_rounds": 0,

            "completed_rounds": 0,

            "last_winner": None,

            "survivor": None,

            "final_winner": None,

            "final_balance": None,
            "last_round_result": None,
            "last_round_error": None,

        }


        self.jobs[telegram_id] = state

        self.stop_events[telegram_id] = (
            asyncio.Event()
        )


        return state


    # =========================
    # Get Merge
    # =========================

    def get_merge(
        self,
        telegram_id
    ):

        return self.jobs.get(
            telegram_id
        )


    # =========================
    # Is Active
    # =========================

    def is_active(
        self,
        telegram_id
    ):

        job = self.jobs.get(
            telegram_id
        )

        if not job:
            return False

        return job["status"] in (
            "queued",
            "running"
        )


    # =========================
    # Update State
    # =========================

    def update(
        self,
        telegram_id,
        **changes
    ):

        job = self.jobs.get(
            telegram_id
        )

        if not job:
            return False


        job.update(changes)

        return True


    # =========================
    # Stop Signal
    # =========================

    def request_stop(
        self,
        telegram_id
    ):

        event = self.stop_events.get(
            telegram_id
        )

        if not event:
            return False


        event.set()

        return True


    # =========================
    # Stop Requested?
    # =========================

    def stop_requested(
        self,
        telegram_id
    ):

        event = self.stop_events.get(
            telegram_id
        )

        if not event:
            return False


        return event.is_set()



    # =========================
    # Run Merge Round
    # =========================

    async def run_round(self, telegram_id, account_a=1, account_b=2, settlement_delay=2.0):
        """Run one Fan Tan round through merge_worker and store its result."""
        job = self.jobs.get(telegram_id)
        if not job:
            return None

        if self.stop_requested(telegram_id):
            return None

        job["status"] = "running"
        job["round_number"] = job.get("round_number", 0) + 1
        job["last_round_error"] = None

        try:
            from merge_worker import merge_worker

            loop = asyncio.get_running_loop()
            result = await loop.run_in_executor(
                self.executor,
                lambda: merge_worker.run_round(
                    account_a=account_a,
                    account_b=account_b,
                    settlement_delay=settlement_delay,
                )
            )

            job["last_round_result"] = result

            if isinstance(result, dict) and result.get("success"):
                job["completed_rounds"] = job.get("completed_rounds", 0) + 1
                job["last_winner"] = result.get("winner")
                job["survivor"] = result.get("winner")

            return result

        except Exception as error:
            job["last_round_error"] = type(error).__name__
            return {
                "success": False,
                "status": "exception",
                "error": type(error).__name__,
            }

    # =========================
    # Finish Merge
    # =========================

    def finish(
        self,
        telegram_id,
        final_winner=None,
        final_balance=None
    ):

        job = self.jobs.get(
            telegram_id
        )

        if not job:
            return False


        job["status"] = "completed"

        job["final_winner"] = (
            final_winner
        )

        job["final_balance"] = (
            final_balance
        )


        return True

        # =========================
    # Run Complete Merge Chain
    # =========================

    async def run_merge_chain(
        self,
        telegram_id,
        password,
        url,
        batch_size=3,
        round_timeout=120,
        settlement_delay=1.0
    ):
        """
        Run the complete Merge chain through merge_worker.
        """

        job = self.jobs.get(telegram_id)

        if not job:
            return None

        if self.stop_requested(telegram_id):
            return None

        job["status"] = "running"
        job["last_round_error"] = None

        try:
            from merge_worker import merge_worker

            loop = asyncio.get_running_loop()

            result = await loop.run_in_executor(
                self.executor,
                lambda: merge_worker.run_merge_chain(
                    usernames=job["usernames"],
                    password=password,
                    url=url,
                    batch_size=batch_size,
                    round_timeout=round_timeout,
                    settlement_delay=settlement_delay
                )
            )

            # Save final result information.
            if isinstance(result, dict):

                job["final_winner"] = result.get(
                    "final_winner"
                )

                job["final_balance"] = result.get(
                    "final_balance"
                )

                job["completed_rounds"] = result.get(
                    "rounds",
                    job.get("completed_rounds", 0)
                )

                job["survivor"] = result.get(
                    "final_winner"
                )

                job["last_round_result"] = result

                if result.get("success"):
                    job["status"] = "completed"
                else:
                    job["status"] = "failed"

            return result

        except Exception as error:

            job["status"] = "failed"

            job["last_round_error"] = (
                type(error).__name__
            )

            return {
                "success": False,
                "status": "exception",
                "error": type(error).__name__
            }
    
    # =========================
    # Mark Stopped
    # =========================

    def stop(
        self,
        telegram_id
    ):

        job = self.jobs.get(
            telegram_id
        )

        if not job:
            return False


        job["status"] = "stopped"

        return True


    # =========================
    # Cleanup
    # =========================

    def cleanup(
        self,
        telegram_id
    ):

        self.tasks.pop(
            telegram_id,
            None
        )

        self.stop_events.pop(
            telegram_id,
            None
        )

        self.jobs.pop(
            telegram_id,
            None
        )


    # =========================
    # Current Merge Summary
    # =========================

    def get_summary(
        self,
        telegram_id
    ):

        job = self.jobs.get(
            telegram_id
        )

        if not job:
            return None


        return {

            "status": job["status"],

            "current_account": (
                job["current_account"]
            ),

            "opponent": (
                job["opponent"]
            ),

            "round_number": (
                job["round_number"]
            ),

            "completed_rounds": (
                job["completed_rounds"]
            ),

            "last_winner": (
                job["last_winner"]
            ),

            "survivor": (
                job["survivor"]
            ),

            "final_winner": (
                job["final_winner"]
            ),

            "final_balance": (
                job["final_balance"]
            ),

        }


merge_manager = MergeManager()