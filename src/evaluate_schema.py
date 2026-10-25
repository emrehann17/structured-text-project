"""200 değerlendirme kaydı; ilk beş geliştirme kaydı dışarıda tutulur.

Tercih edilen başlatıcı: python src/run_evaluation.py.
"""

import argparse
import json
import re
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "data/test_samples.jsonl"
RESULT_PATH = ROOT / "results/schema_results.jsonl"

MODEL = "qwen2.5:3b"

CATEGORIES = {
    "siyaset", "dunya", "ekonomi", "kultur",
    "saglik", "spor", "teknoloji"
}

ENTITY_TYPES = {"person", "organization", "location"}


# JSON Schema: sözdiziminden öte alan adlarını, türlerini ve izin verilen değerleri tarif eder.
JSON_SCHEMA = {
    "type": "object",
    # properties her alanın kuralını tanımlar; tek başına o alanı zorunlu yapmaz.
    "properties": {
        "category": {
            "type": "string",
            # enum kategori değerini yedi seçenekle sınırlar; doğru seçeneği garanti etmez.
            "enum": sorted(CATEGORIES)
        },
        "entities": {
            "type": "object",
            # properties her alanın kuralını tanımlar; tek başına o alanı zorunlu yapmaz.
            "properties": {
                "person": {
                    "type": "array",
                    "items": {"type": "string"}
                },
                "organization": {
                    "type": "array",
                    "items": {"type": "string"}
                },
                "location": {
                    "type": "array",
                    "items": {"type": "string"}
                }
            },
            # required listesinde bulunan alanlar çıktıda mutlaka yer almalıdır.
            "required": [
                "person",
                "organization",
                "location"
            ],
            # Bu nesne düzeyinde listelenmeyen ek anahtarları yasaklar; liste uzunluğunu sınırlandırmaz.
            "additionalProperties": False
        }
    },
    # required listesinde bulunan alanlar çıktıda mutlaka yer almalıdır.
    "required": ["category", "entities"],
    # Bu nesne düzeyinde listelenmeyen ek anahtarları yasaklar; liste uzunluğunu sınırlandırmaz.
    "additionalProperties": False
}


def build_prompt(text):
    """Haber metnini modele verilecek talimata (prompt/istem) yerleştirir.

    Parametreler: text: tek haberin özgün metni.
    Dönüş: Haber ve görevleri birlikte içeren str.

    Kategori tanımları seçim sınırlarını, varlık türleri kişi/kurum/yer ayrımını
    anlatır. f-string içindeki text haberi ekler; çift süslü parantezler JSON
    örneğinin gerçek parantezleridir. İstem sözcükleri çıktıyı etkileyebilir;
    karşılaştırma için değiştirilmemiştir. Burada API çağrısı veya doğrulama yoktur.
    """
    return f"""
Sen Türkçe haber sınıflandırma ve bilgi çıkarma
görevinde çalışan bir NLP sistemisin.

GÖREV 1: HABER SINIFLANDIRMA

Haberi YALNIZCA bir kategoriye ata:

- siyaset: Hükümetler, politikacılar, siyasi
  kararlar, diplomasi ve siyasi gelişmeler.
- dunya: Uluslararası genel olaylar ve
  dünyanın farklı bölgelerindeki gelişmeler.
- ekonomi: Finans, piyasalar, ticaret,
  enflasyon, yatırımlar ve ekonomik gelişmeler.
- kultur: Sanat, müzik, sinema, edebiyat
  ve kültürel etkinlikler.
- saglik: Tıp, hastalıklar, tedaviler
  ve sağlık araştırmaları.
- spor: Spor müsabakaları, motor sporları,
  takımlar, sporcular ve turnuvalar.
- teknoloji: Yazılım, internet, dijital
  platformlar, teknoloji ürünleri ve bilişim.

Haberi tek bir kelimeye göre değil,
ANA KONUSUNA göre sınıflandır.

GÖREV 2: ENTITY EXTRACTION

- person: Yalnızca gerçek kişi isimleri.
- organization: Şirket, kurum ve kuruluşlar.
- location: Şehir, ülke ve coğrafi konumlar.

KURALLAR:
1. Sadece metinde geçen varlıkları çıkar.
2. İsimleri metindeki yazımlarıyla koru.
3. Aynı varlığı aynı listede tekrarlama.
4. Bir ülke ismini person olarak yazma.
5. Belirsiz varlıkları ekleme.
6. Bulunmayan varlıklar için [] kullan.
7. Açıklama veya Markdown ekleme.
8. SADECE geçerli JSON üret.

JSON FORMATI:
{{
  "category": "teknoloji",
  "entities": {{
    "person": [],
    "organization": [],
    "location": []
  }}
}}

HABER:
{text}
"""


