"""coolest-art-01 v3 entry: ship the bundled artwork to the output dir.

The artwork is a single bundled image (entry.png next to this file).
This script only copies it to $MAKEFUN_OUTPUT_DIR/entry.png after
checking the competition gates itself, so a bad bundle fails loudly
instead of silently submitting a non-compliant image.
"""

import hashlib
import os
import struct
import sys

MAX_BYTES = 1_048_576
MAX_SIDE = 1024


def fail(message):
    print("gate failed: " + message, file=sys.stderr)
    raise SystemExit(1)


def jpeg_dimensions(blob):
    """Walk JPEG markers until the first Start-Of-Frame; return (w, h)."""
    if blob[:2] != b"\xff\xd8":
        return None
    pos = 2
    while pos + 9 < len(blob):
        if blob[pos] != 0xFF:
            return None
        marker = blob[pos + 1]
        if marker in (0xD8, 0xD9) or 0xD0 <= marker <= 0xD7:
            pos += 2
            continue
        size = struct.unpack(">H", blob[pos + 2:pos + 4])[0]
        if 0xC0 <= marker <= 0xCF and marker not in (0xC4, 0xC8, 0xCC):
            height, width = struct.unpack(">HH", blob[pos + 5:pos + 9])
            return (width, height)
        pos += 2 + size
    return None


def png_dimensions(blob):
    """Read width/height out of a PNG IHDR chunk; return (w, h)."""
    if blob[:8] != b"\x89PNG\r\n\x1a\n":
        return None
    if blob[12:16] != b"IHDR":
        return None
    width, height = struct.unpack(">II", blob[16:24])
    return (width, height)


def measure(blob):
    """Return (width, height, kind) for a PNG or JPEG blob, or fail."""
    dims = jpeg_dimensions(blob)
    if dims is not None:
        return dims[0], dims[1], "JPEG"
    dims = png_dimensions(blob)
    if dims is not None:
        return dims[0], dims[1], "PNG"
    fail("entry.png is neither a JPEG nor a PNG")


def check_gates(blob):
    """Enforce the competition's image gates; return (w, h, kind)."""
    if len(blob) > MAX_BYTES:
        fail("entry.png is %d bytes, over the 1 MiB cap" % len(blob))
    width, height, kind = measure(blob)
    if width > MAX_SIDE or height > MAX_SIDE:
        fail("entry.png is %dx%d, over the 1024x1024 cap" % (width, height))
    if kind == "JPEG" and not blob.rstrip(b"\x00").endswith(b"\xff\xd9"):
        fail("JPEG does not end with an EOI marker (truncated image)")
    if kind == "PNG":
        # An IEND chunk is exactly 12 bytes: zero length, "IEND", CRC.
        tail = blob[-12:]
        if len(tail) != 12 or tail[:4] != b"\x00\x00\x00\x00" \
                or tail[4:8] != b"IEND":
            fail("PNG does not end with an IEND chunk (truncated image)")
    return width, height, kind


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    source_path = os.path.join(here, "entry.png")
    with open(source_path, "rb") as handle:
        blob = handle.read()
    width, height, kind = check_gates(blob)
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(out_dir, exist_ok=True)
    dest_path = os.path.join(out_dir, "entry.png")
    with open(dest_path, "wb") as handle:
        handle.write(blob)
    with open(dest_path, "rb") as handle:
        written = handle.read()
    if hashlib.sha256(written).hexdigest() != hashlib.sha256(blob).hexdigest():
        fail("written entry.png differs from the bundled image")
    print("wrote %s (%s %dx%d, %d bytes)"
          % (dest_path, kind, width, height, len(blob)))


if __name__ == "__main__":
    main()
