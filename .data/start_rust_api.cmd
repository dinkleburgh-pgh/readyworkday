@echo off
call "C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\Common7\Tools\VsDevCmd.bat" -arch=amd64
set TRUCKAPP_DATA_DIR=..
set RUST_API_PORT=8787
cd /d C:\Users\dinkleburgh\TruckApp\rust_api
C:\Users\dinkleburgh\.cargo\bin\cargo.exe run --release
