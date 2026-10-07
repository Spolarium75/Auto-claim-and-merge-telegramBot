import asyncio
from concurrent.futures import ThreadPoolExecutor

from repositories import (
    create_job,
    mark_job_running,
    get_next_queued_account,
    mark_account_running,
    mark_account_prepared,
    mark_preparation_failed,
    finish_account,
    get_job,
    get_shared_password,
    get_websites,
    mark_job_completed,
    mark_job_stopped,
)

from worker.camoufox_worker import (
    prepare_account,
    submit_code,
    confirm_code,
    close_account,
)


class JobManager:

    def __init__(self):
        self.tasks = {}
        self.stop_events = {}
        self.prepared_accounts = {}
        self.preparation_events = {}
        self.preparation_stop_events = {}
        self.preparation_stopped_jobs = set()

        # One dedicated thread for ALL Camoufox/PyAutoGUI work.
        #
        # This is important because PyAutoGUI controls
        # one physical mouse/keyboard.
        self.worker_executor = ThreadPoolExecutor(
            max_workers=1,
            thread_name_prefix="camoufox-worker"
        )

    # =========================
    # Worker Runner
    # =========================

    async def run_worker(self, function, *args):
        loop = asyncio.get_running_loop()

        def worker_wrapper():
            result = function(*args)

            return result

        result = await loop.run_in_executor(
            self.worker_executor,
            worker_wrapper
        )

        return result
    # =========================
    # Start / Prepare Job
    # =========================

    async def start_job(
        self,
        telegram_id,
        usernames
    ):
        # Database still requires a code when
        # creating the job, so use an empty string
        # until the user provides the redeem code.

        job_id = create_job(
            telegram_id,
            "",
            usernames
        )

        stop_event = asyncio.Event()
        self.stop_events[job_id] = stop_event
        preparation_stop_event = asyncio.Event()

        self.preparation_stop_events[job_id] = (
            preparation_stop_event
        )

        # Only store account metadata here.
        #
        # IMPORTANT:
        # No browser/page objects are stored in JobManager.
        self.prepared_accounts[job_id] = {}

        preparation_event = asyncio.Event()

        self.preparation_events[job_id] = (
            preparation_event
        )

        task = asyncio.create_task(
            self._prepare_job(
                job_id,
                preparation_stop_event
            )
        )

        self.tasks[job_id] = task

        return job_id

    # =========================
    # Prepare All Accounts
    # =========================

    async def _prepare_job(
        self,
        job_id,
        preparation_stop_event
    ):
        try:

            mark_job_running(job_id)

            job = get_job(job_id)

            if not job:
                print(
                    f"[JOB {job_id}] "
                    "Job not found."
                )
                return

            telegram_id = job["telegram_id"]

            # =========================
            # Password
            # =========================

            password = get_shared_password(
                telegram_id
            )

            if not password:
                print(
                    f"[JOB {job_id}] "
                    "No shared password."
                )

                mark_job_stopped(job_id)

                return

            # =========================
            # Website
            # =========================

            websites = get_websites(
                telegram_id
            )

            if not websites:
                print(
                    f"[JOB {job_id}] "
                    "No website configured."
                )

                mark_job_stopped(job_id)

                return

            # For now we use the first website.
            website = websites[0]

            print("=" * 60)

            print(
                f"[JOB {job_id}] "
                f"Website: {website['name']}"
            )

            print(
                f"[JOB {job_id}] "
                f"URL: {website['url']}"
            )

            print("=" * 60)

            # =========================
            # Account Preparation Loop
            # =========================

            while not preparation_stop_event.is_set():

                account = get_next_queued_account(
                    job_id
                )

                # No more queued accounts.
                if not account:

                    print("=" * 60)

                    print(
                        f"[JOB {job_id}] "
                        "All accounts prepared."
                    )

                    print("=" * 60)

                    return

                account_id = account["id"]
                username = account["username"]
                line_number = account["line_number"]

                print("=" * 60)

                print(
                    f"[JOB {job_id}] "
                    f"Preparing: {username}"
                )

                print(
                    f"[JOB {job_id}] "
                    f"Line: {line_number}"
                )

                print(
                    f"[JOB {job_id}] "
                    f"Account ID: {account_id}"
                )

                print("=" * 60)

                mark_account_running(
                    account_id
                )

                # =========================
                # Prepare Account
                # =========================
                #
                # IMPORTANT:
                #
                # We pass only simple values.
                #
                # The worker owns the actual
                # Camoufox browser/page objects.
                #

                result = await self.run_worker(
                    prepare_account,
                    account_id,
                    website["url"],
                    username,
                    password
                )

                # =========================
                # Preparation Failed
                # =========================

                if not result.get("success"):

                    mark_preparation_failed(
                        job_id=job_id,
                        account_id=account_id,
                        error_code=result.get(
                            "error_code"
                        ),
                        error_message=result.get(
                            "error_message"
                        )
                    )

                    print(
                        f"[JOB {job_id}] "
                        f"Preparation failed: "
                        f"{username}"
                    )

                    if result.get("error_message"):
                        print(
                            f"[JOB {job_id}] "
                            f"Reason: "
                            f"{result['error_message']}"
                        )

                    continue

                # =========================
                # Store Prepared Account
                # =========================
                #
                # ONLY metadata.
                #
                # The browser/page remains inside
                # camoufox_worker.py.
                #

                self.prepared_accounts[
                    job_id
                ][account_id] = {
                    "username": username,
                    "line_number": line_number
                }

                mark_account_prepared(
                    job_id=job_id,
                    account_id=account_id
                )

                print("=" * 60)

                print(
                    f"[JOB {job_id}] "
                    f"READY: {username}"
                )

                print(
                    f"[JOB {job_id}] "
                    "Browser/context remains "
                    "owned by worker."
                )

                print("=" * 60)

        except Exception as e:

            print(
                f"[JOB {job_id}] ERROR: "
                f"{type(e).__name__}: {e}"
            )

        finally:

            # Tell bot.py that preparation
            # has completely finished.

            preparation_event = (
                self.preparation_events.get(
                    job_id
                )
            )

            if preparation_event:
                preparation_event.set()

    # =========================
    # Wait For Preparation
    # =========================

    async def wait_for_preparation(
        self,
        job_id
    ):
        preparation_event = (
            self.preparation_events.get(
                job_id
            )
        )

        if not preparation_event:
            return

        print(
            f"[JOB {job_id}] "
            "Waiting for preparation..."
        )

        await preparation_event.wait()

        print(
            f"[JOB {job_id}] "
            "Preparation wait finished."
        )

    # =========================
    # Submit Code
    # =========================

    async def submit_code(
        self,
        job_id,
        code
    ):
        
        stop_event = self.stop_events.get(
            job_id
        )

        if not stop_event:

            print(
                f"[JOB {job_id}] "
                "Stop event not found."
            )

            return

        try:

            job = get_job(job_id)

            if not job:

                print(
                    f"[JOB {job_id}] "
                    "Job not found."
                )

                return

            if job["status"] != "running":

                print(
                    f"[JOB {job_id}] "
                    f"Cannot redeem. "
                    f"Status: {job['status']}"
                )

                return

            prepared = (
                self.prepared_accounts.get(
                    job_id,
                    {}
                )
            )

            if not prepared:

                print(
                    f"[JOB {job_id}] "
                    "No prepared accounts."
                )

                return

            print("=" * 60)

            print(
                f"[JOB {job_id}] "
                "Starting redemption..."
            )

            print("=" * 60)

            # =========================
            # PASS 1 — Submit All Codes
            # =========================

            print("=" * 60)
            print(
                f"[JOB {job_id}] "
                "PASS 1: Submitting codes..."
            )
            print("=" * 60)

            submission_results = {}

            for account_id, account_data in list(
                prepared.items()
            ):

                if stop_event.is_set():
                    break

                username = account_data["username"]

                print("=" * 60)
                print(
                    f"[JOB {job_id}] "
                    f"Submitting: {username}"
                )
                print(
                    f"[JOB {job_id}] "
                    f"Account ID: {account_id}"
                )
                print("=" * 60)

                try:
                    result = await self.run_worker(
                        submit_code,
                        account_id,
                        username,
                        code
                    )

                except Exception as e:
                    result = {
                        "success": False,
                        "error_code": "SUBMIT_EXCEPTION",
                        "error_message": (
                            f"{type(e).__name__}: {e}"
                        )
                    }

                    print(
                        f"[JOB {job_id}] "
                        f"❌ Submit exception for "
                        f"{username}: "
                        f"{type(e).__name__}: {e}"
                    )

                submission_results[account_id] = result

                print(
                    f"[JOB {job_id}] "
                    f"Submission result: {result}"
                )

                # A submission failure is already a final
                # redemption failure. Do not send it to PASS 2.
                if not result.get("success"):
                    finish_account(
                        job_id=job_id,
                        account_id=account_id,
                        success=False,
                        error_code=result.get(
                            "error_code"
                        ),
                        error_message=result.get(
                            "error_message"
                        )
                    )

            # =========================
            # PASS 2 — Confirm All Codes
            # =========================

            if not stop_event.is_set():

                print("=" * 60)
                print(
                    f"[JOB {job_id}] "
                    "PASS 2: Detecting Use buttons..."
                )
                print("=" * 60)

                for account_id, account_data in list(
                    prepared.items()
                ):

                    if stop_event.is_set():
                        break

                    submission = submission_results.get(
                        account_id
                    )

                    if (
                        not submission
                        or not submission.get("success")
                    ):
                        continue

                    username = account_data["username"]

                    print("=" * 60)
                    print(
                        f"[JOB {job_id}] "
                        f"Confirming: {username}"
                    )
                    print(
                        f"[JOB {job_id}] "
                        f"Account ID: {account_id}"
                    )
                    print("=" * 60)

                    try:
                        result = await self.run_worker(
                            confirm_code,
                            account_id,
                            username
                        )

                    except Exception as e:
                        result = {
                            "success": False,
                            "error_code": "CONFIRM_EXCEPTION",
                            "error_message": (
                                f"{type(e).__name__}: {e}"
                            )
                        }

                        print(
                            f"[JOB {job_id}] "
                            f"❌ Confirm exception for "
                            f"{username}: "
                            f"{type(e).__name__}: {e}"
                        )

                    print(
                        f"[JOB {job_id}] "
                        f"Confirmation result: {result}"
                    )

                    finish_account(
                        job_id=job_id,
                        account_id=account_id,
                        success=result.get("success", False),
                        error_code=result.get(
                            "error_code"
                        ),
                        error_message=result.get(
                            "error_message"
                        )
                    )

            # =========================
            # Mark Job Completed
            # =========================

            if not stop_event.is_set():
                mark_job_completed(job_id)

        finally:
                # =========================
                # Close All Prepared Accounts
                # =========================

                print("=" * 60)
                print(
                    f"[JOB {job_id}] "
                    "Closing prepared accounts..."
                )
                print("=" * 60)

                for account_id in list(prepared.keys()):

                    try:

                        await self.run_worker(
                            close_account,
                            account_id
                        )

                    except Exception as e:

                        print(
                            f"[JOB {job_id}] "
                            f"Failed closing account "
                            f"{account_id}: "
                            f"{type(e).__name__}: {e}"
                        )
                self.prepared_accounts.pop(
                    job_id,
                    None
                )

    # =========================
# Stop Preparation Only
# =========================

    async def stop_preparation(self, job_id):
        preparation_stop_event = (
            self.preparation_stop_events.get(job_id)
        )

        if not preparation_stop_event:
            return False

        print(
            f"[JOB {job_id}] "
            "Stopping preparation..."
        )

        # Tell preparation loop not to start
        # another account.
        preparation_stop_event.set()
        self.preparation_stopped_jobs.add(job_id)
        preparation_stop_event.set()
        task = self.tasks.get(job_id)

        if task:
            try:
                await task
            except asyncio.CancelledError:
                pass

        prepared = self.prepared_accounts.get(
            job_id,
            {}
        )

        print(
            f"[JOB {job_id}] "
            f"Preparation stopped. "
            f"Prepared accounts: {len(prepared)}"
        )

        self.preparation_stop_events.pop(
            job_id,
            None
        )

        self.tasks.pop(
            job_id,
            None
        )

        self.preparation_events.pop(
            job_id,
            None
        )

        # IMPORTANT:
        # Do NOT close prepared accounts.
        # Do NOT mark the job stopped.
        # The job remains available for redemption.

        return True
        
        # =========================
        # Stop Job
        # =========================

    async def stop_job(
            self,
            job_id
        ):
            stop_event = self.stop_events.get(
                job_id
            )

            if stop_event:
                stop_event.set()

            preparation_stop_event = (
                self.preparation_stop_events.get(job_id)
            )

            if preparation_stop_event:
                preparation_stop_event.set()
            
            
            prepared = (
                self.prepared_accounts.get(
                    job_id,
                    {}
                )
            )

            for account_id in list(
                prepared.keys()
            ):

                try:

                    await self.run_worker(
                        close_account,
                        account_id
                    )

                except Exception as e:

                    print(
                        f"[JOB {job_id}] "
                        f"Failed closing account "
                        f"{account_id}: "
                        f"{type(e).__name__}: {e}"
                    )

            self.prepared_accounts.pop(
                job_id,
                None
            )

            # =========================
            # Wait For Preparation Task
            # =========================

            task = self.tasks.get(
                job_id
            )

            if task:

                try:

                    await task

                except asyncio.CancelledError:
                    pass

            # =========================
            # Mark Job Stopped
            # =========================

            mark_job_stopped(
                job_id
            )

            # =========================
            # Cleanup
            # =========================

            self.tasks.pop(
                job_id,
                None
            )

            self.stop_events.pop(
                job_id,
                None
            )

            self.preparation_events.pop(
                job_id,
                None
            )
            
    def consume_preparation_stopped(self, job_id):
        if job_id in self.preparation_stopped_jobs:
            self.preparation_stopped_jobs.remove(job_id)
            return True

        return False        


job_manager = JobManager()