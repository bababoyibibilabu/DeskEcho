import ctypes
import ctypes.wintypes as wt
import sys
import os

advapi32 = ctypes.WinDLL("advapi32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
user32 = ctypes.WinDLL("user32", use_last_error=True)

PROCESS_ALL_ACCESS = 0x1F0FFF
TOKEN_ALL_ACCESS = 0xF01FF
SecurityImpersonation = 2
TokenPrimary = 1

class STARTUPINFO(ctypes.Structure):
    _fields_ = [
        ("cb", wt.DWORD),
        ("lpReserved", wt.LPWSTR),
        ("lpDesktop", wt.LPWSTR),
        ("lpTitle", wt.LPWSTR),
        ("dwX", wt.DWORD),
        ("dwY", wt.DWORD),
        ("dwXSize", wt.DWORD),
        ("dwYSize", wt.DWORD),
        ("dwXCountChars", wt.DWORD),
        ("dwYCountChars", wt.DWORD),
        ("dwFillAttribute", wt.DWORD),
        ("dwFlags", wt.DWORD),
        ("wShowWindow", wt.WORD),
        ("cbReserved2", wt.WORD),
        ("lpReserved2", ctypes.c_char_p),
        ("hStdInput", wt.HANDLE),
        ("hStdOutput", wt.HANDLE),
        ("hStdError", wt.HANDLE),
    ]

class PROCESS_INFORMATION(ctypes.Structure):
    _fields_ = [
        ("hProcess", wt.HANDLE),
        ("hThread", wt.HANDLE),
        ("dwProcessId", wt.DWORD),
        ("dwThreadId", wt.DWORD),
    ]

def get_explorer_pid():
    import subprocess
    cmd = 'powershell -Command "(Get-Process explorer -ErrorAction SilentlyContinue | Select-Object -First 1).Id"'
    out = subprocess.run(cmd, shell=True, capture_output=True, text=True).stdout.strip()
    return int(out) if out.isdigit() else None

def launch_interactive(cmd_line, cwd="C:\\DeskEcho"):
    pid = get_explorer_pid()
    if not pid:
        print("[-] explorer.exe PID not found")
        return False
    print(f"[*] Found explorer.exe PID: {pid}")

    h_process = kernel32.OpenProcess(PROCESS_ALL_ACCESS, False, pid)
    if not h_process:
        print(f"[-] OpenProcess failed: {ctypes.get_last_error()}")
        return False

    h_token = wt.HANDLE()
    if not advapi32.OpenProcessToken(h_process, TOKEN_ALL_ACCESS, ctypes.byref(h_token)):
        print(f"[-] OpenProcessToken failed: {ctypes.get_last_error()}")
        kernel32.CloseHandle(h_process)
        return False

    h_new_token = wt.HANDLE()
    if not advapi32.DuplicateTokenEx(
        h_token,
        TOKEN_ALL_ACCESS,
        None,
        SecurityImpersonation,
        TokenPrimary,
        ctypes.byref(h_new_token)
    ):
        print(f"[-] DuplicateTokenEx failed: {ctypes.get_last_error()}")
        kernel32.CloseHandle(h_token)
        kernel32.CloseHandle(h_process)
        return False

    si = STARTUPINFO()
    si.cb = ctypes.sizeof(STARTUPINFO)
    si.lpDesktop = "winsta0\\default"
    
    pi = PROCESS_INFORMATION()

    res = advapi32.CreateProcessAsUserW(
        h_new_token,
        None,
        cmd_line,
        None,
        None,
        False,
        0x00000010, # CREATE_NEW_CONSOLE
        None,
        cwd,
        ctypes.byref(si),
        ctypes.byref(pi)
    )

    if not res:
        err = ctypes.get_last_error()
        print(f"[-] CreateProcessAsUserW failed: {err}")
        return False

    print(f"[+] Successfully launched interactive process! PID: {pi.dwProcessId}")
    kernel32.CloseHandle(pi.hProcess)
    kernel32.CloseHandle(pi.hThread)
    kernel32.CloseHandle(h_new_token)
    kernel32.CloseHandle(h_token)
    kernel32.CloseHandle(h_process)
    return True

if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else r"C:\DeskEcho\DeskEcho.exe"
    launch_interactive(target)
