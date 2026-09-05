from __future__ import annotations

import json
import sys
import ctypes
from pathlib import Path
from threading import Event

from PySide6.QtCore import (
    QObject,
    QStandardPaths,
    QThread,
    QUrl,
    Qt,
    Signal,
    Slot,
)
from PySide6.QtGui import QDesktopServices, QIcon
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtWebEngineCore import (
    QWebEnginePage,
    QWebEngineProfile,
)
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import QApplication, QFileDialog, QMainWindow

from config import APP_NAME, APP_VERSION, GITHUB_OWNER, GITHUB_REPOSITORY
from core.downloader import (
    DownloadCancelled,
    DownloadEngine,
    default_download_directory,
    get_video_formats,
)
from core.video_loader import get_video_info
from core.user_data import UserDataStore
from updater.app_updater import update_application
from updater.component_updater import update_component
from updater.dependency_checker import check_all_as_dicts


class MetadataWorker(QObject):
    finished = Signal(dict)
    failed = Signal(str)

    def __init__(self, url: str):
        super().__init__()
        self.url = url

    @Slot()
    def run(self):
        try:
            self.finished.emit(
                get_video_info(self.url)
            )
        except Exception as exc:
            self.failed.emit(str(exc))


class FormatsWorker(QObject):
    finished = Signal(dict)
    failed = Signal(str)

    def __init__(self, url: str):
        super().__init__()
        self.url = url

    @Slot()
    def run(self):
        try:
            self.finished.emit(
                get_video_formats(self.url)
            )
        except Exception as exc:
            self.failed.emit(str(exc))


class DownloadWorker(QObject):
    progress = Signal(dict)
    finished = Signal(dict)
    failed = Signal(str)
    cancelled = Signal()

    def __init__(
        self,
        url: str,
        output_dir: str,
        video_selector: str,
        audio_selector: str,
        mode: str,
    ):
        super().__init__()
        self.url = url
        self.output_dir = output_dir
        self.video_selector = video_selector
        self.audio_selector = audio_selector
        self.mode = mode
        self.cancel_event = Event()
        self.engine: DownloadEngine | None = None

    def cancel(self):
        self.cancel_event.set()

        if self.engine:
            self.engine.cancel()

    @Slot()
    def run(self):
        def on_progress(payload: dict):
            self.progress.emit(payload)

        self.engine = DownloadEngine(
            url=self.url,
            output_dir=self.output_dir,
            video_selector=self.video_selector,
            audio_selector=self.audio_selector,
            mode=self.mode,
            progress_callback=on_progress,
            cancel_event=self.cancel_event,
        )

        try:
            result = self.engine.run()

            if self.cancel_event.is_set():
                self.cancelled.emit()
                return

            self.finished.emit(result)

        except DownloadCancelled:
            self.cancelled.emit()

        except Exception as exc:
            if self.cancel_event.is_set():
                self.cancelled.emit()
            else:
                self.failed.emit(str(exc))


class UpdateCheckWorker(QObject):
    finished = Signal(list)
    failed = Signal(str)

    @Slot()
    def run(self):
        try:
            self.finished.emit(
                check_all_as_dicts(
                    APP_VERSION
                )
            )
        except Exception as exc:
            self.failed.emit(str(exc))


class ComponentUpdateWorker(QObject):
    finished = Signal(dict)
    failed = Signal(str)

    def __init__(self, component_id: str):
        super().__init__()
        self.component_id = component_id

    @Slot()
    def run(self):
        try:
            self.finished.emit(
                update_component(
                    self.component_id
                )
            )
        except Exception as exc:
            self.failed.emit(str(exc))


class ApplicationUpdateWorker(QObject):
    finished = Signal(dict)
    failed = Signal(str)

    def __init__(self):
        super().__init__()

    @Slot()
    def run(self):
        try:
            self.finished.emit(
                update_application(
                    GITHUB_OWNER,
                    GITHUB_REPOSITORY,
                )
            )
        except Exception as exc:
            self.failed.emit(str(exc))


