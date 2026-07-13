"""喝 水 啦 —— 儿童喝水养成游戏  Kivy App 入口"""

import os
import sys

from kivy.config import Config

# ── 移动端 / 桌面端 自适应配置 ──
IS_MOBILE = hasattr(sys, "getandroidapilevel") or sys.platform in ("ios", "android")

if not IS_MOBILE:
    Config.set("input", "mouse", "mouse,disable_multitouch")

Config.set("graphics", "resizable", True)
if IS_MOBILE:
    Config.set("graphics", "fullscreen", "auto")

from kivy.app import App
from kivy.core.text import LabelBase
from kivy.core.window import Window
from kivy.lang import Builder
from kivy.properties import ObjectProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.popup import Popup

from src.viewmodel.main_viewmodel import MainViewModel
from src.view.sound_manager import SoundManager

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
KV_PATH = os.path.join(_BASE_DIR, "main_screen.kv")
SETTINGS_KV_PATH = os.path.join(_BASE_DIR, "settings_dialog.kv")
ACHIEVEMENT_KV_PATH = os.path.join(_BASE_DIR, "achievement_screen.kv")
_MODELS_DIR = os.path.join(_BASE_DIR, "resources", "models")

_SOUNDS_DIR = os.path.join(_BASE_DIR, "resources", "sounds")

# ── 注册中文字体 ──
_FONT_DIR = os.path.join(_BASE_DIR, "resources", "fonts")
_FONT_HEI = os.path.join(_FONT_DIR, "SourceHanSansSC-Regular-2.otf")
_FONT_SONG = os.path.join(_FONT_DIR, "SourceHanSerifSC-Regular.otf")

LabelBase.register(name="ChineseHei", fn_regular=_FONT_HEI)
LabelBase.register(name="ChineseSong", fn_regular=_FONT_SONG)

if IS_MOBILE:
    Window.softinput_mode = "below_target"


class VerifyPopup(Popup):
    settings_vm = ObjectProperty(None)

    def on_verify(self) -> None:
        if self.settings_vm.check_verification():
            self.dismiss()
            settings = SettingsPopup(settings_vm=self.settings_vm)
            settings.open()


class SettingsPopup(Popup):
    settings_vm = ObjectProperty(None)

    def on_save(self) -> None:
        self.settings_vm.save()
        self.dismiss()
        app = App.get_running_app()
        if app and hasattr(app.root, 'on_settings_saved'):
            app.root.on_settings_saved()

    def on_reset(self) -> None:
        self.settings_vm.reset_data()
        self.settings_vm.save()
        self.dismiss()
        app = App.get_running_app()
        if app and hasattr(app.root, 'on_data_reset'):
            app.root.on_data_reset()


class AchievementPopup(Popup):
    ach_vm = ObjectProperty(None)

    def on_open(self) -> None:
        from kivy.uix.button import Button
        grid = self.ids.sticker_grid
        grid.clear_widgets()
        for card in self.ach_vm.cards:
            if card["unlocked"]:
                bg = (0.35, 0.7, 0.35, 1)
                text = f"{card['name']}\n{card['description']}"
            else:
                bg = (0.6, 0.6, 0.6, 1)
                text = "?\n---"
            btn = Button(
                font_name="ChineseHei", text=text, font_size="14sp",
                halign="center", valign="middle", background_normal="",
                background_color=bg, color=(1,1,1,1),
                size_hint_y=None, height="90sp",
            )
            btn.bind(size=btn.setter('text_size'))
            grid.add_widget(btn)


class MainScreen(BoxLayout):

    def __init__(self, viewmodel: MainViewModel, **kwargs):
        self.vm = viewmodel
        super().__init__(**kwargs)

    def open_settings(self) -> None:
        from src.viewmodel.settings_viewmodel import SettingsViewModel
        svm = SettingsViewModel(self.vm.config, self.vm.data_dir)
        verify = VerifyPopup(settings_vm=svm)
        verify.open()

    def open_achievements(self) -> None:
        from src.viewmodel.achievement_viewmodel import AchievementViewModel
        avm = AchievementViewModel(self.vm.achievement_manager)
        popup = AchievementPopup(ach_vm=avm)
        popup.open()

    def on_settings_saved(self) -> None:
        self.vm.save_state()
        self.vm.reload_config()

    def on_data_reset(self) -> None:
        self.vm.reload_config()
        if hasattr(self, 'ids') and 'companion_3d' in self.ids:
            w = self.ids.companion_3d
            w._current_idx = 0
            w._last_vm_level = 1
            w._vm_level_init = False
            w._mscale = 1.0
            for i in range(len(w._companions)):
                models = w._companion_data[i].get("models", {})
                name = w._companion_data[i].get("name", f"伙伴{i+1}")
                w._companion_data[i] = {"level": 1, "stage": "形态A", "scale": 1.0, "models": models, "name": name}
            w.current_level = 1
            w._sync_current_name()
            w._load_model(w._companions[0])


class DrinkLaApp(App):

    def build(self):
        Builder.load_file(SETTINGS_KV_PATH)
        Builder.load_file(ACHIEVEMENT_KV_PATH)
        Builder.load_file(KV_PATH)

        self.vm = MainViewModel()
        self.vm.load_state(self.user_data_dir)

        # 音效
        self.vm.set_sound_manager(
            SoundManager(_SOUNDS_DIR, enabled=self.vm.config.sound_enabled)
        )

        root = MainScreen(viewmodel=self.vm)

        # 配置多伙伴模型列表 (文件名, 自定义名称)
        root.ids.companion_3d.setup_companions([
            os.path.join(_MODELS_DIR, "companion.glb"),
            os.path.join(_MODELS_DIR, "Tree_1.glb"),
            os.path.join(_MODELS_DIR, "diamond.glb"),
        ], names=["方块", "小树", "钻石"])
        # 树的进化模型: 等级1→Tree_1, 等级2→Tree_2
        root.ids.companion_3d.set_companion_models(1, {
            "1": os.path.join(_MODELS_DIR, "Tree_1.glb"),
            "2": os.path.join(_MODELS_DIR, "Tree_2.glb"),
        })

        return root

    def on_stop(self) -> None:
        try:
            if self.vm is not None:
                self.vm.save_state()
        except OSError:
            pass

    def on_pause(self) -> None:
        try:
            if self.vm is not None:
                self.vm.save_state()
        except OSError:
            pass
        return True


if __name__ == "__main__":
    DrinkLaApp().run()
