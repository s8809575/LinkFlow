import platform
import subprocess


class HotspotService:
    def __init__(self, ssid="LinkFlow", key=None):
        self.ssid = ssid
        self.key = key

    def start(self):
        if platform.system().lower() != "windows":
            return {"status": "fail", "error": "UNSUPPORTED_OS"}

        if not self.key:
            return {"status": "fail", "error": "MISSING_KEY"}

        try:
            subprocess.run(
                ["netsh", "wlan", "set", "hostednetwork", "mode=allow", f"ssid={self.ssid}", f"key={self.key}"],
                check=True,
                capture_output=True,
                text=True,
            )
            subprocess.run(["netsh", "wlan", "start", "hostednetwork"], check=True, capture_output=True, text=True)
            return {"status": "ok"}
        except subprocess.CalledProcessError as e:
            return {"status": "fail", "error": "NETSH_FAIL", "detail": (e.stderr or e.stdout or "").strip()}

    def stop(self):
        if platform.system().lower() != "windows":
            return {"status": "fail", "error": "UNSUPPORTED_OS"}

        try:
            subprocess.run(["netsh", "wlan", "stop", "hostednetwork"], check=True, capture_output=True, text=True)
            return {"status": "ok"}
        except subprocess.CalledProcessError as e:
            return {"status": "fail", "error": "NETSH_FAIL", "detail": (e.stderr or e.stdout or "").strip()}

