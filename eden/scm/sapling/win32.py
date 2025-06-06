# Portions Copyright (c) Meta Platforms, Inc. and affiliates.
#
# This software may be used and distributed according to the terms of the
# GNU General Public License version 2.

# win32.py - utility functions that use win32 API
#
# Copyright 2005-2009 Olivia Mackall <olivia@selenic.com> and others
#
# This software may be used and distributed according to the terms of the
# GNU General Public License version 2 or any later version.


import ctypes
import ctypes.wintypes as wintypes
import errno
import msvcrt
import os
import random

from . import encoding

# pyre-fixme[16]: Module `ctypes` has no attribute `WinDLL`.
_kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
# pyre-fixme[16]: Module `ctypes` has no attribute `WinDLL`.
_advapi32 = ctypes.WinDLL("advapi32", use_last_error=True)
# pyre-fixme[16]: Module `ctypes` has no attribute `WinDLL`.
_user32 = ctypes.WinDLL("user32", use_last_error=True)
# pyre-fixme[16]: Module `ctypes` has no attribute `WinDLL`.
_crypt32 = ctypes.WinDLL("crypt32", use_last_error=True)

_BOOL = ctypes.c_long
_WORD = ctypes.c_ushort
_DWORD = ctypes.c_ulong
_UINT = ctypes.c_uint
_LONG = ctypes.c_long
_LPCSTR = _LPSTR = ctypes.c_char_p
_LPCWSTR = ctypes.c_wchar_p
_HANDLE = ctypes.c_void_p
_HWND = _HANDLE
_PCCERT_CONTEXT = ctypes.c_void_p
_PCCERT_CHAIN_CONTEXT = ctypes.c_void_p
_MAX_PATH = wintypes.MAX_PATH

_INVALID_HANDLE_VALUE = _HANDLE(-1).value

# GetLastError
_ERROR_SUCCESS = 0
_ERROR_NO_MORE_FILES = 18
_ERROR_INVALID_PARAMETER = 87
_ERROR_BROKEN_PIPE = 109
_ERROR_INSUFFICIENT_BUFFER = 122

# WPARAM is defined as UINT_PTR (unsigned type)
# LPARAM is defined as LONG_PTR (signed type)
if ctypes.sizeof(ctypes.c_long) == ctypes.sizeof(ctypes.c_void_p):
    _WPARAM = ctypes.c_ulong
    _LPARAM = ctypes.c_long
elif ctypes.sizeof(ctypes.c_longlong) == ctypes.sizeof(ctypes.c_void_p):
    _WPARAM = ctypes.c_ulonglong
    _LPARAM = ctypes.c_longlong


class _FILETIME(ctypes.Structure):
    _fields_ = [("dwLowDateTime", _DWORD), ("dwHighDateTime", _DWORD)]


_LPFILETIME = ctypes.POINTER(_FILETIME)


class _BY_HANDLE_FILE_INFORMATION(ctypes.Structure):
    _fields_ = [
        ("dwFileAttributes", _DWORD),
        ("ftCreationTime", _FILETIME),
        ("ftLastAccessTime", _FILETIME),
        ("ftLastWriteTime", _FILETIME),
        ("dwVolumeSerialNumber", _DWORD),
        ("nFileSizeHigh", _DWORD),
        ("nFileSizeLow", _DWORD),
        ("nNumberOfLinks", _DWORD),
        ("nFileIndexHigh", _DWORD),
        ("nFileIndexLow", _DWORD),
    ]


# CreateFile
_FILE_SHARE_READ = 0x00000001
_FILE_SHARE_WRITE = 0x00000002
_FILE_SHARE_DELETE = 0x00000004

_OPEN_EXISTING = 3

_FILE_FLAG_BACKUP_SEMANTICS = 0x02000000

# SetFileAttributes
_FILE_ATTRIBUTE_NORMAL = 0x80
_FILE_ATTRIBUTE_NOT_CONTENT_INDEXED = 0x2000

# Process Security and Access Rights
_PROCESS_QUERY_INFORMATION = 0x0400
_PROCESS_QUERY_LIMITED_INFORMATION = 0x1000

# GetExitCodeProcess
_STILL_ACTIVE = 259


