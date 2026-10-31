@echo off
rem Opens the Plane Projection window. Double-click this file in Windows Explorer.
rem Uses the project's virtual environment (.venv) when it exists.
cd /d "%~dp0"
if exist ".venv\Scripts\pythonw.exe" (
    start "" ".venv\Scripts\pythonw.exe" gui.py
) else (
    start "" pythonw gui.py
)
