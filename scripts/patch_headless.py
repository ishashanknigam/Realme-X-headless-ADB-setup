#!/usr/bin/env python3
"""Patch Realme X RMX1901 persistent_properties for headless ADB recovery.

This ColorOS persistent-properties file stores a sequence of records with an
extra 0x0d separator byte before the outer protobuf field and before each
nested PersistentPropertyRecord. The outer length counts only the protobuf
bytes after that nested 0x0d separator.

Targets:
  persist.sys.usb.config       -> mtp,adb
  persist.vendor.usb.config    -> mtp,adb (create if absent)
  persist.sys.allcommode       -> true

Unrelated records are preserved byte-for-byte.
"""

from __future__ import annotations

from pathlib import Path
import sys

TARGETS = {
    "persist.sys.usb.config": "mtp,adb",
    "persist.vendor.usb.config": "mtp,adb",
    "persist.sys.allcommode": "true",
}

FRAME = b"\x0d"


def read_varint(data: bytes, pos: int) -> tuple[int, int]:
    value = 0
    shift = 0
    while True:
        if pos >= len(data):
            raise ValueError(f"truncated varint at offset {pos}")
        b = data[pos]
        pos += 1
        value |= (b & 0x7f) << shift
        if not (b & 0x80):
            return value, pos
        shift += 7
        if shift >= 64:
            raise ValueError("varint too long")


def enc_varint(value: int) -> bytes:
    if value < 0:
        raise ValueError("negative varint")
    out = bytearray()
    while value >= 0x80:
        out.append((value & 0x7f) | 0x80)
        value >>= 7
    out.append(value)
    return bytes(out)


def read_field(data: bytes, pos: int) -> tuple[int, int, int, int]:
    start = pos
    tag, pos = read_varint(data, pos)
    field_no = tag >> 3
    wire_type = tag & 7

    if field_no == 0:
        raise ValueError(f"invalid field number 0 at offset {start}")

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
        raise ValueError(f"unsupported wire type {wire_type} at offset {start}")

    if pos > len(data):
        raise ValueError(f"truncated field at offset {start}")

    return start, pos, field_no, wire_type


def get_string_field(nested_bytes: bytes, wanted_field: int) -> str | None:
    message = nested_bytes[1:] if nested_bytes.startswith(FRAME) else nested_bytes
    pos = 0
    while pos < len(message):
        start, end, field_no, wire_type = read_field(message, pos)
        if field_no == wanted_field and wire_type == 2:
            _, p = read_varint(message, start)
            length, p = read_varint(message, p)
            raw = message[p:p + length]
            return raw.decode("utf-8")
        pos = end
    return None


def set_nested_value(nested_bytes: bytes, new_value: str) -> bytes:
    has_frame = nested_bytes.startswith(FRAME)
    message = nested_bytes[1:] if has_frame else nested_bytes
    value = new_value.encode("utf-8")

    pos = 0
    out = bytearray()
    replaced = False

    while pos < len(message):
        start, end, field_no, wire_type = read_field(message, pos)
        raw = message[start:end]

        if field_no == 2 and wire_type == 2:
            out += bytes([0x12])
            out += enc_varint(len(value))
            out += value
            replaced = True
        else:
            out += raw

        pos = end

    if not replaced:
        out += bytes([0x12])
        out += enc_varint(len(value))
        out += value

    return (FRAME + bytes(out)) if has_frame else bytes(out)


def property_message(name: str, value: str, has_outer_frame: bool, has_inner_frame: bool) -> bytes:
    n = name.encode("utf-8")
    v = value.encode("utf-8")

    inner = (
        bytes([0x0a]) + enc_varint(len(n)) + n
        + bytes([0x12]) + enc_varint(len(v)) + v
    )

    if has_inner_frame:
        inner = FRAME + inner
        inner_len = len(inner) - 1
    else:
        inner_len = len(inner)

    out = bytes([0x0a]) + enc_varint(inner_len) + inner
    if has_outer_frame:
        out = FRAME + out

    return out


def parse_record(data: bytes, pos: int) -> tuple[int, bytes, str | None, str | None, bool, bool]:
    start = pos
    has_outer_frame = False

    if data[pos:pos + 1] == FRAME:
        has_outer_frame = True
        pos += 1

    tag_start = pos
    tag, pos = read_varint(data, pos)
    if tag != 0x0a:
        raise ValueError(f"expected outer field 1/tag 0x0a at offset {tag_start}, got 0x{tag:x}")

    outer_len, pos = read_varint(data, pos)

    nested_start = pos
    has_inner_frame = False
    if data[nested_start:nested_start + 1] == FRAME:
        has_inner_frame = True

    if has_inner_frame:
        inner_start = nested_start + 1
    else:
        inner_start = nested_start

    inner_end = inner_start + outer_len
    if inner_end > len(data):
        raise ValueError(
            f"truncated nested record at offset {start}: "
            f"need {outer_len} bytes, have {len(data) - inner_start}"
        )

    record_end = inner_end
    nested = data[nested_start:inner_end]
    name = get_string_field(nested, 1)
    value = get_string_field(nested, 2)

    return record_end, nested, name, value, has_outer_frame, has_inner_frame


def patch(data: bytes) -> tuple[bytes, list[tuple[str, str | None, str]]]:
    pos = 0
    out = bytearray()
    seen: dict[str, int] = {name: 0 for name in TARGETS}
    changes: list[tuple[str, str | None, str]] = []

    uses_outer_frame = False
    uses_inner_frame = False

    while pos < len(data):
        record_end, nested, name, old, has_outer_frame, has_inner_frame = parse_record(data, pos)
        uses_outer_frame = has_outer_frame
        uses_inner_frame = has_inner_frame

        if name in TARGETS:
            seen[name] += 1
            if seen[name] > 1:
                raise ValueError(f"duplicate property entry: {name}")

            new = TARGETS[name]
            patched_nested = set_nested_value(nested, new)

            if has_inner_frame:
                inner_len = len(patched_nested) - 1
            else:
                inner_len = len(patched_nested)

            rebuilt = bytearray()
            if has_outer_frame:
                rebuilt += FRAME
            rebuilt += bytes([0x0a]) + enc_varint(inner_len) + patched_nested

            out += rebuilt
            changes.append((name, old, new))
        else:
            out += data[pos:record_end]

        pos = record_end

    for name, value in TARGETS.items():
        if seen[name] == 0:
            out += property_message(name, value, uses_outer_frame, uses_inner_frame)
            changes.append((name, None, value))

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

    print(f"Input : {src} ({len(data)} bytes)")
    print(f"Output: {dst} ({len(patched)} bytes)")
    for name, old, new in changes:
        print(f"{name}: {old!r} -> {new!r}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
