"""喝 水 啦 —— 儿童喝水养成游戏  Kivy App 入口"""

import os
from kivy.app import App
from kivy.core.text import LabelBase
from kivy.lang import Builder
from kivy.properties import ObjectProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.popup import Popup

from src.viewmodel.main_viewmodel import MainViewModel

KV_PATH = "src/view/main_screen.kv"
SETTINGS_KV_PATH = "src/view/settings_dialog.kv"

# ── 注册中文字体 ──
_FONT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_FONT_HEI = os.path.join(_FONT_DIR, "SiYuanHeiTi-Regular", "SourceHanSansSC-Regular-2.otf")
_FONT_SONG = os.path.join(_FONT_DIR, "思源宋体 (行高修正版)_2.003", "思源宋体.otf")

LabelBase.register(name="ChineseHei", fn_regular=_FONT_HEI)
LabelBase.register(name="ChineseSong", fn_regular=_FONT_SONG)


class VerifyPopup(Popup):
    """Arithmetic-verification popup before settings access."""
    settings_vm = ObjectProperty(None)

    def on_verify(self) -> None:
        if self.settings_vm.check_verification():
            self.dismiss()
            settings = SettingsPopup(settings_vm=self.settings_vm)
            settings.open()
        # on failure, error message is set on settings_vm.verify_error,
        # the label binding will display it. Question regenerated automatically.


class SettingsPopup(Popup):
    """Parent settings popup — sliders, nickname, sound, reset."""
    settings_vm = ObjectProperty(None)

    def on_save(self) -> None:
        self.settings_vm.save()
        self.dismiss()
        # trigger main viewmodel reload
        app = App.get_running_app()
        if app and hasattr(app, 'root') and hasattr(app.root, 'on_settings_saved'):
            app.root.on_settings_saved()

    def on_reset(self) -> None:
        self.settings_vm.reset_data()
        self.settings_vm.save()
        self.dismiss()
        app = App.get_running_app()
        if app and hasattr(app, 'root') and hasattr(app.root, 'on_settings_saved'):
            app.root.on_settings_saved()


class MainScreen(BoxLayout):
    """Root widget; ViewModel injected by App."""

    def __init__(self, viewmodel: MainViewModel, **kwargs):
        self.vm = viewmodel  # must be set before super() — kv rules access root.vm
        super().__init__(**kwargs)

    def open_settings(self) -> None:
        """Open the settings flow: verify → settings dialog."""
        from src.viewmodel.settings_viewmodel import SettingsViewModel
        svm = SettingsViewModel(self.vm.config, self.vm.data_dir)
        verify = VerifyPopup(settings_vm=svm)
        verify.open()

    def on_settings_saved(self) -> None:
        """Called after settings are saved — flush state, then reload config."""
        self.vm.save_state()
        self.vm.reload_config()


class DrinkLaApp(App):
    """Kivy application entry point."""

    def build(self):
        Builder.load_file(SETTINGS_KV_PATH)
        Builder.load_file(KV_PATH)
        self.vm = MainViewModel()
        self.vm.load_state(self.user_data_dir)
        return MainScreen(viewmodel=self.vm)

    def on_stop(self) -> None:
        """Desktop window close — flush state synchronously."""
        if self.vm is not None:
            self.vm.save_state(self.user_data_dir)

    def on_pause(self) -> None:
        """Android background — flush state synchronously."""
        if self.vm is not None:
            self.vm.save_state(self.user_data_dir)
        return True


if __name__ == "__main__":
    DrinkLaApp().run()
