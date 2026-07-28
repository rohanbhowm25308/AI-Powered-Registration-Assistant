"""
QR Code Verification.

Each registration gets a QR code that encodes a verification URL
(/api/verify/<reg_id>). Scanning it — or visiting the link directly —
shows a styled page confirming the registration is genuine, without
exposing any editable data.
"""
import io
import qrcode


def make_qr_png(data, box_size=8, border=2):
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=box_size,
        border=border,
    )
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#04060c", back_color="#eaf1ff")

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf
