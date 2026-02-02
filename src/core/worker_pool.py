from concurrent.futures import ThreadPoolExecutor, Future, as_completed
from typing import Callable, Iterator, Optional
from queue import Queue, Empty
import threading
import logging
import os
import time

from src.models.conversion_task import ConversionTask
from src.models.conversion_result import ConversionResult
from src.core.converter import HEICConverter

logger = logging.getLogger(__name__)


class WorkerPool:
    """
    Manages a pool of worker threads for parallel image conversion.
    Supports pause, resume, and stop operations.
    """

    def __init__(self, max_workers: Optional[int] = None):
        """
        Initialize worker pool.

        Args:
            max_workers: Maximum number of worker threads (None = auto-detect)
        """
        if max_workers is None:
            max_workers = min(32, (os.cpu_count() or 4) * 2)

        self.max_workers = max_workers
        self.executor: Optional[ThreadPoolExecutor] = None
        self.is_paused = threading.Event()
        self.is_paused.set()  # Start unpaused
        self.is_stopped = threading.Event()
        self.active_futures: list[Future] = []
        self._pause_callback = None
        self._pause_notified = False
        self._in_flight = 0
        self._in_flight_lock = threading.Lock()

        logger.info(f"WorkerPool initialized with {self.max_workers} workers")

    def process_tasks(
        self,
        tasks: Iterator[ConversionTask],
        result_callback: Callable[[ConversionResult], None],
        batch_size: int = 100,
        pause_callback: Optional[Callable[[], None]] = None
    ) -> None:
        """
        Process conversion tasks using the worker pool.

        Args:
            tasks: Iterator of ConversionTask objects
            result_callback: Function to call with each ConversionResult
            batch_size: Number of tasks to queue at once (memory management)
        """
        self.is_stopped.clear()
        self.is_paused.set()  # Start unpaused
        self._pause_callback = pause_callback
        self._pause_notified = False

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            self.executor = executor
            self.active_futures = []

            try:
                task_batch = []

                for task in tasks:
                    # Check if stopped
                    if self.is_stopped.is_set():
                        logger.info("Worker pool stopped by user")
                        break

                    # Wait if paused
                    self.is_paused.wait()

                    # Add task to batch
                    task_batch.append(task)

                    # Submit batch when it reaches batch_size
                    if len(task_batch) >= batch_size:
                        self._submit_batch(task_batch, result_callback)
                        task_batch = []

                # Submit remaining tasks
                if task_batch and not self.is_stopped.is_set():
                    self._submit_batch(task_batch, result_callback)

                # Wait for all remaining futures to complete
                self._wait_for_completion(result_callback)

            finally:
                self.executor = None
                self.active_futures = []
                self._pause_callback = None
                self._pause_notified = False

        logger.info("Worker pool processing complete")

    def _submit_batch(
        self,
        tasks: list[ConversionTask],
        result_callback: Callable[[ConversionResult], None]
    ) -> None:
        """Submit a batch of tasks to the executor."""
        for task in tasks:
            if self.is_stopped.is_set():
                break

            future = self.executor.submit(self._process_task_with_pause, task)
            self.active_futures.append(future)

        # Process completed futures
        self._collect_completed_results(result_callback)

    def _process_task_with_pause(self, task: ConversionTask) -> ConversionResult:
        """
        Process a single task, respecting pause state.

        Args:
            task: ConversionTask to process

        Returns:
            ConversionResult
        """
        # Wait if paused
        self.is_paused.wait()

        # Check if stopped
        if self.is_stopped.is_set():
            return ConversionResult(
                success=False,
                input_path=task.input_path,
                error="Processing stopped by user"
            )

        # Perform conversion
        with self._in_flight_lock:
            self._in_flight += 1
        try:
            result = HEICConverter.convert(task)
        finally:
            with self._in_flight_lock:
                self._in_flight -= 1
            self._maybe_emit_paused()

        # Handle source file deletion if successful and requested
        if result.success and task.delete_source:
            try:
                import send2trash
                send2trash.send2trash(str(task.input_path))
                logger.info(f"Moved to recycle bin: {task.input_path}")
            except Exception as e:
                logger.warning(f"Could not delete source file {task.input_path}: {e}")

        return result

    def _collect_completed_results(
        self,
        result_callback: Callable[[ConversionResult], None]
    ) -> None:
        """Collect and process completed futures."""
        completed = [f for f in self.active_futures if f.done()]

        for future in completed:
            try:
                result = future.result()
                result_callback(result)
            except Exception as e:
                logger.error(f"Error processing result: {e}")

            self.active_futures.remove(future)
        self._maybe_emit_paused()

    def _wait_for_completion(
        self,
        result_callback: Callable[[ConversionResult], None]
    ) -> None:
        """Wait for all active futures to complete."""
        for future in as_completed(self.active_futures):
            try:
                result = future.result()
                result_callback(result)
            except Exception as e:
                logger.error(f"Error processing result: {e}")

        self.active_futures = []
        self._maybe_emit_paused()

    def pause(self) -> None:
        """Pause processing. Workers will finish current tasks then wait."""
        if not self.is_paused.is_set():
            logger.info("Worker pool already paused")
            return

        logger.info("Pausing worker pool")
        self.is_paused.clear()

    def resume(self) -> None:
        """Resume processing after pause."""
        if self.is_paused.is_set():
            logger.info("Worker pool already running")
            return

        logger.info("Resuming worker pool")
        self.is_paused.set()

    def stop(self) -> None:
        """
        Stop processing immediately.
        Current tasks will finish, but no new tasks will start.
        """
        logger.info("Stopping worker pool")
        self.is_stopped.set()
        self.is_paused.set()  # Resume if paused to allow stopping

    def is_running(self) -> bool:
        """Check if worker pool is currently processing."""
        return self.executor is not None and not self.is_stopped.is_set()

    def is_paused_state(self) -> bool:
        """Check if worker pool is paused."""
        return not self.is_paused.is_set()

    def get_active_task_count(self) -> int:
        """Get number of tasks currently being processed."""
        return len([f for f in self.active_futures if not f.done()])

    def get_in_flight_count(self) -> int:
        """Get number of tasks actively converting (not waiting on pause)."""
        with self._in_flight_lock:
            return self._in_flight

    def _maybe_emit_paused(self):
        if self._pause_notified:
            return
        if self.is_paused.is_set():
            return
        if self.get_in_flight_count() != 0:
            return
        if self._pause_callback:
            self._pause_notified = True
            try:
                self._pause_callback()
            except Exception:
                pass

    def wait_for_idle(self, check_interval: float = 0.2) -> None:
        """Block until no active tasks remain or stop is requested."""
        while True:
            if self.is_stopped.is_set():
                break
            if self.get_active_task_count() == 0:
                break
            time.sleep(check_interval)


class WorkerPoolStats:
    """Track statistics for worker pool processing."""

    def __init__(self):
        self.total_processed = 0
        self.successful = 0
        self.failed = 0
        self.total_time = 0.0
        self.lock = threading.Lock()

    def add_result(self, result: ConversionResult) -> None:
        """Add a result to the statistics."""
        with self.lock:
            self.total_processed += 1
            if result.success:
                self.successful += 1
            else:
                self.failed += 1

            if result.conversion_time:
                self.total_time += result.conversion_time

    def get_stats(self) -> dict:
        """Get current statistics as a dictionary."""
        with self.lock:
            return {
                'total_processed': self.total_processed,
                'successful': self.successful,
                'failed': self.failed,
                'success_rate': f"{(self.successful / self.total_processed * 100):.1f}%" if self.total_processed > 0 else "0%",
                'total_time_seconds': self.total_time,
                'avg_time_per_file': f"{(self.total_time / self.total_processed):.3f}s" if self.total_processed > 0 else "0s"
            }

    def reset(self) -> None:
        """Reset all statistics."""
        with self.lock:
            self.total_processed = 0
            self.successful = 0
            self.failed = 0
            self.total_time = 0.0
