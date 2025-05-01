import qrcode

def generate_qr_code(user_id):
    qr_data = f"user_session:{user_id}"
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(qr_data)
    qr.make(fit=True)
    qr_code_img = qr.make_image(fill_color="black", back_color="white")
    qr_code_path = f"static/images/{user_id}_qr.png"
    qr_code_img.save(qr_code_path)
    return qr_code_path