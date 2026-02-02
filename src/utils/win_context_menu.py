import os
from pathlib import Path

try:
    import winreg
except ImportError:  # Non-Windows
    winreg = None


APP_KEY = r"Software\Classes\Directory\shell\HEICtoJPG"


def is_supported() -> bool:
    return os.name == "nt" and winreg is not None


def is_enabled() -> bool:
    if not is_supported():
        return False
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, APP_KEY) as _:
            return True
    except OSError:
        return False


def enable(exe_path: Path) -> None:
    if not is_supported():
        return
    exe_path = Path(exe_path).resolve()
    command = f'"{exe_path}" "%1"'
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, APP_KEY) as key:
        winreg.SetValueEx(key, "", 0, winreg.REG_SZ, "Convert HEICs to JPG")
        winreg.SetValueEx(key, "Icon", 0, winreg.REG_SZ, str(exe_path))
        with winreg.CreateKey(key, "command") as cmd_key:
            winreg.SetValueEx(cmd_key, "", 0, winreg.REG_SZ, command)


def disable() -> None:
    if not is_supported():
        return
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, APP_KEY + r"\command"):
            pass
        winreg.DeleteKey(winreg.HKEY_CURRENT_USER, APP_KEY + r"\command")
        winreg.DeleteKey(winreg.HKEY_CURRENT_USER, APP_KEY)
    except OSError:
        pass