class _STARTUPINFO(ctypes.Structure):
    _fields_ = [
        ("cb", _DWORD),
        ("lpReserved", _LPSTR),
        ("lpDesktop", _LPSTR),
        ("lpTitle", _LPSTR),
        ("dwX", _DWORD),
        ("dwY", _DWORD),
        ("dwXSize", _DWORD),
        ("dwYSize", _DWORD),
        ("dwXCountChars", _DWORD),
        ("dwYCountChars", _DWORD),
        ("dwFillAttribute", _DWORD),
        ("dwFlags", _DWORD),
        ("wShowWindow", _WORD),
        ("cbReserved2", _WORD),
        ("lpReserved2", ctypes.c_char_p),
        ("hStdInput", _HANDLE),
        ("hStdOutput", _HANDLE),
        ("hStdError", _HANDLE),
    ]


class _PROCESS_INFORMATION(ctypes.Structure):
    _fields_ = [
        ("hProcess", _HANDLE),
        ("hThread", _HANDLE),
        ("dwProcessId", _DWORD),
        ("dwThreadId", _DWORD),
    ]


_CREATE_NO_WINDOW = 0x08000000
_SW_HIDE = 0


class _COORD(ctypes.Structure):
    _fields_ = [("X", ctypes.c_short), ("Y", ctypes.c_short)]


class _SMALL_RECT(ctypes.Structure):
    _fields_ = [
        ("Left", ctypes.c_short),
        ("Top", ctypes.c_short),
        ("Right", ctypes.c_short),
        ("Bottom", ctypes.c_short),
    ]


class _CONSOLE_SCREEN_BUFFER_INFO(ctypes.Structure):
    _fields_ = [
        ("dwSize", _COORD),
        ("dwCursorPosition", _COORD),
        ("wAttributes", _WORD),
        ("srWindow", _SMALL_RECT),
        ("dwMaximumWindowSize", _COORD),
    ]


_STD_OUTPUT_HANDLE = _DWORD(-11).value
_STD_ERROR_HANDLE = _DWORD(-12).value

# CERT_TRUST_STATUS dwErrorStatus
CERT_TRUST_IS_PARTIAL_CHAIN = 0x10000

# CertCreateCertificateContext encodings
X509_ASN_ENCODING = 0x00000001
PKCS_7_ASN_ENCODING = 0x00010000


# These structs are only complete enough to achieve what we need.
class CERT_CHAIN_CONTEXT(ctypes.Structure):
    _fields_ = (
        ("cbSize", _DWORD),
        # CERT_TRUST_STATUS struct
        ("dwErrorStatus", _DWORD),
        ("dwInfoStatus", _DWORD),
        ("cChain", _DWORD),
        ("rgpChain", ctypes.c_void_p),
        ("cLowerQualityChainContext", _DWORD),
        ("rgpLowerQualityChainContext", ctypes.c_void_p),
        ("fHasRevocationFreshnessTime", _BOOL),
        ("dwRevocationFreshnessTime", _DWORD),
    )


class CERT_USAGE_MATCH(ctypes.Structure):
    _fields_ = (
        ("dwType", _DWORD),
        # CERT_ENHKEY_USAGE struct
        ("cUsageIdentifier", _DWORD),
        ("rgpszUsageIdentifier", ctypes.c_void_p),  # LPSTR *
    )


class CERT_CHAIN_PARA(ctypes.Structure):
    _fields_ = (
        ("cbSize", _DWORD),
        ("RequestedUsage", CERT_USAGE_MATCH),
        ("RequestedIssuancePolicy", CERT_USAGE_MATCH),
        ("dwUrlRetrievalTimeout", _DWORD),
        ("fCheckRevocationFreshnessTime", _BOOL),
        ("dwRevocationFreshnessTime", _DWORD),
        ("pftCacheResync", ctypes.c_void_p),  # LPFILETIME
        ("pStrongSignPara", ctypes.c_void_p),  # PCCERT_STRONG_SIGN_PARA
        ("dwStrongSignFlags", _DWORD),
    )


# types of parameters of C functions used

_crypt32.CertCreateCertificateContext.argtypes = [
    _DWORD,  # cert encoding
    ctypes.c_char_p,  # cert
    _DWORD,
]  # cert size
_crypt32.CertCreateCertificateContext.restype = _PCCERT_CONTEXT

_crypt32.CertGetCertificateChain.argtypes = [
    ctypes.c_void_p,  # HCERTCHAINENGINE
    _PCCERT_CONTEXT,
    ctypes.c_void_p,  # LPFILETIME
    ctypes.c_void_p,  # HCERTSTORE
    ctypes.c_void_p,  # PCERT_CHAIN_PARA
    _DWORD,
    ctypes.c_void_p,  # LPVOID
    ctypes.c_void_p,  # PCCERT_CHAIN_CONTEXT *
]
_crypt32.CertGetCertificateChain.restype = _BOOL

