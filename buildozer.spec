[app]
title = Gulyaturmix
package.name = gulyaturmix
package.domain = org.gulyaturmix

source.dir = .
source.include_exts = py,json
source.main = kivy_app

version = 1.0

requirements = python3,kivy,sqlite3,requests,python-dotenv

orientation = portrait
fullscreen = 0

android.permissions =
android.api = 33
android.minapi = 21
android.ndk = 25b
android.build_tools_version = 34.0.0
android.archs = arm64-v8a

[buildozer]
log_level = 2