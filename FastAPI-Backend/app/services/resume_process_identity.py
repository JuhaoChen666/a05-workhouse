"""Read identity of registered worker processes; never terminate any process."""
import os
from pathlib import Path


def process_identity(pid):
    if type(pid) is not int or pid <= 0:
        raise ValueError("invalid worker PID")
    if os.name == "nt":
        import ctypes
        from ctypes import wintypes
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        kernel.OpenProcess.restype = wintypes.HANDLE
        kernel.GetProcessTimes.argtypes = [wintypes.HANDLE] + [ctypes.POINTER(wintypes.FILETIME)] * 4
        kernel.GetProcessTimes.restype = wintypes.BOOL
        kernel.GetExitCodeProcess.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
        kernel.GetExitCodeProcess.restype = wintypes.BOOL
        kernel.CloseHandle.argtypes = [wintypes.HANDLE]
        handle = kernel.OpenProcess(0x1000, False, pid)  # query-only limited information
        if not handle:
            if ctypes.get_last_error() == 87:
                return None
            raise RuntimeError("worker process identity unconfirmed")
        try:
            exit_code = wintypes.DWORD()
            if not kernel.GetExitCodeProcess(handle, ctypes.byref(exit_code)):
                raise RuntimeError("worker process identity unconfirmed")
            if exit_code.value != 259:  # STILL_ACTIVE
                return None
            times = [wintypes.FILETIME() for _ in range(4)]
            if not kernel.GetProcessTimes(handle, *(ctypes.byref(value) for value in times)):
                raise RuntimeError("worker process identity unconfirmed")
            return str((times[0].dwHighDateTime << 32) | times[0].dwLowDateTime)
        finally:
            kernel.CloseHandle(handle)
    try:
        stat = Path(f"/proc/{pid}/stat").read_text(encoding="ascii")
        if stat.rsplit(") ", 1)[1].split()[0] in {"Z", "X"}:
            return None
        start = stat.rsplit(") ", 1)[1].split()[19]
        boot = Path("/proc/sys/kernel/random/boot_id").read_text(encoding="ascii").strip()
        return f"{boot}:{start}"
    except FileNotFoundError:
        return None
    except (OSError, IndexError):
        raise RuntimeError("worker process identity unconfirmed") from None
