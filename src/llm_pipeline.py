"""Yerel haber sınıflandırması ve varlık çıkarımı (Qwen2.5:3b, Ollama).

İki deney ayarı vardır ve aralarındaki TEK fark Ollama `format` alanıdır:
    mode="prompt"  -> JSON yalnızca istemde istenir; istekte `format` anahtarı HİÇ yoktur.
    mode="schema"  -> istek gövdesine `format=JSON_SCHEMA` eklenir.
Model, istem, sıcaklık, tohum, bağlam uzunluğu ve üretim sınırı iki ayarda aynıdır.
"""

import json
import hashlib
import math
import re
import time

import requests

MODEL = "qwen2.5:3b"
OLLAMA_URL = "http://localhost:11434/api/generate"
CATEGORIES = {"dunya", "ekonomi", "kultur", "saglik", "siyaset", "spor", "teknoloji"}
ENTITY_TYPES = {"person", "organization", "location"}
MODES = ("prompt", "schema")
# İki modda da aynı açık üretim ayarları kullanılır.
OPTIONS = {
    "temperature": 0, "seed": 42, "num_ctx": 4096, "num_predict": 1024,
    "repeat_penalty": 1.2, "repeat_last_n": 128,
    "top_k": 40, "top_p": 0.9, "min_p": 0,
    "presence_penalty": 0, "frequency_penalty": 0,
}
PROMPT_VERSION = "manual-study-v1"

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

OUTPUT_FORMAT_BLOCK = """
ÇIKTI BİÇİMİ (yalnızca bu yapıda tek bir JSON nesnesi döndür):
{"category": "<kategori>", "entities": {"person": [], "organization": [], "location": []}}
"""


def build_prompt(text):
    """Aynı görev tanımını iki deney ayarı için de üretir."""
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
- Metindeki tüm kişi, kurum ve yer adlarını çıkar; isim sayısına sınır koyma.
- Aynı ismi ASLA tekrar etme.
- Metinde olmayan isimleri üretme.
- Özel isimleri metindeki yazımıyla koru.
- Unvanları ve çekim eklerini isme dahil etme; metindeki en uzun açık adı kullan.
- Bir adın kısa ve uzun biçimi metinde ayrı ayrı geçiyorsa her farklı yazımı çıkar.
- Ürün, etkinlik ve kurmaca karakter adlarını dahil etme.
- Kulüp ve milli takım adları kurumdur; coğrafi anlamdaki ülkeler ve şehirler yerdir.
- Gereksiz açıklama yazma.
- Boş entity listeleri için [] kullan.
- Yalnızca JSON şemasına uygun çıktı üret.
{OUTPUT_FORMAT_BLOCK}
HABER:
{text}
"""


def build_options(temperature=0):
    """Sabit üretim ayarlarını kopyalar; deneyler arasında yalnızca sıcaklık değişir."""
    if not math.isfinite(temperature) or temperature < 0:
        raise ValueError("temperature must be finite and nonnegative")
    return dict(OPTIONS, temperature=temperature)


def fingerprint(value):
    """Stable SHA-256 for text or a JSON configuration."""
    text = value if isinstance(value, str) else json.dumps(value, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def build_request(text, mode="schema", temperature=0):
    """Ollama istek gövdesi. Prompt-only modunda `format` anahtarı tamamen çıkarılır."""
    if mode not in MODES:
        raise ValueError(f"mode must be one of {MODES}, got {mode!r}")
    request_body = {
        "model": MODEL,
        "prompt": build_prompt(text),
        "stream": False,
        "options": build_options(temperature),
    }
    if mode == "schema":
        request_body["format"] = JSON_SCHEMA
    return request_body


def call_ollama(text, mode="schema", temperature=0):
    """Yerel sunucudan, parçalara bölünmeden dönen tek bir yanıt ister."""
    response = requests.post(OLLAMA_URL, json=build_request(text, mode, temperature),
                             timeout=(5, 300))
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, dict) or not isinstance(payload.get("response"), str):
        raise ValueError("Ollama response must contain a string 'response' field")
    return payload


def clean_json_output(raw_output):
    """Kod çitlerini ve çevredeki açıklamaları kaldırır.

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
    return cleaned  # Kurtarma imkânsızsa hatayı çağıran kaydeder.


def parse_json_response(raw_output):
    """(Ayrıştırılan değer, ilk deneme başarısı, temizleme sonrası başarı) döndürür."""
    try:
        parsed = json.loads(raw_output)  # Önce hiçbir temizleme yapılmadan.
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
    """Model metnini HTTP sürecinden ve kayıtlı bayraklardan bağımsız değerlendirir.

    Tahmin ve varlıklar yalnızca şema geçerliyse kullanılır; geçersiz çıktı onarılmaz.
    """
    parsed, raw_ok, clean_ok = parse_json_response(raw_output)
    schema_ok = clean_ok and validate_schema(parsed)
    return {
        "raw_json_valid": raw_ok,
        "clean_json_valid": clean_ok,
        "schema_valid": schema_ok,
        "category_correct": bool(schema_ok and parsed["category"] == true_category),
        "predicted_category": parsed["category"] if schema_ok else None,
        "entities": parsed["entities"] if schema_ok else None,
    }


def evaluate_sample(sample, mode="schema", temperature=0):
    """Tek istek yapar; değerlendirme sürebilsin diye API ve biçim hatalarını kaydeder."""
    request_body = build_request(sample["text"], mode, temperature)  # Geçersiz mod burada durur.
    result = {
        "id": sample["id"], "true_category": sample.get("true_category"),
        "mode": mode, "temperature": temperature, "model": MODEL,
        "prompt_version": PROMPT_VERSION, "format_sent": "format" in request_body,
        "options": request_body["options"],
        "prompt_sha256": fingerprint(build_prompt("")),
        "schema_sha256": fingerprint(JSON_SCHEMA),
        "text_sha256": fingerprint(sample["text"]),
        "raw_json_valid": False, "clean_json_valid": False,
        "schema_valid": False, "category_correct": False,
        "predicted_category": None, "entities": None,
        "response_received": False, "api_error": None,
        "raw_output": None, "elapsed_seconds": 0,
    }
    start = time.perf_counter()
    try:
        payload = call_ollama(sample["text"], mode, temperature)
        result.update(response_received=True, raw_output=payload["response"],
                      done_reason=payload.get("done_reason"),
                      eval_count=payload.get("eval_count"),
                      prompt_eval_count=payload.get("prompt_eval_count"))
        result.update(evaluate_response(payload["response"], sample.get("true_category")))
    except (requests.RequestException, ValueError, KeyError) as error:
        result["api_error"] = str(error)
    result["elapsed_seconds"] = round(time.perf_counter() - start, 2)
    return result
