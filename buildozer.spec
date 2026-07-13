[app]

# ── 基本信息 ──
title = 喝水啦
package.name = heshuila
package.domain = org.heshuila
source.dir = .
source.include_exts = py,kv,glsl,glb,obj,otf,ttf,wav,mp3,ogg,png,jpg,atlas,json,txt

# ── 依赖 ──
requirements = python3,kivy==2.3.0,numpy,pygltflib

# ── 入口 ──
# 项目根目录 main.py → src/view/main.py → DrinkLaApp
# 注意：字体已内嵌至 src/view/resources/fonts/，无需额外 include_patterns
source.include_patterns = main.py,src/**

# ── 版本 ──
version = 0.1.0
version.code = 1

# ── 方向 / 全屏 ──
orientation = portrait
fullscreen = 1

# ── Android 权限 ──
android.permissions = INTERNET,VIBRATE

# ── Android SDK License ──
android.accept_sdk_license = True

# ── Android 架构 (现代手机都是 arm64-v8a) ──
android.archs = arm64-v8a
android.api = 33
android.minapi = 26
android.ndk = 25b

# ── 签名 (debug 测试用) ──
android.allow_backup = True
android.debug_artifact = True

# ── 日志 ──
android.logcat_filters = *:S python:D

# ── Kivy 特定 ──
osx.python_version = 3
osx.kivy_version = 2.3.0

# ── 崩溃日志 ──
android.add_src =

# ── 清理 ──
android.clean_on_build = False

[buildozer]
log_level = 2
warn_on_root = 1
