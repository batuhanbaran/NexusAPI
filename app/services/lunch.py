import json
import logging

from groq import AsyncGroq

from app.config import settings
from app.schemas.lunch import Mekan

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = (
    "Sen bir yemek mekanı öneri asistanısın. "
    "Kullanıcının istediği koordinata yakın mekanları JSON formatında döndürürsün. "
    "Sadece geçerli JSON array döndür, başka hiçbir metin ekleme."
)

_USER_PROMPT_TEMPLATE = """
{lat}, {lng} koordinatına yakın öğle yemeği için en uygun 10 mekanı listele.

Her mekan için şu alanları içeren bir JSON array döndür:
- isim: mekanın adı (string)
- adres: tam adres (string)
- mutfak_turu: mutfak türü, örn. "Türk", "İtalyan", "Fast Food" (string)
- puan: 1.0 ile 5.0 arasında tahmini puan (float)
- aciklama: 1-2 cümle kısa açıklama (string)
- mesafe_metre: koordinata yaklaşık mesafe metre cinsinden (integer)

Sadece JSON array döndür.
"""


def _get_client() -> AsyncGroq:
    if not settings.groq_api_key:
        raise ValueError("GROQ_API_KEY ayarlanmamış")
    return AsyncGroq(api_key=settings.groq_api_key)


def _parse_mekanlar(raw: str) -> list[Mekan]:
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("```")[1]
        if cleaned.startswith("json"):
            cleaned = cleaned[4:]
        cleaned = cleaned.strip()

    data = json.loads(cleaned)
    if not isinstance(data, list):
        raise ValueError("Yanıt JSON array değil")

    return [Mekan(**item) for item in data]


async def mekan_listesi_getir(lat: float, lng: float) -> list[Mekan]:
    client = _get_client()
    prompt = _USER_PROMPT_TEMPLATE.format(lat=lat, lng=lng)

    try:
        response = await client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=0.7,
        )
        raw_text = response.choices[0].message.content
        logger.debug("Groq ham yanıt: %s", raw_text)
        return _parse_mekanlar(raw_text)
    except json.JSONDecodeError as exc:
        logger.error("Groq yanıtı JSON olarak ayrıştırılamadı: %s", exc)
        raise ValueError("AI servisinden geçersiz yanıt alındı") from exc
    except Exception as exc:
        logger.error("Groq API hatası: %s", exc)
        raise