_crypt32.CertFreeCertificateChain.argtypes = [_PCCERT_CHAIN_CONTEXT]
_crypt32.CertFreeCertificateChain.restype = None

_crypt32.CertFreeCertificateContext.argtypes = [_PCCERT_CONTEXT]
_crypt32.CertFreeCertificateContext.restype = _BOOL

_kernel32.CreateFileW.argtypes = [
    _LPCWSTR,
    _DWORD,
    _DWORD,
    ctypes.c_void_p,
    _DWORD,
    _DWORD,
    _HANDLE,
]
_kernel32.CreateFileW.restype = _HANDLE

_kernel32.GetFileInformationByHandle.argtypes = [_HANDLE, ctypes.c_void_p]
_kernel32.GetFileInformationByHandle.restype = _BOOL

_kernel32.CloseHandle.argtypes = [_HANDLE]
_kernel32.CloseHandle.restype = _BOOL

try:
    _kernel32.CreateHardLinkW.argtypes = [_LPCWSTR, _LPCWSTR, ctypes.c_void_p]
    _kernel32.CreateHardLinkW.restype = _BOOL
except AttributeError:
    pass

_kernel32.SetFileAttributesW.argtypes = [_LPCWSTR, _DWORD]
_kernel32.SetFileAttributesW.restype = _BOOL

_DRIVE_UNKNOWN = 0
_DRIVE_NO_ROOT_DIR = 1
_DRIVE_REMOVABLE = 2
_DRIVE_FIXED = 3
_DRIVE_REMOTE = 4
_DRIVE_CDROM = 5
_DRIVE_RAMDISK = 6

_kernel32.GetDriveTypeA.argtypes = [_LPCSTR]
_kernel32.GetDriveTypeA.restype = _UINT

_kernel32.GetVolumeInformationA.argtypes = [
    _LPCSTR,
    ctypes.c_void_p,
    _DWORD,
    ctypes.c_void_p,
    ctypes.c_void_p,
    ctypes.c_void_p,
    ctypes.c_void_p,
    _DWORD,
]
_kernel32.GetVolumeInformationA.restype = _BOOL

_kernel32.GetVolumePathNameA.argtypes = [_LPCSTR, ctypes.c_void_p, _DWORD]
_kernel32.GetVolumePathNameA.restype = _BOOL


_kernel32.OpenProcess.argtypes = [_DWORD, _BOOL, _DWORD]
_kernel32.OpenProcess.restype = _HANDLE

_kernel32.GetExitCodeProcess.argtypes = [_HANDLE, ctypes.c_void_p]
_kernel32.GetExitCodeProcess.restype = _BOOL

_kernel32.GetLastError.argtypes = []
_kernel32.GetLastError.restype = _DWORD

_kernel32.GetModuleFileNameA.argtypes = [_HANDLE, ctypes.c_void_p, _DWORD]
_kernel32.GetModuleFileNameA.restype = _DWORD

_kernel32.CreateProcessA.argtypes = [
    _LPCSTR,
    _LPCSTR,
    ctypes.c_void_p,
    ctypes.c_void_p,
    _BOOL,
    _DWORD,
    ctypes.c_void_p,
    _LPCSTR,
    ctypes.c_void_p,
    ctypes.c_void_p,
]
_kernel32.CreateProcessA.restype = _BOOL

_kernel32.ExitProcess.argtypes = [_UINT]
_kernel32.ExitProcess.restype = None

_kernel32.GetCurrentProcessId.argtypes = []
_kernel32.GetCurrentProcessId.restype = _DWORD

# pyre-fixme[16]: Module `ctypes` has no attribute `WINFUNCTYPE`.
_SIGNAL_HANDLER = ctypes.WINFUNCTYPE(_BOOL, _DWORD)
_kernel32.SetConsoleCtrlHandler.argtypes = [_SIGNAL_HANDLER, _BOOL]
_kernel32.SetConsoleCtrlHandler.restype = _BOOL

_kernel32.SetConsoleMode.argtypes = [_HANDLE, _DWORD]
_kernel32.SetConsoleMode.restype = _BOOL

_kernel32.GetConsoleMode.argtypes = [_HANDLE, ctypes.c_void_p]
_kernel32.GetConsoleMode.restype = _BOOL

