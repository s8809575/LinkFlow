#!/usr/bin/env python3
"""Module A/B/C/D mock endpoints for isolated development."""
from dataclasses import dataclass

@dataclass(frozen=True)
class PairingContextDTO:
    schema_version: str
    host_ipv4: str
    port: int
    pairing_id: str
    key_b64: str

@dataclass(frozen=True)
class RpcSessionDTO:
    schema_version: str
    session_id: str
    connected: bool
    secure_channel: bool
    host_ipv4: str
    port: int

def mock_discover() -> PairingContextDTO:
    return PairingContextDTO('1.0.0','192.168.137.1',8089,'pair-demo-001','AAAAAAAAAAAAAAAAAAAAAA==')

def mock_connect(ctx: PairingContextDTO) -> RpcSessionDTO:
    return RpcSessionDTO('1.0.0','sess-demo-001',True,True,ctx.host_ipv4,ctx.port)

def mock_rpc(method: str, params: dict) -> dict:
    if method == 'system.stats':
        return {'cpu_percent': 22.5, 'memory_percent': 48.1, 'battery_percent': 87, 'os_info': 'Windows 11'}
    if method == 'file.read_chunk':
        return {'path': params.get('path','C:/x.bin'), 'offset': params.get('offset',0), 'size': 262144, 'crc32': 123456789, 'eof': False, 'data_b64': 'AA=='}
    return {'status': 'ok'}