def clean_and_parse(raw):
    """Ham model yanıtından mevcut kurallarla JSON nesnesi çıkarmayı dener.

    Parametreler: raw: modelin döndürdüğü metin.
    Dönüş: (başarı: bool, ayrıştırılan nesne); başarısızsa (False, None).

    Önce boşluklar ve Markdown çitleri (```json ... ```) kaldırılır.
    json.loads metni Python nesnesine çevirir; bozuk sözdizimi
    JSONDecodeError üretir. İlk deneme olmazsa her { konumunda raw_decode
    denenir: ilk tamamlanmış nesneyi ve bitiş konumunu verir. Bitiş konumu
    burada kullanılmaz; sonraki ikinci nesne birleştirilmez. Bu yöntem
    eksik kapanışları tamamlamaz ve içerik doğruluğunu düzeltmez.
    """
    cleaned = raw.strip()

    # Markdown kod bloklarını kaldır.
    cleaned = re.sub(
        r"^```(?:json)?\s*",
        "",
        cleaned,
        flags=re.IGNORECASE
    )
    cleaned = re.sub(r"\s*```$", "", cleaned)

    try:
        return True, json.loads(cleaned)
    # Geçersiz tırnak, eksik kapanış veya açıklama metni JSON ayrıştırmasını bozabilir.
    except json.JSONDecodeError:
        pass

    # "İşte JSON:" gibi ön metinleri atla.
    decoder = json.JSONDecoder()

    # İlk çözülebilen { başlangıcını arar; birden fazla JSON nesnesini birleştirmez.
    for i, char in enumerate(cleaned):
        if char == "{":
            try:
                # raw_decode nesne ve bittiği indeksi döndürür; sondaki metin burada yok sayılır.
                obj, _ = decoder.raw_decode(cleaned[i:])
                return True, obj
            # Geçersiz tırnak, eksik kapanış veya açıklama metni JSON ayrıştırmasını bozabilir.
            except json.JSONDecodeError:
                continue

    return False, None


def validate_schema(obj):
    # Geçerli JSON bir sayı/liste de olabilir; uygulama ise haber sözlüğü bekler.
    """Ayrıştırılmış nesnenin projenin beklediği yapıda olup olmadığını denetler.

    Parametreler: obj: json.loads veya temizleyicinin ürettiği herhangi bir Python değeri.
    Dönüş: Bütün kontroller sağlanırsa True, ilk uyumsuzlukta False.

    Sırayla sözlük, tam anahtar kümesi, geçerli kategori, entities sözlüğü
    ve üç metin listesi kontrol edilir. JSON olarak 42 de geçerlidir ama
    bu projede beklenen haber nesnesi değildir. Yalnızca yapı sınanır;
    yanlış haber kategorisi veya metinde olmayan isim bu denetimi geçebilir.
    """
    if not isinstance(obj, dict):
        return False

    # Eksik veya fazla alanı reddeder; yalnız JSON sözdiziminin doğru olması yetmez.
    if set(obj.keys()) != {"category", "entities"}:
        return False

    if not isinstance(obj["category"], str):
        return False

    if obj["category"] not in CATEGORIES:
        return False

    entities = obj["entities"]

    if not isinstance(entities, dict):
        return False

    if set(entities.keys()) != ENTITY_TYPES:
        return False

    return all(
        isinstance(entities[key], list)
        and all(isinstance(x, str) for x in entities[key])
        for key in ENTITY_TYPES
    )


