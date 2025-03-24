import pyotp
import qrcode
import io
import base64

def generate_2fa_qr_code(secret, identifier):
    totp_uri = pyotp.totp.TOTP(secret).provisioning_uri(name=identifier, issuer_name="Autometa")
    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(totp_uri)
    qr.make(fit=True)
    img = qr.make_image(fill="black", back_color="white")
    buffered = io.BytesIO()
    img.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode("utf-8")