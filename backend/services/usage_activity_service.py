from queue import Empty, Full, Queue
import threading

from extensions import db
from models.auth import UsageActivity


class UsageActivityRecorder:
    def __init__(self, app, batch_size=50, flush_interval_seconds=0.75, queue_size=5000):
        self._app = app
        self._batch_size = batch_size
        self._flush_interval_seconds = flush_interval_seconds
        self._queue = Queue(maxsize=queue_size)
        self._started = False
        self._start_lock = threading.Lock()

    def start(self):
        with self._start_lock:
            if self._started:
                return
            self._started = True
            threading.Thread(
                target=self._run,
                daemon=True,
                name="usage-activity-recorder",
            ).start()

    def enqueue(self, event):
        self.start()
        try:
            self._queue.put_nowait(event)
            return True
        except Full:
            self._app.logger.warning("Usage activity queue is full; dropping one event.")
            return False

    def _run(self):
        while True:
            try:
                first_event = self._queue.get(timeout=self._flush_interval_seconds)
            except Empty:
                continue

            batch = [first_event]
            while len(batch) < self._batch_size:
                try:
                    batch.append(self._queue.get_nowait())
                except Empty:
                    break

            try:
                with self._app.app_context():
                    db.session.bulk_insert_mappings(UsageActivity, batch)
                    db.session.commit()
            except Exception:
                with self._app.app_context():
                    db.session.rollback()
                self._app.logger.exception("Could not persist usage activity batch.")
            finally:
                for _ in batch:
                    self._queue.task_done()


def initialize_usage_activity_recorder(app):
    recorder = app.extensions.get("usage_activity_recorder")
    if recorder is None:
        recorder = UsageActivityRecorder(app)
        app.extensions["usage_activity_recorder"] = recorder
    recorder.start()
    return recorder


def enqueue_usage_activity(app, event):
    recorder = app.extensions.get("usage_activity_recorder")
    if recorder is None:
        recorder = initialize_usage_activity_recorder(app)
    return recorder.enqueue(event)
