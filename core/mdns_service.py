import socket

from zeroconf import ServiceInfo, Zeroconf


class MdnsService:
    def __init__(self, service_name, port, properties=None, service_type="_companion._tcp.local."):
        self.service_name = service_name
        self.port = port
        self.properties = properties or {}
        self.service_type = service_type
        self._zc = None
        self._info = None

    def start(self, ip=None):
        if ip is None:
            ip = socket.gethostbyname(socket.gethostname())
        addr = socket.inet_aton(ip)
        name = f"{self.service_name}.{self.service_type}"
        props = {k.encode("utf-8"): str(v).encode("utf-8") for k, v in self.properties.items()}
        self._info = ServiceInfo(
            type_=self.service_type,
            name=name,
            addresses=[addr],
            port=self.port,
            properties=props,
        )
        self._zc = Zeroconf()
        self._zc.register_service(self._info)

    def stop(self):
        if self._zc and self._info:
            try:
                self._zc.unregister_service(self._info)
            except Exception:
                pass
        if self._zc:
            try:
                self._zc.close()
            except Exception:
                pass
        self._zc = None
        self._info = None

