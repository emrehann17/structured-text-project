"""Yerel haber sınıflandırması: tamamlanmış çalışmanın istemi ve üretim ayarları korunmuştur."""

import json
import re
import time

import requests

MODEL = "qwen2.5:3b"
OLLAMA_URL = "http://localhost:11434/api/generate"
CATEGORIES = {"dunya", "ekonomi", "kultur", "saglik", "siyaset", "spor", "teknoloji"}
ENTITY_TYPES = {"person", "organization", "location"}
OPTIONS = {
    "temperature": 0, "seed": 42, "num_ctx": 4096, "num_predict": 384,
    "repeat_penalty": 1.2, "repeat_last_n": 128,
}

JSON_SCHEMA = {
    "type": "object",
    "properties": {
        "category": {"type": "string", "enum": sorted(CATEGORIES)},
        "entities": {
            "type": "object",
            "properties": {
                "person": {"type": "array", "items": {"type": "string"}},
                "organization": {"type": "array", "items": {"type": "string"}},
                "location": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["person", "organization", "location"],
            "additionalProperties": False,
        },
    },
    "required": ["category", "entities"],
    "additionalProperties": False,
}


def build_prompt(text):
    """Haberi, boşluk düzenini koruyarak özgün Türkçe isteme yerleştirir."""
    return f"""
Türkçe haberleri analiz eden bir bilgi çıkarma sistemisin.

HABER KATEGORİLERİ:
- siyaset: Siyasi kararlar, hükümetler, diplomasi
- dunya: Uluslararası genel haberler ve olaylar
- ekonomi: Para, şirketler, finans ve piyasalar
- kultur: Sanat, sinema, müzik ve edebiyat
- saglik: Hastalıklar, tıp ve sağlık
- spor: Sporcular, takımlar ve yarışmalar
- teknoloji: Yazılım, internet ve teknoloji

GÖREV:
1. Haberin ana konusuna göre tek kategori seç.
2. person: Gerçek kişi isimleri.
3. organization: Kurum, şirket ve kuruluşlar.
4. location: Şehir, ülke ve coğrafi yerler.

KESİN KURALLAR:
- Her entity listesinde EN FAZLA 5 isim olsun.
- Aynı ismi ASLA tekrar etme.
- Metinde olmayan isimleri üretme.
- Özel isimleri metindeki yazımıyla koru.
- Gereksiz açıklama yazma.
- Boş entity listeleri için [] kullan.
- Yalnızca JSON şemasına uygun çıktı üret.

HABER:
{text}
"""


def call_ollama(text):
    """Yalnızca yerel sunucudan, parçalara bölünmeden dönen tek bir yanıt ister."""
    response = requests.post(
        OLLAMA_URL,
        json={"model": MODEL, "prompt": build_prompt(text), "stream": False,
              "format": JSON_SCHEMA, "options": OPTIONS},
        timeout=(5, 60),
    )
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, dict) or not isinstance(payload.get("response"), str):
        raise ValueError("Ollama response must contain a string 'response' field")
    return payload


def clean_json_output(raw_output):
    """Tamamlanmış çalışmanın kurtarma kurallarıyla kod çitlerini ve açıklamaları kaldırır.

    İlk ayrıştırılabilir nesneyi korur; eksik süslü parantez veya alan eklemez.
    Kesilmiş girdiden kurtarılan bir parça da şema doğrulamasından geçmelidir.
    """
    cleaned = raw_output.strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    try:
        json.loads(cleaned)
        return cleaned
    except json.JSONDecodeError:
        pass

    decoder = json.JSONDecoder()
    for index, character in enumerate(cleaned):
        if character == "{":
            try:
                _, end = decoder.raw_decode(cleaned[index:])
                return cleaned[index:index + end]
            except json.JSONDecodeError:
                continue
    return cleaned  # Let the caller record failure if recovery was impossible.


def parse_json_response(raw_output):
    """(Ayrıştırılan değer, ilk deneme başarısı, kurtarma sonrası başarı) döndürür."""
    try:
        parsed = json.loads(raw_output)  # No strip, cleaning or repair first.
        return parsed, True, True
    except json.JSONDecodeError:
        cleaned = clean_json_output(raw_output)
        try:
            return json.loads(cleaned), False, True
        except json.JSONDecodeError:
            return None, False, False


def validate_schema(obj):
    """Alanların tamlığını, izin verilen kategoriyi ve üç metin listesini denetler."""
    if not isinstance(obj, dict) or set(obj) != {"category", "entities"}:
        return False
    if not isinstance(obj["category"], str) or obj["category"] not in CATEGORIES:
        return False
    entities = obj["entities"]
    if not isinstance(entities, dict) or set(entities) != ENTITY_TYPES:
        return False
    return all(isinstance(entities[key], list)
               and all(isinstance(value, str) for value in entities[key])
               for key in ENTITY_TYPES)


def evaluate_response(raw_output, true_category=None):
    """Model metnini HTTP sürecinden ve kayıtlı başarı bayraklarından bağımsız değerlendirir."""
    parsed, raw_ok, clean_ok = parse_json_response(raw_output)
    schema_ok = clean_ok and validate_schema(parsed)
    return {
        "raw_json_valid": raw_ok,
        "clean_json_valid": clean_ok,
        "schema_valid": schema_ok,
        "category_correct": bool(schema_ok and parsed["category"] == true_category),
    }


def evaluate_sample(sample):
    """Tek istek yapar; değerlendirme sürebilsin diye API ve biçim hatalarını kaydeder."""
    result = {
        "id": sample["id"], "true_category": sample.get("true_category"),
        "raw_json_valid": False, "clean_json_valid": False,
        "schema_valid": False, "category_correct": False,
        "response_received": False, "api_error": None,
        "raw_output": None, "elapsed_seconds": 0,
    }
    start = time.perf_counter()
    try:
        payload = call_ollama(sample["text"])
        result.update(response_received=True, raw_output=payload["response"],
                      done_reason=payload.get("done_reason"),
                      eval_count=payload.get("eval_count"))
        result.update(evaluate_response(payload["response"], sample.get("true_category")))
    except (requests.RequestException, ValueError, KeyError) as error:
        result["api_error"] = str(error)
    result["elapsed_seconds"] = round(time.perf_counter() - start, 2)
    return result
