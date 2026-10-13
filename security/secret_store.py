from __future__ import annotations

import base64
import ctypes
import os
from ctypes import wintypes


PREFIX = "dpapi:"


class _DataBlob(ctypes.Structure):
    _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_ubyte))]


def is_protected(value):
    return isinstance(value, str) and value.startswith(PREFIX)


def _ensure_windows():
    if os.name != "nt":
        raise RuntimeError("API Key 加密保存需要 Windows DPAPI")


def _input_blob(data):
    buffer = ctypes.create_string_buffer(data)
    blob = _DataBlob(len(data), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_ubyte)))
    return blob, buffer


def _free(blob):
    if blob.pbData:
        ctypes.windll.kernel32.LocalFree(ctypes.cast(blob.pbData, wintypes.HLOCAL))


def protect_secret(value):
    if not value:
        return ""
    if is_protected(value):
        return value
    _ensure_windows()
    source, source_buffer = _input_blob(value.encode("utf-8"))
    result = _DataBlob()
    if not ctypes.windll.crypt32.CryptProtectData(
        ctypes.byref(source), None, None, None, None, 0, ctypes.byref(result)
    ):
        raise ctypes.WinError()
    try:
        encrypted = ctypes.string_at(result.pbData, result.cbData)
    finally:
        _free(result)
    return PREFIX + base64.b64encode(encrypted).decode("ascii")


def unprotect_secret(value):
    if not value or not is_protected(value):
        return value or ""
    _ensure_windows()
    try:
        encrypted = base64.b64decode(value[len(PREFIX):], validate=True)
    except Exception as exc:
        raise RuntimeError("API Key 加密内容损坏") from exc
    source, source_buffer = _input_blob(encrypted)
    result = _DataBlob()
    if not ctypes.windll.crypt32.CryptUnprotectData(
        ctypes.byref(source), None, None, None, None, 0, ctypes.byref(result)
    ):
        raise ctypes.WinError()
    try:
        return ctypes.string_at(result.pbData, result.cbData).decode("utf-8")
    finally:
        _free(result)
