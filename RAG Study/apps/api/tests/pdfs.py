"""Small PDFs for ingestion tests. Extraction uses pypdf, same as the worker."""

from io import BytesIO

from pypdf import PdfWriter


def text_pdf(pages: list[str]) -> bytes:
    objects: list[bytes] = []
    page_ids: list[int] = []
    font_id = 3
    next_id = 4
    content_ids: list[tuple[int, bytes]] = []
    for text in pages:
        escaped = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        stream = f"BT /F1 12 Tf 72 720 Td ({escaped}) Tj ET".encode("latin-1")
        content_id = next_id
        page_id = next_id + 1
        next_id += 2
        content_ids.append((content_id, stream))
        page_ids.append(page_id)
        objects.append((page_id, (
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            f"/Contents {content_id} 0 R /Resources << /Font << /F1 {font_id} 0 R >> >> >>"
        ).encode()))

    kids = " ".join(f"{page_id} 0 R" for page_id in page_ids)
    catalog = b"<< /Type /Catalog /Pages 2 0 R >>"
    pages_obj = f"<< /Type /Pages /Kids [{kids}] /Count {len(pages)} >>".encode()
    font = b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"
    numbered = [(1, catalog), (2, pages_obj), (3, font)]
    for content_id, stream in content_ids:
        numbered.append((content_id, b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"\nendstream"))
    numbered.extend(objects)
    numbered.sort(key=lambda item: item[0])

    out = bytearray(b"%PDF-1.4\n")
    offsets = [0] * (numbered[-1][0] + 1)
    for object_id, body in numbered:
        offsets[object_id] = len(out)
        out.extend(f"{object_id} 0 obj\n".encode())
        out.extend(body)
        out.extend(b"\nendobj\n")
    xref = len(out)
    out.extend(f"xref\n0 {len(offsets)}\n".encode())
    out.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        out.extend(f"{offset:010d} 00000 n \n".encode())
    out.extend(
        f"trailer\n<< /Size {len(offsets)} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    )
    return bytes(out)


def blank_pdf() -> bytes:
    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)
    buffer = BytesIO()
    writer.write(buffer)
    return buffer.getvalue()
