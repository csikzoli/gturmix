[app]
title = Gulyaturmix
package.name = gulyaturmix
package.domain = org.gulyaturmix

source.dir = .
source.include_exts = py,json
source.main = kivy_app.py

version = 1.0

requirements = python3,kivy,sqlite3,requests,python-dotenv

orientation = portrait
fullscreen = 0

android.permissions =
android.api = 33
android.minapi = 21
android.sdk = 33
android.ndk = 25b

log_level = 2