_kernel32.GetProcessTimes.argtypes = [
    _HANDLE,
    _LPFILETIME,
    _LPFILETIME,
    _LPFILETIME,
    _LPFILETIME,
]
_kernel32.GetProcessTimes.restype = _BOOL

_kernel32.GetStdHandle.argtypes = [_DWORD]
_kernel32.GetStdHandle.restype = _HANDLE

_kernel32.GetConsoleScreenBufferInfo.argtypes = [_HANDLE, ctypes.c_void_p]
_kernel32.GetConsoleScreenBufferInfo.restype = _BOOL

_advapi32.GetUserNameA.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
_advapi32.GetUserNameA.restype = _BOOL

_user32.GetWindowThreadProcessId.argtypes = [_HANDLE, ctypes.c_void_p]
_user32.GetWindowThreadProcessId.restype = _DWORD

_user32.ShowWindow.argtypes = [_HANDLE, ctypes.c_int]
_user32.ShowWindow.restype = _BOOL

# pyre-fixme[16]: Module `ctypes` has no attribute `WINFUNCTYPE`.
_WNDENUMPROC = ctypes.WINFUNCTYPE(_BOOL, _HWND, _LPARAM)
_user32.EnumWindows.argtypes = [_WNDENUMPROC, _LPARAM]
_user32.EnumWindows.restype = _BOOL

_kernel32.PeekNamedPipe.argtypes = [
    _HANDLE,
    ctypes.c_void_p,
    _DWORD,
    ctypes.c_void_p,
    ctypes.c_void_p,
    ctypes.c_void_p,
]
_kernel32.PeekNamedPipe.restype = _BOOL

_kernel32.GetOEMCP.argtypes = []
_kernel32.GetOEMCP.restype = _UINT


def _raiseoserror(name):
    # Force the code to a signed int to avoid an 'int too large' error.
    # See https://bugs.python.org/issue28474
    code = _kernel32.GetLastError()
    if code > 0x7FFFFFFF:
        code -= 2**32
    err = ctypes.WinError(code=code)
    raise OSError(err.errno, "%s: %s" % (name, err.strerror))


def getfileinfo(name):
    fh = _kernel32.CreateFileW(
        pathtowin32W(name),
        0,
        _FILE_SHARE_READ | _FILE_SHARE_WRITE | _FILE_SHARE_DELETE,
        None,
        _OPEN_EXISTING,
        _FILE_FLAG_BACKUP_SEMANTICS,
        None,
    )
    if fh == _INVALID_HANDLE_VALUE:
        _raiseoserror(name)
    try:
        fi = _BY_HANDLE_FILE_INFORMATION()
        if not _kernel32.GetFileInformationByHandle(fh, ctypes.byref(fi)):
            _raiseoserror(name)
        return fi
    finally:
        _kernel32.CloseHandle(fh)


def getcurrentprocstarttime():
    """Get current process start time

    See _getprocstarttime docstring for more info"""
    pid = _kernel32.GetCurrentProcessId()
    return getprocstarttime(pid)


def getprocstarttime(pid):
    """Get the windows timestamp of process start time

    Windows Timestamp in this context is a number of 100-nanosecond
    time units since January 1, 1601 at Greenwich, England.

    See https://msdn.microsoft.com/en-us/library/ms683223(VS.85).aspx"""
    ph = _kernel32.OpenProcess(_PROCESS_QUERY_LIMITED_INFORMATION, 1, pid)
    if not ph or ph == _INVALID_HANDLE_VALUE:
        raise ctypes.WinError(_kernel32.GetLastError())
    try:
        creationtime = _FILETIME()
        exittime = _FILETIME()
        kerneltime = _FILETIME()
        usertime = _FILETIME()
        success = _kernel32.GetProcessTimes(
            ph,
            ctypes.byref(creationtime),
            ctypes.byref(exittime),
            ctypes.byref(kerneltime),
            ctypes.byref(usertime),
        )
        if not success:
            raise ctypes.WinError(_kernel32.GetLastError())
        ct = (creationtime.dwHighDateTime << 32) + creationtime.dwLowDateTime
        return ct
    finally:
        _kernel32.CloseHandle(ph)