class YouLoadBridge(QObject):
    videoLoaded = Signal(dict)
    videoError = Signal(str)

    formatsReady = Signal(dict)
    formatsError = Signal(str)

    downloadProgress = Signal(dict)
    downloadFinished = Signal(dict)
    downloadError = Signal(str)
    downloadCancelled = Signal()
    downloadFolder = Signal(str)

    updatesReady = Signal(list)
    updatesError = Signal(str)

    componentUpdateReady = Signal(dict)
    componentUpdateError = Signal(str)

    applicationUpdateReady = Signal(dict)
    applicationUpdateError = Signal(str)
    userDataReady = Signal(dict)

    def __init__(self, user_data_store: UserDataStore):
        super().__init__()

        self.user_data_store = user_data_store

        self.videoThread = None
        self.videoWorker = None

        self.formatsThread = None
        self.formatsWorker = None

        self.downloadThread = None
        self.downloadWorker = None

        self.updateThread = None
        self.updateWorker = None

        self.componentThread = None
        self.componentWorker = None

        self.applicationThread = None
        self.applicationWorker = None

    @Slot()
    def getUserData(self):
        self.userDataReady.emit(
            self.user_data_store.load()
        )

    @Slot(str, str)
    def saveUserData(
        self,
        history_json: str,
        queue_json: str,
    ):
        try:
            history = json.loads(
                history_json
            )
            queue = json.loads(
                queue_json
            )

            if not isinstance(history, list):
                return

            if not isinstance(queue, list):
                return

            self.user_data_store.save(
                history,
                queue,
            )
        except (
            ValueError,
            json.JSONDecodeError,
        ):
            return

    @Slot(str)
    def openExternalUrl(self, url: str):
        value = str(url or "").strip()

        if not value.startswith(
            (
                "https://",
                "http://",
            )
        ):
            return

        QDesktopServices.openUrl(
            QUrl(value)
        )

    @Slot(str)
    def loadVideo(self, url: str):
        if self._thread_running(
            self.videoThread
        ):
            return

        self.videoThread = QThread()
        self.videoWorker = MetadataWorker(url)
        self.videoWorker.moveToThread(
            self.videoThread
        )

        self.videoThread.started.connect(
            self.videoWorker.run
        )
        self.videoWorker.finished.connect(
            self.videoLoaded.emit
        )
        self.videoWorker.failed.connect(
            self.videoError.emit
        )
        self.videoWorker.finished.connect(
            self.videoThread.quit
        )
        self.videoWorker.failed.connect(
            self.videoThread.quit
        )
        self.videoThread.finished.connect(
            self._clear_video_worker
        )
        self.videoThread.start()

    @Slot(str)
    def getVideoFormats(self, url: str):
        if self._thread_running(
            self.formatsThread
        ):
            return

        self.formatsThread = QThread()
        self.formatsWorker = FormatsWorker(url)
        self.formatsWorker.moveToThread(
            self.formatsThread
        )

        self.formatsThread.started.connect(
            self.formatsWorker.run
        )
        self.formatsWorker.finished.connect(
            self.formatsReady.emit
        )
        self.formatsWorker.failed.connect(
            self.formatsError.emit
        )
        self.formatsWorker.finished.connect(
            self.formatsThread.quit
        )
        self.formatsWorker.failed.connect(
            self.formatsThread.quit
        )
        self.formatsThread.finished.connect(
            self._clear_formats_worker
        )
        self.formatsThread.start()

    @Slot(str, str, str, str, str)
    def startDownload(
        self,
        url: str,
        video_selector: str,
        audio_selector: str,
        mode: str,
        output_dir: str,
    ):
        if self._thread_running(
            self.downloadThread
        ):
            self.downloadError.emit(
                "A download is already running."
            )
            return

        directory = (
            Path(output_dir)
            if output_dir
            else default_download_directory()
        )

        self.downloadThread = QThread()
        self.downloadWorker = DownloadWorker(
            url=url,
            output_dir=str(directory),
            video_selector=video_selector,
            audio_selector=audio_selector,
            mode=mode,
        )

        self.downloadWorker.moveToThread(
            self.downloadThread
        )

        self.downloadThread.started.connect(
            self.downloadWorker.run
        )

        self.downloadWorker.progress.connect(
            self.downloadProgress.emit
        )
        self.downloadWorker.finished.connect(
            self.downloadFinished.emit
        )
        self.downloadWorker.failed.connect(
            self.downloadError.emit
        )
        self.downloadWorker.cancelled.connect(
            self.downloadCancelled.emit
        )

        self.downloadWorker.finished.connect(
            self.downloadThread.quit
        )
        self.downloadWorker.failed.connect(
            self.downloadThread.quit
        )
        self.downloadWorker.cancelled.connect(
            self.downloadThread.quit
        )

        self.downloadThread.finished.connect(
            self._clear_download_worker
        )

        self.downloadThread.start()

    @Slot()
    def cancelDownload(self):
        if self.downloadWorker:
            self.downloadWorker.cancel()

    @Slot()
    def getDownloadFolder(self):
        self.downloadFolder.emit(
            str(
                default_download_directory()
            )
        )

    @Slot()
    def chooseDownloadFolder(self):
        directory = QFileDialog.getExistingDirectory(
            None,
            "Choose download folder",
            str(
                default_download_directory()
            ),
        )

        if directory:
            self.downloadFolder.emit(
                directory
            )

    @Slot(str)
    def openDownloadFolder(self, path: str):
        target = Path(path)

        if target.is_file():
            target = target.parent

        target.mkdir(
            parents=True,
            exist_ok=True,
        )

        QDesktopServices.openUrl(
            QUrl.fromLocalFile(
                str(target)
            )
        )

    @Slot()
    def checkForUpdates(self):
        if self._thread_running(
            self.updateThread
        ):
            return

        self.updateThread = QThread()
        self.updateWorker = UpdateCheckWorker()
        self.updateWorker.moveToThread(
            self.updateThread
        )

        self.updateThread.started.connect(
            self.updateWorker.run
        )
        self.updateWorker.finished.connect(
            self.updatesReady.emit
        )
        self.updateWorker.failed.connect(
            self.updatesError.emit
        )
        self.updateWorker.finished.connect(
            self.updateThread.quit
        )
        self.updateWorker.failed.connect(
            self.updateThread.quit
        )
        self.updateThread.finished.connect(
            self._clear_update_worker
        )
        self.updateThread.start()

    @Slot(str)
    def updateComponent(self, component_id: str):
        if self._thread_running(
            self.componentThread
        ):
            return

        self.componentThread = QThread()
        self.componentWorker = ComponentUpdateWorker(
            component_id
        )
        self.componentWorker.moveToThread(
            self.componentThread
        )

        self.componentThread.started.connect(
            self.componentWorker.run
        )
        self.componentWorker.finished.connect(
            self.componentUpdateReady.emit
        )
        self.componentWorker.failed.connect(
            self.componentUpdateError.emit
        )
        self.componentWorker.finished.connect(
            self.componentThread.quit
        )
        self.componentWorker.failed.connect(
            self.componentThread.quit
        )
        self.componentThread.finished.connect(
            self._clear_component_worker
        )
        self.componentThread.start()

    @Slot()
    def updateApplication(self):
        if self._thread_running(
            self.applicationThread
        ):
            return

        self.applicationThread = QThread()
        self.applicationWorker = ApplicationUpdateWorker()
        self.applicationWorker.moveToThread(
            self.applicationThread
        )

        self.applicationThread.started.connect(
            self.applicationWorker.run
        )
        self.applicationWorker.finished.connect(
            self.applicationUpdateReady.emit
        )
        self.applicationWorker.failed.connect(
            self.applicationUpdateError.emit
        )
        self.applicationWorker.finished.connect(
            self.applicationThread.quit
        )
        self.applicationWorker.failed.connect(
            self.applicationThread.quit
        )
        self.applicationThread.finished.connect(
            self._clear_application_worker
        )
        self.applicationThread.start()

    @staticmethod
    def _thread_running(thread):
        return bool(
            thread
            and thread.isRunning()
        )

    def _clear_video_worker(self):
        if self.videoWorker:
            self.videoWorker.deleteLater()

        if self.videoThread:
            self.videoThread.deleteLater()

        self.videoWorker = None
        self.videoThread = None

    def _clear_formats_worker(self):
        if self.formatsWorker:
            self.formatsWorker.deleteLater()

        if self.formatsThread:
            self.formatsThread.deleteLater()

        self.formatsWorker = None
        self.formatsThread = None

    def _clear_download_worker(self):
        if self.downloadWorker:
            self.downloadWorker.deleteLater()

        if self.downloadThread:
            self.downloadThread.deleteLater()

        self.downloadWorker = None
        self.downloadThread = None

    def _clear_update_worker(self):
        if self.updateWorker:
            self.updateWorker.deleteLater()

        if self.updateThread:
            self.updateThread.deleteLater()

        self.updateWorker = None
        self.updateThread = None

    def _clear_component_worker(self):
        if self.componentWorker:
            self.componentWorker.deleteLater()

        if self.componentThread:
            self.componentThread.deleteLater()

        self.componentWorker = None
        self.componentThread = None

    def _clear_application_worker(self):
        if self.applicationWorker:
            self.applicationWorker.deleteLater()

        if self.applicationThread:
            self.applicationThread.deleteLater()

        self.applicationWorker = None
        self.applicationThread = None