def evaluate_sample(sample):
    """Tek haber için bir Ollama isteği yapar ve ölçüm kaydı döndürür.

    Parametreler: sample: id, text ve true_category alanları olan haber sözlüğü.
    Dönüş: Ham yanıt, başarı bayrakları, hata ve geçen saniyeyi içeren dict.

    Başlangıçta bütün başarılar False olur. HTTP POST ile istem gönderilir;
    sunucu yanıtının response alanı alınır. Önce ham JSON, gerekirse temiz
    JSON denenir; sonra yapı, en son kategori kontrol edilir. try-except
    bağlantı/HTTP hatalarını, ValueError ve eksik alan KeyError durumlarını
    kayda geçirir; beklenmeyen her hatayı yakalama iddiası yoktur.
    Süre API beklemesini ve yerel ayrıştırmayı kapsar; saf GPU süresi değildir.
    Bu fonksiyon diske yazmaz; kalıcı kaydı main yapar.
    """
    result = {
        "id": sample["id"],
        "true_category": sample["true_category"],
        "raw_json_valid": False,
        "clean_json_valid": False,
        "schema_valid": False,
        "category_correct": False,
        "response_received": False,
        "api_error": None,
        "raw_output": None,
        "elapsed_seconds": 0
    }

    start = time.perf_counter()

    try:
        # HTTP isteği istemci ile sunucu arasında veri gönderimidir; /api/generate modeli verilen istemle çalıştırır.
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": MODEL,
                "prompt": build_prompt(sample["text"]),
                # Yanıt parçalar halinde değil tek HTTP JSON gövdesinde beklendiği için False kullanılır.
                "stream": False,
                # Şema Ollama üretimine gönderilir; aşağıdaki Python doğrulaması ayrıca yapılır.
                "format": JSON_SCHEMA,
                "options": {
                    # Düşük rastgelelik: en olası token seçimi hedeflenir; farklı sürüm/donanımda birebir sonuç garantisi değildir.
                    "temperature": 0,
                    # Model örnekleyicisinin tohumu; veri kümesini karıştıran Python tohumundan ayrı bir ayardır.
                    "seed": 42,
                    # İstem ve üretim için bağlam penceresi token cinsinden sınırlandırılır.
                    "num_ctx": 4096,
                    # Çıktı en fazla bu kadar token üretebilir; sınırda kesilen JSON tamamlanmamış olabilir.
                    "num_predict": 384
                }
            },
            # Bağlantı için 5, okumada veri bekleme için 60 saniye; toplam isteğin kesin üst sınırı değildir.
            timeout=(5, 60)
        )

        # HTTP 4xx/5xx gibi başarısız durumları yakalanabilir istisnaya çevirir.
        response.raise_for_status()
        payload = response.json()
        # Sunucu zarfından model metnini alır; alan yoksa KeyError yakalanır.
        raw = payload["response"]

        result["done_reason"] = payload.get("done_reason")
        result["eval_count"] = payload.get("eval_count")

        result["response_received"] = True
        result["raw_output"] = raw

        # 1. İlk denemede ham JSON parsing
        try:
            # JSON, metin tabanlı veri biçimidir; loads bu metni Python sözlük/liste/değerlerine çevirir.
            parsed = json.loads(raw)
            result["raw_json_valid"] = True
            result["clean_json_valid"] = True

        # Geçersiz tırnak, eksik kapanış veya açıklama metni JSON ayrıştırmasını bozabilir.
        except json.JSONDecodeError:
            # 2. Temizleme sonrası parsing
            success, parsed = clean_and_parse(raw)
            result["clean_json_valid"] = success

        if result["clean_json_valid"]:
            result["schema_valid"] = validate_schema(parsed)

            # Şema geçersizse kategori doğru görünse bile uçtan uca başarılı sayılmaz.
            if result["schema_valid"]:
                result["category_correct"] = (
                    parsed["category"] == sample["true_category"]
                )

    # Hata kaydı sonraki haberlerin işlenebilmesini sağlar; hatayı başarıya dönüştürmez.
    except (requests.RequestException, ValueError, KeyError) as e:
        result["api_error"] = str(e)

    result["elapsed_seconds"] = round(
        time.perf_counter() - start, 2
    )

    return result


def percentage(a, b):
    """Pay ve paydayı okunabilir yüzdeye dönüştürür.

    Parametreler: a: başarılı sayı; b: kullanılan toplam sayı.
    Dönüş: İki ondalığa yuvarlanmış yüzde; payda sıfırsa 0.0.

    Paydanın yanıt sayısı mı tüm istekler mi olduğu çağrı yerinde belirlenir.
    Sıfır dönüşü bölme hatasını önler; hiç ölçüm yokken gerçek başarı oranı
    varmış gibi yorumlanmamalıdır.
    """
    return round(100 * a / b, 2) if b else 0.0



