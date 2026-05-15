"""
Pure-Python Tuya local-protocol client (v3.3 / v3.5).

Implements just enough of the Tuya LAN protocol to:
  - Query device status  (command 10)
  - Send DPS updates     (command 13)

No third-party libraries required — only the Python standard library
plus the `cryptography` package (already present in HA's venv).

Wire format (each frame):
  Prefix  4 bytes  0x000055AA
  SeqNo   4 bytes  uint32 big-endian
  Cmd     4 bytes  uint32 big-endian
  Len     4 bytes  uint32 big-endian  (payload + suffix length)
  Payload variable
  CRC     4 bytes  uint32 big-endian
  Suffix  4 bytes  0x0000AA55

v3.3 payload: <version_str> <padding_to_15> <AES-128-ECB encrypted JSON>
v3.5 payload: <header (15 bytes)> <AES-128-GCM encrypted JSON>
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import socket
import struct
import time
from typing import Any, Optional

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend

_LOGGER = logging.getLogger(__name__)

_PREFIX = b"\x00\x00\x55\xaa"
_SUFFIX = b"\x00\x00\xaa\x55"

CMD_STATUS = 10
CMD_SET    = 13


# ──────────────────────────────────────────────────────────────
# AES helpers
# ──────────────────────────────────────────────────────────────

def _aes_ecb_encrypt(key: bytes, data: bytes) -> bytes:
    """PKCS#7-pad then AES-ECB encrypt."""
    pad = 16 - len(data) % 16
    data += bytes([pad] * pad)
    cipher = Cipher(algorithms.AES(key), modes.ECB(), backend=default_backend())
    enc = cipher.encryptor()
    return enc.update(data) + enc.finalize()


def _aes_ecb_decrypt(key: bytes, data: bytes) -> bytes:
    cipher = Cipher(algorithms.AES(key), modes.ECB(), backend=default_backend())
    dec = cipher.decryptor()
    plain = dec.update(data) + dec.finalize()
    # Remove PKCS#7 padding
    return plain[: -plain[-1]]


def _aes_gcm_encrypt(key: bytes, nonce: bytes, data: bytes) -> tuple[bytes, bytes]:
    """Return (ciphertext, tag)."""
    cipher = Cipher(
        algorithms.AES(key), modes.GCM(nonce), backend=default_backend()
    )
    enc = cipher.encryptor()
    ct = enc.update(data) + enc.finalize()
    return ct, enc.tag


def _aes_gcm_decrypt(key: bytes, nonce: bytes, ct: bytes, tag: bytes) -> bytes:
    cipher = Cipher(
        algorithms.AES(key), modes.GCM(nonce, tag), backend=default_backend()
    )
    dec = cipher.decryptor()
    return dec.update(ct) + dec.finalize()


# ──────────────────────────────────────────────────────────────
# Frame helpers
# ──────────────────────────────────────────────────────────────

def _crc32(data: bytes) -> int:
    import binascii
    return binascii.crc32(data) & 0xFFFFFFFF


def _build_frame(seq: int, cmd: int, payload: bytes) -> bytes:
    length = len(payload) + 8  # 4-byte CRC + 4-byte suffix
    header = _PREFIX + struct.pack(">IIII", seq, cmd, length, 0)
    # Re-pack with CRC over prefix+seq+cmd+len+payload
    body = struct.pack(">III", seq, cmd, length) + payload
    crc = _crc32(_PREFIX + body)
    return _PREFIX + body + struct.pack(">I", crc) + _SUFFIX


def _parse_frames(data: bytes) -> list[bytes]:
    """Split a byte stream into individual Tuya frames, return payloads."""
    frames = []
    while True:
        start = data.find(_PREFIX)
        if start == -1:
            break
        data = data[start:]
        if len(data) < 20:
            break
        _seq, cmd, length = struct.unpack(">III", data[4:16])
        total = 16 + length  # prefix(4) + seq+cmd+len(12) + length
        if len(data) < total:
            break
        frame = data[:total]
        # payload is everything between the 16-byte header and the last 8 bytes (crc+suffix)
        payload = frame[16 : total - 8]
        frames.append(payload)
        data = data[total:]
    return frames


# ──────────────────────────────────────────────────────────────
# TuyaClient
# ──────────────────────────────────────────────────────────────

