#!/usr/bin/env python3
"""Patch Realme X RMX1901 persistent_properties for headless ADB recovery.

Targets:
  persist.sys.usb.config       -> mtp,adb
  persist.vendor.usb.config    -> mtp,adb (create if absent)
  persist.sys.allcommode       -> true

The Android persistent-properties file is a protobuf-like binary store. This
script updates the existing property messages and appends missing properties,
preserving all unrelated fields byte-for-byte.
"""

from __future__ import annotations

from pathlib import Path
import sys


TARGETS = {
    "persist.sys.usb.config": "mtp,adb",
    "persist.vendor.usb.config": "mtp,adb",
    "persist.sys.allcommode": "true",
}


def read_varint(data: bytes, pos: int) -> tuple[int, int]:
    value = 0
    shift = 0
    while True:
        if pos >= len(data):
            raise ValueError("truncated varint")
        b = data[pos]
        pos += 1
        value |= (b & 0x7F) << shift
        if not (b & 0x80):
            return value, pos
        shift += 7
        if shift >= 64:
            raise ValueError("varint too long")


def enc_varint(value: int) -> bytes:
    out = bytearray()
    while value >= 0x80:
        out.append((value & 0x7F) | 0x80)
        value >>= 7
    out.append(value)
    return bytes(out)


def read_field(data: bytes, pos: int) -> tuple[int, int, int, int]:
    start = pos
    tag, pos = read_varint(data, pos)
    field_no = tag >> 3
    wire_type = tag & 7

    if wire_type == 0:
        _, pos = read_varint(data, pos)
    elif wire_type == 1:
        pos += 8
    elif wire_type == 2:
        length, pos = read_varint(data, pos)
        pos += length
    elif wire_type == 5:
        pos += 4
    else:
        raise ValueError(f"unsupported wire type {wire_type}")

    if pos > len(data):
        raise ValueError("truncated field")

    return start, pos, field_no, wire_type


def get_string_field(message: bytes, wanted_field: int) -> str | None:
    pos = 0
    while pos < len(message):
        start, end, field_no, wire_type = read_field(message, pos)
        if field_no == wanted_field and wire_type == 2:
            _, p = read_varint(message, start)
            length, p = read_varint(message, p)
            return message[p:p + length].decode("utf-8")
        pos = end
    return None


def set_nested_value(message: bytes, new_value: str) -> bytes:
    pos = 0
    out = bytearray()
    replaced = False

    while pos < len(message):
        start, end, field_no, wire_type = read_field(message, pos)
        raw = message[start:end]

        if field_no == 2 and wire_type == 2:
            value = new_value.encode("utf-8")
            out += enc_varint((2 << 3) | 2)
            out += enc_varint(len(value))
            out += value
            replaced = True
        else:
            out += raw
        pos = end

    if not replaced:
        value = new_value.encode("utf-8")
        out += enc_varint((2 << 3) | 2)
        out += enc_varint(len(value))
        out += value

    return bytes(out)


def property_message(name: str, value: str) -> bytes:
    n = name.encode("utf-8")
    v = value.encode("utf-8")
    nested = (
        enc_varint((1 << 3) | 2)
        + enc_varint(len(n)) + n
        + enc_varint((2 << 3) | 2)
        + enc_varint(len(v)) + v
    )
    return enc_varint((1 << 3) | 2) + enc_varint(len(nested)) + nested


def patch(data: bytes) -> tuple[bytes, list[tuple[str, str | None, str]]]:
    pos = 0
    out = bytearray()
    seen: dict[str, int] = {name: 0 for name in TARGETS}
    changes: list[tuple[str, str | None, str]] = []

    while pos < len(data):
        start, end, field_no, wire_type = read_field(data, pos)
        raw = data[start:end]

        if field_no == 1 and wire_type == 2:
            _, p = read_varint(data, start)
            outer_len, p = read_varint(data, p)
            nested = data[p:p + outer_len]
            name = get_string_field(nested, 1)

            if name in TARGETS:
                seen[name] += 1
                if seen[name] > 1:
                    raise ValueError(f"duplicate property entry: {name}")
                old = get_string_field(nested, 2)
                new = TARGETS[name]
                nested = set_nested_value(nested, new)
                rebuilt = enc_varint((1 << 3) | 2) + enc_varint(len(nested)) + nested
                out += rebuilt
                changes.append((name, old, new))
            else:
                out += raw
        else:
            out += raw

        pos = end

    for name, new in TARGETS.items():
        if seen[name] == 0:
            out += property_message(name, new)
            changes.append((name, None, new))

    return bytes(out), changes


def main() -> int:
    if len(sys.argv) != 3:
        print(f"Usage: {sys.argv[0]} INPUT OUTPUT", file=sys.stderr)
        return 2

    src = Path(sys.argv[1])
    dst = Path(sys.argv[2])

    data = src.read_bytes()
    patched, changes = patch(data)
    dst.write_bytes(patched)

    print(f"Size: {len(data)} -> {len(patched)} bytes")
    for name, old, new in changes:
        old_display = "<missing>" if old is None else old
        print(f"{name}: {old_display} -> {new}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
