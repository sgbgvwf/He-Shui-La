"""喝 水 啦 —— 双击此文件启动 (或右键 → Open with → Python)"""

import os

# 确保工作目录在项目根
os.chdir(os.path.dirname(os.path.abspath(__file__)))

# 启动 Kivy 应用
from src.view.main import DrinkLaApp
DrinkLaApp().run()
