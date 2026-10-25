"""İlk geliştirme haberiyle Ollama bağlantısını ve tek yanıtın JSON biçimini dener.
Ollama, modeli yerel bilgisayarda çalıştıran sunucudur; requests istemcidir.
Bu kısa deneme ana A/B/C deneylerinden farklı ayarlara sahiptir ve sonuç dosyası yazmaz.
"""

import json
import requests

with open(
    "data/test_samples.jsonl",
    encoding="utf-8"
) as f:
    sample = json.loads(f.readline())

# İstem, görev ve beklenen biçimi anlatan metindir; haber f-string ile sona eklenir.
prompt = f"""
Sen bir Türkçe haber analiz sistemisin.

Haberi şu kategorilerden birine ata:
siyaset, dunya, ekonomi, kultur,
saglik, spor, teknoloji.

Metindeki kişi, kurum ve yer isimlerini çıkar.
Yalnızca metinde açıkça geçen isimleri kullan.

Yanıt SADECE geçerli JSON olmalıdır.

Örnek format:
{{
  "category": "teknoloji",
  "entities": {{
    "person": [],
    "organization": [],
    "location": []
  }}
}}

Haber:
{sample["text"]}
"""

try:
    # HTTP isteği istemci ile sunucu arasında veri gönderimidir; /api/generate modeli verilen istemle çalıştırır.
    response = requests.post(
        "http://localhost:11434/api/generate",
        json={
            "model": "qwen2.5:3b",
            "prompt": prompt,
            # Yanıt parçalar halinde değil tek HTTP JSON gövdesinde beklendiği için False kullanılır.
            "stream": False,
            "options": {
                # Düşük rastgelelik: en olası token seçimi hedeflenir; farklı sürüm/donanımda birebir sonuç garantisi değildir.
                "temperature": 0,
                # İstem ve üretim için bağlam penceresi token cinsinden sınırlandırılır.
                "num_ctx": 4096
            }
        },
        timeout=180
    )
    # HTTP 4xx/5xx gibi başarısız durumları yakalanabilir istisnaya çevirir.
    response.raise_for_status()

    # Dış JSON sunucunun zarfıdır; içteki response ise modelin henüz ayrıştırılmamış metnidir.
    raw = response.json()["response"]

    print("Gerçek kategori:", sample["true_category"])
    print("Model çıktısı:", raw)

    try:
        # JSON, metin tabanlı veri biçimidir; loads bu metni Python sözlük/liste/değerlerine çevirir.
        parsed = json.loads(raw)
        print("JSON parsing: SUCCESS")
        print("Tahmin:", parsed.get("category"))

    # Geçersiz tırnak, eksik kapanış veya açıklama metni JSON ayrıştırmasını bozabilir.
    except json.JSONDecodeError as e:
        print("JSON parsing: FAILED", e)

except requests.RequestException as e:
    print("Ollama bağlantı hatası:", e)
