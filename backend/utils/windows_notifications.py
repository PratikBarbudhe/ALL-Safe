"""Windows 10/11 native toast notifications for AllSafe security alerts."""

from __future__ import annotations

import logging
import subprocess
import sys
from typing import Any

logger = logging.getLogger(__name__)

_WINOTIFY_AVAILABLE = False
if sys.platform == "win32":
    try:
        from winotify import audio, notification  # type: ignore[import-untyped]

        _WINOTIFY_AVAILABLE = True
    except ImportError:
        audio = None  # type: ignore[assignment,misc]
        notification = None  # type: ignore[assignment,misc]


SEVERITY_TOAST_AUDIO: dict[str, Any] = {}


def _escape_xml(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )


def show_toast(
    *,
    title: str,
    message: str,
    severity: str = "info",
    app_id: str = "AllSafe Security",
    critical_popup: bool = False,
) -> bool:
    """
    Display a Windows toast notification. Returns True if a toast was attempted.
    Falls back to PowerShell BurntToast/XML when winotify is unavailable.
    """
    if sys.platform != "win32":
        return False

    title = title[:128]
    message = message[:256]

    if _WINOTIFY_AVAILABLE and notification is not None:
        try:
            toast = notification.Notification(
                app_id=app_id,
                title=title,
                msg=message,
                duration="long" if severity in ("high", "critical") else "short",
            )
            if severity == "critical" and audio is not None:
                toast.set_audio(audio.LoopingAlarm, loop=True)
            elif severity in ("high", "warning") and audio is not None:
                toast.set_audio(audio.Reminder, loop=False)
            toast.show()
            return True
        except Exception as exc:
            logger.warning("winotify toast failed: %s", exc)

    return _show_powershell_toast(
        title=title,
        message=message,
        severity=severity,
        critical_popup=critical_popup,
    )


def _show_powershell_toast(
    *,
    title: str,
    message: str,
    severity: str,
    critical_popup: bool,
) -> bool:
    """Fallback toast via Windows Runtime XML template."""
    try:
        if critical_popup and severity == "critical":
            script = f"""
            Add-Type -AssemblyName PresentationFramework
            [System.Windows.MessageBox]::Show(
                '{_escape_xml(message)}',
                '{_escape_xml(title)}',
                'OK',
                'Warning'
            )
            """
            subprocess.run(
                ["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
                capture_output=True,
                timeout=30,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            return True

        xml = f"""
<toast activationType="protocol" launch="allsafe://alert">
  <visual>
    <binding template="ToastGeneric">
      <text>{_escape_xml(title)}</text>
      <text>{_escape_xml(message)}</text>
    </binding>
  </visual>
  <audio src="{"ms-winsoundevent:Notification.Looping.Alarm" if severity == "critical" else "ms-winsoundevent:Notification.Default"}" loop="{"true" if severity == "critical" else "false"}" />
</toast>
"""
        script = f"""
[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
[Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom.XmlDocument, ContentType = WindowsRuntime] | Out-Null
$xml = New-Object Windows.Data.Xml.Dom.XmlDocument
$xml.LoadXml(@'
{xml.strip()}
'@)
$toast = [Windows.UI.Notifications.ToastNotification]::new($xml)
[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier('AllSafe Security').Show($toast)
"""
        subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
            capture_output=True,
            timeout=15,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        return True
    except Exception as exc:
        logger.warning("PowerShell toast failed: %s", exc)
        return False
