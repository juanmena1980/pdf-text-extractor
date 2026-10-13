from __future__ import annotations

import threading
import traceback

from . import delivery


class Scheduler:
    def __init__(self) -> None:
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._loop, name="sintesis-envio", daemon=True)

    def start(self) -> None:
        if not self._thread.is_alive():
            self._thread.start()

    def _loop(self) -> None:
        while not self._stop.wait(15):
            try:
                delivery.dispatch_due()
            except Exception:
                traceback.print_exc()
