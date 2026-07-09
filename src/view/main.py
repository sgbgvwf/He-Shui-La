"""喝 水 啦 —— 儿童喝水养成游戏  Kivy App 入口"""

import os
from kivy.app import App
from kivy.core.text import LabelBase
from kivy.lang import Builder
from kivy.uix.boxlayout import BoxLayout

from src.viewmodel.main_viewmodel import MainViewModel

KV_PATH = "src/view/main_screen.kv"

# ── 注册中文字体 ──
_FONT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_FONT_HEI = os.path.join(_FONT_DIR, "SiYuanHeiTi-Regular", "SourceHanSansSC-Regular-2.otf")
_FONT_SONG = os.path.join(_FONT_DIR, "思源宋体 (行高修正版)_2.003", "思源宋体.otf")

LabelBase.register(name="ChineseHei", fn_regular=_FONT_HEI)
LabelBase.register(name="ChineseSong", fn_regular=_FONT_SONG)


class MainScreen(BoxLayout):
    """Root widget; ViewModel injected by App."""

    def __init__(self, viewmodel: MainViewModel, **kwargs):
        self.vm = viewmodel  # must be set before super() — kv rules access root.vm
        super().__init__(**kwargs)


class DrinkLaApp(App):
    """Kivy application entry point."""

    def build(self):
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
