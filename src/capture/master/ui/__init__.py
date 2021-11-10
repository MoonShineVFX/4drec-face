"""圖形介面

採用 Qt 的主介面
藉由 UIEvent 來跟外部溝通

"""
import threading
import sys
import os
from PyQt5.Qt import QApplication, QIcon, QPixmap, QSplashScreen
from PyQt5 import QtCore

from utility.logger import log
from utility.define import UIEventType

from .theme import apply_theme
from .main import MainWindow


class MasterUI(threading.Thread):
    """主介面控制

    將介面分離主執行緒來執行
    屬性皆取自 MainUI

    """

    def __init__(self, lock):
        super().__init__()
        self._lock = lock
        self._main = None

        # 直接開始執行
        self.start()

    def __getattr__(self, prop):
        if self._main is None:
            raise AttributeError("Main UI isn't initialized")
        return getattr(self._main, prop)

    def run(self):
        # Catch QT exception
        sys._excepthook = sys.excepthook
        sys.excepthook = self._qt_exception_hook

        # Execute QT
        os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"
        app = QApplication(sys.argv)
        app.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling)
        app.setWindowIcon(QIcon('source/icon/ico.svg'))
        apply_theme(app)

        # Splash Screen
        splash_pix = QPixmap('source/splash.png')
        splash = QSplashScreen(
            splash_pix, QtCore.Qt.WindowStaysOnTopHint
        )
        splash.show()

        log.info('Initialize UI')
        main_window = MainWindow(splash)

        self._main = main_window
        self._lock.acquire()
        self._lock.notify()
        self._lock.release()

        sys.exit(app.exec_())

    @staticmethod
    def _qt_exception_hook(_type, value, traceback):
        print(_type, value, traceback)
        # Call the normal Exception hook after
        sys._excepthook(_type, value, traceback)
        sys.exit(1)

    def show(self):
        self._main.dispatch_event(UIEventType.UI_SHOW)


lock = threading.Condition()
ui = MasterUI(lock)  # 單一實例
lock.acquire()
lock.wait()
lock.release()
