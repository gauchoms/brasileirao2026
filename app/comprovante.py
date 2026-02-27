import hashlib
import time
from datetime import datetime

SECRET_SALT = "brasileirao2026_salt_secreto_mude_isso"  # MUDE PARA ALGO ÚNICO!

def gerar_hash_palpite(usuario_id, jogo_id, gols_casa, gols_fora, timestamp):
    """
    Gera hash SHA-256 imutável do palpite
    """
    dados = f"{usuario_id}|{jogo_id}|{gols_casa}|{gols_fora}|{timestamp}|{SECRET_SALT}"
    return hashlib.sha256(dados.encode()).hexdigest()

def validar_hash_palpite(palpite):
    """
    Valida se o hash do palpite é autêntico
    """
    hash_calculado = gerar_hash_palpite(
        palpite.usuario_id,
        palpite.jogo_id,
        palpite.gols_casa_palpite,
        palpite.gols_fora_palpite,
        palpite.timestamp_preciso
    )
    return hash_calculado == palpite.hash_comprovante

def gerar_qr_code(hash_comprovante):
    """
    Gera QR Code do comprovante
    """
    import qrcode
    from io import BytesIO
    import base64
    
    url_verificacao = f"https://brasileirao2026.onrender.com/verificar/{hash_comprovante}"
    
    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(url_verificacao)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    buffer = BytesIO()
    img.save(buffer, format='PNG')
    img_base64 = base64.b64encode(buffer.getvalue()).decode()
    
    return img_base64