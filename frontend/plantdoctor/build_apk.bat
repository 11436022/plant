@echo off
set "JAVA_HOME=C:\Program Files\Android\Android Studio\jbr"
set "PATH=%JAVA_HOME%\bin;%PATH%"
cd /d "D:\plant_backend\frontend\plantdoctor"
call "D:\plant_backend\frontend\plantdoctor\gradlew.bat" assembleDebug