class YouLoadWebView(QWebEngineView):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setContextMenuPolicy(
            Qt.ContextMenuPolicy.NoContextMenu
        )


class YouLoadWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle(
            f"{APP_NAME} • {APP_VERSION}"
        )
        self.resize(1280, 820)
        self.setMinimumSize(1000, 700)

        self.view = YouLoadWebView(self)
        self.setCentralWidget(self.view)

        # Use an explicit named persistent WebEngine profile.
        # This keeps browser storage separate from the temporary
        # off-the-record profile used by Qt's default profile.
        app_data_dir = Path(
            QStandardPaths.writableLocation(
                QStandardPaths.AppLocalDataLocation
            )
        )

        webengine_dir = (
            app_data_dir / "webengine"
        )

        cache_dir = (
            app_data_dir / "cache"
        )

        webengine_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        cache_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.web_profile = QWebEngineProfile(
            "YouLoad",
            self,
        )

        self.web_profile.setPersistentStoragePath(
            str(webengine_dir)
        )

        self.web_profile.setCachePath(
            str(cache_dir)
        )

        self.web_profile.setPersistentCookiesPolicy(
            QWebEngineProfile.PersistentCookiesPolicy.ForcePersistentCookies
        )

        self.web_page = QWebEnginePage(
            self.web_profile,
            self.view,
        )

        self.view.setPage(
            self.web_page
        )

        self.channel = QWebChannel(
            self.web_page
        )

        self.user_data_store = UserDataStore(
            app_data_dir / "user_data.json"
        )

        self.bridge = YouLoadBridge(
            self.user_data_store
        )

        self.channel.registerObject(
            "youLoad",
            self.bridge,
        )

        self.view.page().setWebChannel(
            self.channel
        )

        self.bridge.videoLoaded.connect(
            lambda data: self._run_javascript(
                "window.YouLoad && "
                f"window.YouLoad.onVideoLoaded({json.dumps(data)});"
            )
        )

        self.bridge.videoError.connect(
            lambda message: self._run_javascript(
                "window.YouLoad && "
                f"window.YouLoad.onVideoError({json.dumps(message)});"
            )
        )

        self.bridge.formatsReady.connect(
            lambda data: self._run_javascript(
                "window.YouLoad && "
                f"window.YouLoad.onFormatsReady({json.dumps(data)});"
            )
        )

        self.bridge.formatsError.connect(
            lambda message: self._run_javascript(
                "window.YouLoad && "
                f"window.YouLoad.onFormatsError({json.dumps(message)});"
            )
        )

        self.bridge.downloadProgress.connect(
            lambda data: self._run_javascript(
                "window.YouLoad && "
                f"window.YouLoad.onDownloadProgress({json.dumps(data)});"
            )
        )

        self.bridge.downloadFinished.connect(
            lambda data: self._run_javascript(
                "window.YouLoad && "
                f"window.YouLoad.onDownloadFinished({json.dumps(data)});"
            )
        )

        self.bridge.downloadError.connect(
            lambda message: self._run_javascript(
                "window.YouLoad && "
                f"window.YouLoad.onDownloadError({json.dumps(message)});"
            )
        )

        self.bridge.downloadCancelled.connect(
            lambda: self._run_javascript(
                "window.YouLoad && "
                "window.YouLoad.onDownloadCancelled();"
            )
        )

        self.bridge.downloadFolder.connect(
            lambda path: self._run_javascript(
                "window.YouLoad && "
                f"window.YouLoad.onDownloadFolder({json.dumps(path)});"
            )
        )

        self.bridge.updatesReady.connect(
            lambda data: self._run_javascript(
                "window.YouLoad && "
                f"window.YouLoad.onUpdatesReady({json.dumps(data)});"
            )
        )

        self.bridge.updatesError.connect(
            lambda message: self._run_javascript(
                "window.YouLoad && "
                f"window.YouLoad.onUpdatesError({json.dumps(message)});"
            )
        )

        self.bridge.componentUpdateReady.connect(
            lambda data: self._run_javascript(
                "window.YouLoad && "
                f"window.YouLoad.onComponentUpdateReady({json.dumps(data)});"
            )
        )

        self.bridge.componentUpdateError.connect(
            lambda message: self._run_javascript(
                "window.YouLoad && "
                f"window.YouLoad.onComponentUpdateError({json.dumps(message)});"
            )
        )

        self.bridge.applicationUpdateReady.connect(
            lambda data: self._run_javascript(
                "window.YouLoad && "
                f"window.YouLoad.onApplicationUpdateReady({json.dumps(data)});"
            )
        )

        self.bridge.applicationUpdateError.connect(
            lambda message: self._run_javascript(
                "window.YouLoad && "
                f"window.YouLoad.onApplicationUpdateError({json.dumps(message)});"
            )
        )

        self.bridge.userDataReady.connect(
            lambda data: self._run_javascript(
                "window.YouLoad && "
                f"window.YouLoad.onUserDataReady({json.dumps(data)});"
            )
        )

        page = (
            Path(__file__).resolve().parent
            / "ui"
            / "index.html"
        )

        self.web_page.load(
            QUrl.fromLocalFile(
                str(page)
            )
        )

    def _run_javascript(
        self,
        script: str,
    ):
        self.view.page().runJavaScript(
            script
        )


def _set_windows_app_id():
    if sys.platform != "win32":
        return

    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
            "Nispax.YouLoad"
        )
    except (AttributeError, OSError):
        pass


def _icon_path() -> Path:
    return (
        Path(__file__).resolve().parent
        / "ui"
        / "assets"
        / "youload-icon.png"
    )

def main():
    _set_windows_app_id()

    app = QApplication(sys.argv)

    app.setOrganizationName(
        "NISPAX InfoTech"
    )

    app.setOrganizationDomain(
        "nispax.in"
    )

    app.setApplicationName(
        APP_NAME
    )

    app.setApplicationVersion(
        APP_VERSION
    )

    icon = QIcon(str(_icon_path()))
    app.setWindowIcon(icon)

    window = YouLoadWindow()
    window.setWindowIcon(icon)
    window.show()

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
