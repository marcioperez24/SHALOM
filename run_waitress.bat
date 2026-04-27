@echo off
cd /d "C:\Users\MARCIO-SERVER\Desktop\Shalom"
"C:\Users\MARCIO-SERVER\Desktop\Shalom\venv_shalom\Scripts\python.exe" -m waitress --listen=0.0.0.0:8080 colegio_web.wsgi.application