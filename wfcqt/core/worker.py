"""QRunnable wrapper to execute WFC work in a thread pool."""
# pylint: disable=no-name-in-module

from PySide6.QtCore import Slot, QRunnable

from wfcqt.wfc.solver import Cancelled


class WFCWorker(QRunnable):  # pylint: disable=too-few-public-methods
    """Run a callable in a Qt thread pool with cancellation handling."""

    def __init__(self, fn, *args, **kwargs):
        """Store function and its args for deferred execution."""
        super().__init__()
        self.fn = fn
        self.args = args
        self.kwargs = kwargs

    @Slot()
    def run(self):
        """Run the task, returning None if cancelled."""
        try:
            return self.fn(*self.args, **self.kwargs)
        except Cancelled:
            return None
