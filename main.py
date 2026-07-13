"""喝 水 啦 —— Buildozer 打包入口

此文件位于项目根目录，供 ``buildozer android debug`` 自动发现。
实际 App 逻辑在 ``src/view/main.py``。
"""

from src.view.main import DrinkLaApp

if __name__ == "__main__":
    DrinkLaApp().run()
