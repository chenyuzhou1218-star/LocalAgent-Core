from __future__ import annotations

import json
import subprocess
import textwrap
import time
from threading import Event


def listen_once(timeout: int | None = None, stop_event: Event | None = None) -> dict:
    """Use the installed Windows Speech API without sending audio to a cloud service."""
    script = textwrap.dedent(
        """
        Add-Type -AssemblyName System.Speech
        $recognizer = New-Object System.Speech.Recognition.SpeechRecognitionEngine
        $recognizer.SetInputToDefaultAudioDevice()
        $recognizer.LoadGrammar((New-Object System.Speech.Recognition.DictationGrammar))
        $result = __RECOGNIZE__
        if ($null -eq $result) { @{success=$false; error='没有识别到语音'} | ConvertTo-Json -Compress }
        else { @{success=$true; text=$result.Text} | ConvertTo-Json -Compress }
        """
    ).replace("__RECOGNIZE__", "$recognizer.Recognize()" if timeout is None else "$recognizer.Recognize((New-TimeSpan -Seconds " + str(max(3, int(timeout))) + "))")
    try:
        process = subprocess.Popen(
            ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="gbk",
            errors="replace",
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        deadline = None if timeout is None else time.monotonic() + max(3, int(timeout)) + 5
        while process.poll() is None:
            if stop_event and stop_event.is_set():
                process.terminate()
                try:
                    process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    process.kill()
                return {"success": False, "cancelled": True, "error": "语音输入已取消"}
            if deadline is not None and time.monotonic() >= deadline:
                process.terminate()
                return {"success": False, "error": "语音输入超时"}
            time.sleep(0.08)
        stdout, stderr = process.communicate(timeout=2)
        completed = type("Completed", (), {"stdout": stdout, "stderr": stderr, "returncode": process.returncode})()
        output = completed.stdout.strip().splitlines()
        data = json.loads(output[-1]) if output else {}
        if completed.returncode and not data:
            return {"success": False, "error": completed.stderr.strip() or "Windows 语音识别启动失败"}
        return data
    except subprocess.TimeoutExpired:
        return {"success": False, "error": "语音输入超时"}
    except Exception as exc:
        return {"success": False, "error": str(exc)}
