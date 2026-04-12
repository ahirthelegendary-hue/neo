import socket
import platform
import uuid

class TrustedGuard:
    def __init__(self):
        self.local_ips = self._get_local_ips()
        self.device_id = self._get_device_id()

    def _get_local_ips(self):
        ips = ["127.0.0.1", "::1"]
        try:
            hostname = socket.gethostname()
            local_ip = socket.gethostbyname(hostname)
            ips.append(local_ip)
        except:
            pass
        return ips

    def _get_device_id(self):
        return f"{platform.node()}-{uuid.getnode()}"

    def is_local(self, ip: str) -> bool:
        return ip in self.local_ips

    def is_private(self, ip: str) -> bool:
        return (
            ip.startswith("192.168.") or
            ip.startswith("10.") or
            ip.startswith("172.")
        )

    def is_trusted_device(self) -> bool:
        return self._get_device_id() == self.device_id

    def is_safe(self, ip: str) -> bool:
        return self.is_local(ip) or self.is_private(ip) or self.is_trusted_device()