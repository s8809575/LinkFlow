import sys
import os

os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = "--disable-gpu --disable-software-rasterizer --disable-gpu-compositing --disable-features=VizDisplayCompositor"
os.environ["QT_OPENGL"] = "software"
os.environ["QT_QUICK_BACKEND"] = "software"

try:
    from PyQt5.QtWidgets import (
        QMainWindow, QToolBar, QLineEdit, QStatusBar,
        QAction, QApplication, QWidget, QVBoxLayout, QPushButton, QLabel, QHBoxLayout,
        QFileDialog
    )
    from PyQt5.QtWebEngineWidgets import QWebEngineView
    from PyQt5.QtCore import QUrl, Qt, QTimer, QObject, pyqtSlot, QVariant
    from PyQt5.QtGui import QIcon, QDesktopServices
    from PyQt5.QtWebChannel import QWebChannel
    QT_AVAILABLE = True
except ImportError:
    QT_AVAILABLE = False


class FileDialogBridge(QObject):
    def __init__(self, parent=None):
        super().__init__(parent)

    @pyqtSlot(result=str)
    def selectFolder(self):
        folder_path = QFileDialog.getExistingDirectory(
            None,
            "选择文件夹",
            "",
            QFileDialog.ShowDirsOnly | QFileDialog.DontResolveSymlinks
        )
        return folder_path


class LinkFlowMainWindow(QMainWindow):
    def __init__(self, url='http://localhost:8766/desktop', parent=None):
        super().__init__(parent)
        self.setWindowTitle("LinkFlow")
        self.resize(1200, 800)
        
        self.web_view = QWebEngineView()
        self.channel = QWebChannel()
        self.file_dialog_bridge = FileDialogBridge()
        
        self._setup_ui()
        self._setup_web_engine_settings()
        self._setup_javascript_bridge()
        
        self.load_url(url)
        
        QTimer.singleShot(5000, self._check_page_load)

    def _setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        toolbar = QToolBar()
        toolbar.setMovable(False)
        
        back_action = QAction("←", self)
        back_action.triggered.connect(self.web_view.back)
        toolbar.addAction(back_action)
        
        forward_action = QAction("→", self)
        forward_action.triggered.connect(self.web_view.forward)
        toolbar.addAction(forward_action)
        
        refresh_action = QAction("↻", self)
        refresh_action.triggered.connect(self.web_view.reload)
        toolbar.addAction(refresh_action)
        
        toolbar.addSeparator()
        
        self.url_edit = QLineEdit()
        self.url_edit.returnPressed.connect(self._on_url_enter)
        toolbar.addWidget(self.url_edit)
        
        self.addToolBar(toolbar)
        
        layout.addWidget(self.web_view)
        
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("就绪")
        
        self.web_view.titleChanged.connect(self.setWindowTitle)
        self.web_view.urlChanged.connect(self._on_url_changed)
        self.web_view.loadStarted.connect(self._on_load_started)
        self.web_view.loadFinished.connect(self._on_load_finished)
        self.web_view.loadProgress.connect(self._on_load_progress)
        self.web_view.renderProcessTerminated.connect(self._on_render_crash)

    def _setup_web_engine_settings(self):
        settings = self.web_view.settings()
        settings.setAttribute(settings.JavascriptEnabled, True)
        settings.setAttribute(settings.LocalContentCanAccessRemoteUrls, False)
        settings.setAttribute(settings.AllowRunningInsecureContent, False)
        settings.setAttribute(settings.JavascriptCanAccessClipboard, True)
        settings.setAttribute(settings.JavascriptCanOpenWindows, False)
        settings.setAttribute(settings.Accelerated2dCanvasEnabled, False)
        settings.setAttribute(settings.WebGLEnabled, False)
        settings.setAttribute(settings.FullScreenSupportEnabled, False)

    def _setup_javascript_bridge(self):
        self.channel.registerObject('fileDialogBridge', self.file_dialog_bridge)
        self.web_view.page().setWebChannel(self.channel)

    def load_url(self, url):
        self.url_edit.setText(url)
        self.web_view.load(QUrl(url))

    def _on_url_enter(self):
        url = self.url_edit.text().strip()
        if url:
            if not url.startswith('http://') and not url.startswith('https://'):
                url = 'http://' + url
            self.web_view.load(QUrl(url))

    def _on_url_changed(self, url):
        self.url_edit.setText(url.toString())

    def _on_load_started(self):
        self.status_bar.showMessage("加载中...")

    def _on_load_finished(self, ok):
        if ok:
            self.status_bar.showMessage("加载完成")
        else:
            self.status_bar.showMessage("加载失败")
            self._show_error_page()

    def _on_load_progress(self, progress):
        self.status_bar.showMessage(f"加载中: {progress}%")

    def _on_render_crash(self, process_id, exit_code):
        self.status_bar.showMessage(f"渲染进程崩溃 (PID: {process_id}, 退出码: {exit_code})")
        self._show_error_page()

    def _check_page_load(self):
        if self.web_view.url().toString() == "about:blank":
            self.status_bar.showMessage("页面加载超时，尝试重新加载...")
            QTimer.singleShot(1000, lambda: self.load_url(self.url_edit.text()))

    def _show_error_page(self):
        error_html = """
        <html>
        <head><title>加载失败</title></head>
        <body style="text-align:center; padding:50px; font-family:Arial;">
        <h1>页面加载失败</h1>
        <p>无法加载页面，请检查网络连接或服务是否正常运行。</p>
        <button onclick="window.location.reload()" style="padding:10px 20px; font-size:16px;">
            重新加载
        </button>
        </body>
        </html>
        """
        self.web_view.setHtml(error_html)

    def closeEvent(self, event):
        self.web_view.stop()
        event.accept()


def run_qt_app(url='http://localhost:8766/desktop'):
    if not QT_AVAILABLE:
        raise ImportError("PyQt5 或 PyQtWebEngine 未安装")
    
    os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = "--disable-gpu --disable-software-rasterizer --disable-gpu-compositing --disable-features=VizDisplayCompositor"
    os.environ["QT_OPENGL"] = "software"
    
    QApplication.setAttribute(Qt.AA_UseSoftwareOpenGL)
    from PyQt5.QtGui import QSurfaceFormat
    sf = QSurfaceFormat()
    sf.setRenderableType(QSurfaceFormat.OpenGLES)
    sf.setVersion(2, 0)
    sf.setSwapInterval(0)
    QSurfaceFormat.setDefaultFormat(sf)
    app = QApplication(sys.argv)
    
    from PyQt5.QtWebEngineWidgets import QWebEngineProfile
    profile = QWebEngineProfile.defaultProfile()
    profile.clearHttpCache()
    profile.setHttpCacheType(QWebEngineProfile.NoCache)
    
    window = LinkFlowMainWindow(url)
    window.show()
    return app.exec_()


if __name__ == "__main__":
    run_qt_app()