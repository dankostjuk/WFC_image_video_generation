from PySide6.QtWidgets import QApplication
import sys
from wfcqt.ui.main_window import MainWindow

def main() -> int:
    app: QApplication
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    return app.exec()

if __name__ == "__main__":
    raise SystemExit(main())