def checkcertificatechain(cert, build=True):
    """Tests the given certificate to see if there is a complete chain to a
    trusted root certificate.  As a side effect, missing certificates are
    downloaded and installed unless ``build=False``.  True is returned if a
    chain to a trusted root exists (even if built on the fly), otherwise
    False.  NB: A chain to a trusted root does NOT imply that the certificate
    is valid.
    """

    chainctxptr = ctypes.POINTER(CERT_CHAIN_CONTEXT)

    pchainctx = chainctxptr()
    chainpara = CERT_CHAIN_PARA(
        cbSize=ctypes.sizeof(CERT_CHAIN_PARA), RequestedUsage=CERT_USAGE_MATCH()
    )

    certctx = _crypt32.CertCreateCertificateContext(X509_ASN_ENCODING, cert, len(cert))
    if certctx is None:
        _raiseoserror("CertCreateCertificateContext")

    flags = 0

    if not build:
        flags |= 0x100  # CERT_CHAIN_DISABLE_AUTH_ROOT_AUTO_UPDATE

    try:
        # Building the certificate chain will update root certs as necessary.
        if not _crypt32.CertGetCertificateChain(
            None,  # hChainEngine
            certctx,  # pCertContext
            None,  # pTime
            None,  # hAdditionalStore
            ctypes.byref(chainpara),
            flags,
            None,  # pvReserved
            ctypes.byref(pchainctx),
        ):
            _raiseoserror("CertGetCertificateChain")

        chainctx = pchainctx.contents

        return chainctx.dwErrorStatus & CERT_TRUST_IS_PARTIAL_CHAIN == 0
    finally:
        if pchainctx:
            _crypt32.CertFreeCertificateChain(pchainctx)
        _crypt32.CertFreeCertificateContext(certctx)


def oslink(src, dst):
    try:
        if not _kernel32.CreateHardLinkW(pathtowin32W(dst), pathtowin32W(src), None):
            _raiseoserror(src)
    except AttributeError:  # Wine doesn't support this function
        _raiseoserror(src)


def nlinks(name):
    """return number of hardlinks for the given file"""
    return getfileinfo(name).nNumberOfLinks


def samefile(path1, path2):
    """Returns whether path1 and path2 refer to the same file or directory."""
    res1 = getfileinfo(path1)
    res2 = getfileinfo(path2)
    return (
        res1.dwVolumeSerialNumber == res2.dwVolumeSerialNumber
        and res1.nFileIndexHigh == res2.nFileIndexHigh
        and res1.nFileIndexLow == res2.nFileIndexLow
    )


def samedevice(path1, path2):
    """Returns whether path1 and path2 are on the same device."""
    res1 = getfileinfo(path1)
    res2 = getfileinfo(path2)
    return res1.dwVolumeSerialNumber == res2.dwVolumeSerialNumber


def peekpipe(pipe):
    handle = msvcrt.get_osfhandle(pipe.fileno())
    avail = _DWORD()

    if not _kernel32.PeekNamedPipe(handle, None, 0, None, ctypes.byref(avail), None):
        err = _kernel32.GetLastError()
        if err == _ERROR_BROKEN_PIPE:
            return 0
        raise ctypes.WinError(err)

    return avail.value


def testpid(pid):
    """return True if pid is still running or unable to
    determine, False otherwise"""
    h = _kernel32.OpenProcess(_PROCESS_QUERY_INFORMATION, False, pid)
    if h:
        try:
            status = _DWORD()
            if _kernel32.GetExitCodeProcess(h, ctypes.byref(status)):
                return status.value == _STILL_ACTIVE
        finally:
            _kernel32.CloseHandle(h)
    return _kernel32.GetLastError() != _ERROR_INVALID_PARAMETER


def executablepath():
    """return full path of hg.exe"""
    size = 600
    buf = ctypes.create_string_buffer(size + 1)
    len = _kernel32.GetModuleFileNameA(None, ctypes.byref(buf), size)
    if len == 0:
        raise ctypes.WinError()  # Note: WinError is a function
    elif len == size:
        raise ctypes.WinError(_ERROR_INSUFFICIENT_BUFFER)
    return buf.value


def getuser():
    """return name of current user"""
    size = _DWORD(300)
    buf = ctypes.create_string_buffer(size.value + 1)
    if not _advapi32.GetUserNameA(ctypes.byref(buf), ctypes.byref(size)):
        raise ctypes.WinError()
    return buf.value.decode()


_signalhandler = []


