[app]
title = Gulyaturmix
package.name = gulyaturmix
package.domain = org.gulyaturmix

source.dir = .
source.include_exts = py,json
source.main = kivy_app.py

version = 1.0

requirements = python3,kivy,sqlite3

orientation = portrait
fullscreen = 0

android.permissions =
android.api = 33
android.minapi = 21
android.archs = arm64-v8a, armeabi-v7a

[buildozer]
log_level = 2