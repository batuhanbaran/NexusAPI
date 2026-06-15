from __future__ import annotations

import logging
import random
import string

import resend

from app.cache import otp_cache
from app.config import settings

logger = logging.getLogger(__name__)


def _generate_otp(length: int = 6) -> str:
    return "".join(random.choices(string.digits, k=length))


async def send_otp(mail: str) -> bool:
    """OTP üretir, cache'e kaydeder ve e-posta ile gönderir. Başarılıysa True döner."""
    otp = _generate_otp()
    cache_key = f"otp:{mail}"
    await otp_cache.set(cache_key, otp)

    resend.api_key = settings.resend_api_key

    try:
        resend.Emails.send({
            "from": "NexusAPI <onboarding@resend.dev>",
            "to": [mail],
            "subject": "Giriş Doğrulama Kodunuz",
            "html": f"""
            <div style="font-family: Arial, sans-serif; max-width: 480px; margin: 0 auto; padding: 32px;">
                <h2 style="color: #1a1a1a;">Doğrulama Kodunuz</h2>
                <p style="color: #555;">Aşağıdaki kodu girerek girişinizi tamamlayın:</p>
                <div style="background: #f4f4f5; border-radius: 8px; padding: 24px; text-align: center; margin: 24px 0;">
                    <span style="font-size: 36px; font-weight: bold; letter-spacing: 8px; color: #1a1a1a;">{otp}</span>
                </div>
                <p style="color: #888; font-size: 13px;">Bu kod <strong>2 dakika</strong> geçerlidir. Eğer giriş yapmadıysanız bu e-postayı görmezden gelin.</p>
            </div>
            """,
        })
        logger.info("OTP gönderildi: %s", mail)
        return True
    except Exception as exc:
        logger.exception("OTP gönderilemedi: %s", exc)
        return False


async def verify_otp(mail: str, otp: str) -> bool:
    """OTP doğrular. Doğruysa cache'den siler (tek kullanım)."""
    cache_key = f"otp:{mail}"
    cached = await otp_cache.get(cache_key)
    if cached is None:
        return False
    if cached != otp.strip():
        return False
    # Tek kullanım — doğrulandıktan sonra sil
    await otp_cache.set(cache_key, "__used__")
    return True
