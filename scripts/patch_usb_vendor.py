from pathlib import Path

SRC = Path("persistent_properties-current.bin")
DST = Path("persistent_properties-vendor-adb.bin")

TARGET_SYS = "persist.sys.usb.config"
TARGET_VENDOR = "persist.vendor.usb.config"
OLD = "midi"
NEW = "mtp,adb"


def enc_varint(n):
    out = bytearray()
    while n >= 0x80:
        out.append((n & 0x7f) | 0x80)
        n >>= 7
    out.append(n)
    return bytes(out)


def dec_varint(buf, pos):
    value = 0
    shift = 0

    while True:
        if pos >= len(buf):
            raise ValueError("truncated varint")

        b = buf[pos]
        pos += 1
        value |= (b & 0x7f) << shift

        if b < 0x80:
            return value, pos

        shift += 7


def iter_fields(buf):
    pos = 0

    while pos < len(buf):
        start = pos
        tag, pos = dec_varint(buf, pos)

        field_no = tag >> 3
        wire = tag & 7

        if wire == 0:
            _, pos = dec_varint(buf, pos)
        elif wire == 1:
            pos += 8
        elif wire == 2:
            length, pos = dec_varint(buf, pos)
            pos += length
        elif wire == 5:
            pos += 4
        else:
            raise ValueError(f"unsupported wire type {wire}")

        if pos > len(buf):
            raise ValueError("field extends past buffer")

        yield field_no, wire, buf[start:pos]


def decode_record(record):
    name = None
    value = None

    for field_no, wire, raw in iter_fields(record):
        if wire != 2:
            continue

        _, p = dec_varint(raw, 0)
        length, p = dec_varint(raw, p)
        payload = raw[p:p + length]

        if field_no == 1:
            name = payload.decode(errors="replace")
        elif field_no == 2:
            value = payload.decode(errors="replace")

    return name, value


def rebuild_record(record, new_value):
    out = bytearray()

    for field_no, wire, raw in iter_fields(record):
        if field_no == 2 and wire == 2:
            value = new_value.encode()
            out += enc_varint((2 << 3) | 2)
            out += enc_varint(len(value))
            out += value
        else:
            out += raw

    return bytes(out)


data = SRC.read_bytes()

out = bytearray()
found_sys = False
found_vendor = False

for field_no, wire, raw in iter_fields(data):
    if field_no != 1 or wire != 2:
        out += raw
        continue

    _, p = dec_varint(raw, 0)
    length, p = dec_varint(raw, p)
    record = raw[p:p + length]

    name, value = decode_record(record)

    if name == TARGET_SYS and value == OLD:
        record = rebuild_record(record, NEW)
        found_sys = True

    elif name == TARGET_VENDOR:
        record = rebuild_record(record, NEW)
        found_vendor = True

    out += (
        enc_varint((1 << 3) | 2)
        + enc_varint(len(record))
        + record
    )

# Add vendor property if it did not already exist.
if not found_vendor:
    name = TARGET_VENDOR.encode()
    value = NEW.encode()

    record = (
        enc_varint((1 << 3) | 2)
        + enc_varint(len(name))
        + name
        + enc_varint((2 << 3) | 2)
        + enc_varint(len(value))
        + value
    )

    out += (
        enc_varint((1 << 3) | 2)
        + enc_varint(len(record))
        + record
    )

if not found_sys:
    raise SystemExit(
        f"ERROR: {TARGET_SYS}={OLD} was not found"
    )

DST.write_bytes(out)

print(f"Input : {len(data)} bytes")
print(f"Output: {len(out)} bytes")
print(f"Changed: {TARGET_SYS}={OLD} -> {NEW}")
print(f"{'Updated' if found_vendor else 'Added'}: "
      f"{TARGET_VENDOR}={NEW}")
print(f"Size difference: {len(out) - len(data):+d} bytes")