def main():
    """Komut satırı seçimi, kayıt yükleme, çıkarım ve özet akışını yönetir.

    Parametreler: Parametre yok; --limit komut satırından okunur.
    Dönüş: None; JSONL dosyasına sonuç ekler ve terminale özet yazar.

    Veriyi okur, ilgili dilimi seçer, önceki ID kayıtlarını yükler.
    Yeni haberleri evaluate_sample ile işler; her birini hemen kaydeder.
    Sonunda yanıt sayısı ve başarıları toplar. Dosya erişim/bozuk JSONL
    hataları burada otomatik onarılmaz. Ayrı sonuç yolu deneyleri karıştırmaz.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=200)
    args = parser.parse_args()

    if args.limit < 1:
        parser.error("--limit en az 1 olmalı")

    # Dataset yükle
    with open(DATA_PATH, encoding="utf-8") as f:
        samples = [
            json.loads(line)
            for line in f
            if line.strip()
        ]

    # İlk 5 örnek geliştirme için ayrıldı
    # Geliştirmede görülen ilk 5 haber, ana deney puanını yapay olarak yükseltmemek için dışarıda kalır.
    selected = samples[5:5 + args.limit]

    print("Dataset toplam örnek:", len(samples))
    print("Seçilen örnek:", len(selected))

    if not selected:
        raise ValueError("Hiç örnek seçilemedi!")

    RESULT_PATH.parent.mkdir(parents=True, exist_ok=True)

    # Önceden kaydedilen sonuçları yükle
    results = {}

    if RESULT_PATH.exists():
        with open(RESULT_PATH, encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    item = json.loads(line)
                    results[item["id"]] = item

    # Değerlendirme döngüsü
    for index, sample in enumerate(selected, 1):

        # Checkpoint: diskte kimliği bulunan haber tekrar gönderilmez; eski hata kayıtları da atlanır.
        if sample["id"] in results:
            print(f"[{index}/{len(selected)}] Already done")
            continue

        result = evaluate_sample(sample)
        results[sample["id"]] = result

        # Append her ölçümü sonuna ekler. Blok kapanınca dosya kapanır; kesintide yalnız son satır yarım kalabilir.
        with open(RESULT_PATH, "a", encoding="utf-8") as f:
            f.write(
                json.dumps(result, ensure_ascii=False)
                + "\n"
            )

        print(
            f"[{index}/{len(selected)}] "
            f"JSON={result['raw_json_valid']} "
            f"Schema={result['schema_valid']} "
            f"Category={result['category_correct']} "
            f"Time={result['elapsed_seconds']}s",
            flush=True
        )

    # İlgili deney sonuçlarını seç
    evaluated = [
        results[s["id"]]
        for s in selected
        if s["id"] in results
    ]

    received = [
        r for r in evaluated
        if r["response_received"]
    ]

    # Buradaki payda yalnız yanıt alınan isteklerdir; tüm istek paydası attempted ile ayrıca gösterilir.
    n = len(received)
    attempted = len(evaluated)

    raw_ok = sum(r["raw_json_valid"] for r in received)
    clean_ok = sum(r["clean_json_valid"] for r in received)
    schema_ok = sum(r["schema_valid"] for r in received)
    # Kategori eşitliği şema kontrolünden sonra sayılmıştır; biçim hataları doğru sayılmaz.
    correct = sum(r["category_correct"] for r in received)

    print("\n========== EVALUATION RESULTS ==========")
    print(f"Requested samples: {len(selected)}")
    print(f"Model responses: {n}")
    print(f"API errors: {attempted - n}")
    print(f"Raw JSON success: {percentage(raw_ok, n)}%")
    print(f"Clean JSON success: {percentage(clean_ok, n)}%")
    print(f"Schema success: {percentage(schema_ok, n)}%")
    print(f"Category accuracy: {percentage(correct, n)}%")
    print(
        "First-try success / all requests:",
        f"{raw_ok}/{attempted}",
        f"({percentage(raw_ok, attempted)}%)"
    )
    print(
        "Total inference time:",
        round(
            sum(r["elapsed_seconds"] for r in evaluated),
            2
        ),
        "seconds"
    )

    if n < 100:
        print("\nNOTE: At least 100 model responses")
        print("are required for final evaluation.")

if __name__ == "__main__":
    main()