class TuyaClient:
    """Minimal Tuya LAN client supporting protocol v3.3 and v3.5."""

    def __init__(
        self,
        ip: str,
        device_id: str,
        local_key: str,
        version: float = 3.5,
        timeout: int = 5,
    ) -> None:
        self._ip = ip
        self._device_id = device_id
        self._local_key = local_key.encode()[:16]  # must be 16 bytes
        self._version = version
        self._timeout = timeout
        self._seq = 1

    # ── Low-level I/O ────────────────────────────────────────

    def _send_recv(self, cmd: int, payload: bytes) -> bytes:
        frame = _build_frame(self._seq, cmd, payload)
        self._seq += 1
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(self._timeout)
            sock.connect((self._ip, 6668))
            sock.sendall(frame)
            chunks = []
            try:
                while True:
                    chunk = sock.recv(4096)
                    if not chunk:
                        break
                    chunks.append(chunk)
            except socket.timeout:
                pass
        return b"".join(chunks)

    # ── Payload encoding ─────────────────────────────────────

    def _encode_payload(self, data: dict) -> bytes:
        json_bytes = json.dumps(data, separators=(",", ":")).encode()
        if self._version >= 3.5:
            return self._encode_v35(json_bytes)
        return self._encode_v33(json_bytes)

    def _encode_v33(self, json_bytes: bytes) -> bytes:
        encrypted = _aes_ecb_encrypt(self._local_key, json_bytes)
        version_prefix = b"3.3" + b"\x00" * 12  # 15 bytes
        return version_prefix + encrypted

    def _encode_v35(self, json_bytes: bytes) -> bytes:
        import os
        nonce = os.urandom(12)
        ct, tag = _aes_gcm_encrypt(self._local_key, nonce, json_bytes)
        # v3.5 header: version(3) + padding(12) = 15 bytes, then nonce(12), ct, tag(16)
        header = b"3.5" + b"\x00" * 12
        return header + nonce + ct + tag

    # ── Payload decoding ─────────────────────────────────────

    def _decode_payload(self, payload: bytes) -> Optional[dict]:
        if len(payload) < 15:
            return None
        version_str = payload[:3].decode("ascii", errors="ignore")
        body = payload[15:]
        try:
            if version_str == "3.5":
                return self._decode_v35(body)
            return self._decode_v33(body)
        except Exception as exc:
            _LOGGER.debug("Payload decode error: %s", exc)
            return None

    def _decode_v33(self, body: bytes) -> Optional[dict]:
        plain = _aes_ecb_decrypt(self._local_key, body)
        return json.loads(plain)

    def _decode_v35(self, body: bytes) -> Optional[dict]:
        # nonce(12) + ciphertext + tag(16)
        nonce = body[:12]
        tag   = body[-16:]
        ct    = body[12:-16]
        plain = _aes_gcm_decrypt(self._local_key, nonce, ct, tag)
        return json.loads(plain)

    # ── Public API ───────────────────────────────────────────

    def get_status(self) -> Optional[dict]:
        """Return the full DPS status dict, or None on failure."""
        payload_dict = {
            "gwId":  self._device_id,
            "devId": self._device_id,
            "uid":   self._device_id,
            "t":     str(int(time.time())),
        }
        raw_payload = json.dumps(payload_dict, separators=(",", ":")).encode()
        try:
            raw = self._send_recv(CMD_STATUS, raw_payload)
        except Exception as exc:
            _LOGGER.error("get_status network error (%s): %s", self._ip, exc)
            return None

        for payload_bytes in _parse_frames(raw):
            result = self._decode_payload(payload_bytes)
            if result and "dps" in result:
                return result["dps"]
            # Some firmware sends status wrapped differently
            if isinstance(result, dict):
                for v in result.values():
                    if isinstance(v, dict) and "dps" in v:
                        return v["dps"]
        _LOGGER.debug("get_status: no dps in response from %s", self._ip)
        return None

    def set_dps(self, dps: dict) -> bool:
        """Send DPS update. Returns True on apparent success."""
        payload_dict = {
            "devId": self._device_id,
            "uid":   self._device_id,
            "t":     str(int(time.time())),
            "dps":   dps,
        }
        try:
            encoded = self._encode_payload(payload_dict)
            raw = self._send_recv(CMD_SET, encoded)
        except Exception as exc:
            _LOGGER.error("set_dps network error (%s): %s", self._ip, exc)
            return False

        for payload_bytes in _parse_frames(raw):
            result = self._decode_payload(payload_bytes)
            if isinstance(result, dict) and result.get("error"):
                _LOGGER.warning("set_dps error response: %s", result)
                return False
        return True