def setsignalhandler():
    """Register a termination handler for console events including
    CTRL+C. python signal handlers do not work well with socket
    operations.
    """

    def handler(event):
        _kernel32.ExitProcess(1)

    if _signalhandler:
        return  # already registered
    h = _SIGNAL_HANDLER(handler)
    _signalhandler.append(h)  # needed to prevent garbage collection
    if not _kernel32.SetConsoleCtrlHandler(h, True):
        raise ctypes.WinError()


def hidewindow():
    def callback(hwnd, pid):
        wpid = _DWORD()
        _user32.GetWindowThreadProcessId(hwnd, ctypes.byref(wpid))
        if pid == wpid.value:
            _user32.ShowWindow(hwnd, _SW_HIDE)
            return False  # stop enumerating windows
        return True

    pid = _kernel32.GetCurrentProcessId()
    _user32.EnumWindows(_WNDENUMPROC(callback), pid)


def termsize():
    # cmd.exe does not handle CR like a unix console, the CR is
    # counted in the line length. On 80 columns consoles, if 80
    # characters are written, the following CR won't apply on the
    # current line but on the new one. Keep room for it.
    width = 80 - 1
    height = 25
    # Query stderr to avoid problems with redirections
    screenbuf = _kernel32.GetStdHandle(
        _STD_ERROR_HANDLE
    )  # don't close the handle returned
    if screenbuf is None or screenbuf == _INVALID_HANDLE_VALUE:
        return width, height
    csbi = _CONSOLE_SCREEN_BUFFER_INFO()
    if not _kernel32.GetConsoleScreenBufferInfo(screenbuf, ctypes.byref(csbi)):
        return width, height
    width = csbi.srWindow.Right - csbi.srWindow.Left  # don't '+ 1'
    height = csbi.srWindow.Bottom - csbi.srWindow.Top + 1
    return width, height


def unlink(f):
    """try to implement POSIX' unlink semantics on Windows"""
    # POSIX allows to unlink and rename open files. Windows has serious
    # problems with doing that:
    # - Calling os.unlink (or os.rename) on a file f fails if f or any
    #   hardlinked copy of f has been opened with Python's open(). There is no
    #   way such a file can be deleted or renamed on Windows (other than
    #   scheduling the delete or rename for the next reboot).
    # - Calling os.unlink on a file that has been opened with Mercurial's
    #   posixfile (or comparable methods) will delay the actual deletion of
    #   the file for as long as the file is held open. The filename is blocked
    #   during that time and cannot be used for recreating a new file under
    #   that same name ("zombie file"). Directories containing such zombie files
    #   cannot be removed or moved.
    # A file that has been opened with posixfile can be renamed, so we rename
    # f to a random temporary name before calling os.unlink on it. This allows
    # callers to recreate f immediately while having other readers do their
    # implicit zombie filename blocking on a temporary name.

    for tries in range(10):
        temp = "%s-%08x" % (f, random.randint(0, 0xFFFFFFFF))
        try:
            os.rename(f, temp)  # raises OSError EEXIST if temp exists
            break
        except OSError as e:
            if e.errno != errno.EEXIST:
                raise
    else:
        raise IOError(errno.EEXIST, "No usable temporary filename found")

    try:
        os.unlink(temp)
    except OSError:
        # The unlink might have failed because the READONLY attribute may have
        # been set on the original file. Rename works fine with READONLY set,
        # but not os.unlink. Reset all attributes and try again.
        _kernel32.SetFileAttributesW(pathtowin32W(temp), _FILE_ATTRIBUTE_NORMAL)
        try:
            os.unlink(temp)
        except OSError:
            try:
                # Last effort, open it as a temporary file which will remove it
                # when it's unmapped.
                os.open(temp, os.O_TEMPORARY)
            except OSError:
                # The unlink might have failed due to some very rude AV-Scanners.
                # Leaking a tempfile is the lesser evil than aborting here and
                # leaving some potentially serious inconsistencies.
                pass


def makedir(path, notindexed):
    os.mkdir(path)
    if notindexed:
        _kernel32.SetFileAttributesW(
            pathtowin32W(path), _FILE_ATTRIBUTE_NOT_CONTENT_INDEXED
        )


def getmaxmemoryusage():
    """Returns the maximum memory used by the process in bytes, similar to
    maxrss in Unix.
    """
    # TODO(phillco): Implement via GetProcessMemoryInfo().
    raise NotImplementedError


def getoemcp():
    """Returns the OEM codepage, which is the codepage that should be used for
    output to the console."""
    return "cp%d" % _kernel32.GetOEMCP()


def pathtowin32W(path):
    return _LPCWSTR(path)
