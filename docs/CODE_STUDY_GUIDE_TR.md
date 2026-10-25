# Kod çalışma rehberi — Türkçe

Çalışma tamamlandı: `data/test_samples.jsonl` 205 kayıt içerir. `samples[:5]` geliştirme, `samples[5:205]` değerlendirmedir. A/B/C aynı 200 kimlik için 200'er yanıt içerir. 2138 ve 2296 aynı metin olduğundan değerlendirmede 199 farklı metin vardır; üyelik ve sıra çıkarımdan sonra değiştirilmedi.

## Akış

Dosya numaraları çalışmanın sırasını gösterir. Sunumda her adımın girdisini, yaptığı işi ve çıktısını şu sırayla anlatın:

| Adım | `src/` içindeki dosya | Sunumda açıklanacak görev |
|---|---|---|
| 1 | `step1_prepare_dataset.py` | Kaynaktan sabit 205 kaydı hazırlar ve manifest karmasını doğrular; ilk beş geliştirme, sonraki 200 değerlendirmedir. |
| 2 | `step2_test_model.py` | Bir geliştirme haberiyle bağlantıyı dener; gerçek Ollama çağrısı yapar ve ana deneylere dahil değildir. |
| 3 | `step3_run_experiments.py` | Checkpoint kontrolünden sonra A → B → C sırasını yönetir; 600 kayıt tam ise yalnız doğrular ve çıkarım yapmadan çıkar. |
| 3a | `step3a_evaluate_prompt.py` | A: uzun istem, üretim sırasında şema zorlaması yok. |
| 3b | `step3b_evaluate_json.py` | B: A ile aynı istem, üretim sırasında JSON Schema. |
| 3c | `step3c_evaluate_optimized.py` | C: kısa istem ve tekrar ayarları, B ile aynı şema. |
| 4 | `step4_analyze_results.py` | Kaydedilmiş ham yanıtlardan metrikleri ve karışıklık matrislerini hesaplar. |
| 5 | `step5_generate_figures.py` | Analizi yeniler; altı şekli PNG ve SVG olarak üretir. |
| 6 | `step6_build_report.py` | Analiz/şekilleri yeniler ve akademik PDF'yi oluşturur. |
| 7 | `step7_verify_project.py` | Veri, yanıt, metrik, kaynak karması, matris, şekil ve PDF kontrollerini ağsız yapar. |
| 8 | `step8_package_submission.py` | Doğrulama yapar; güncel dosyaları teslim ZIP'ine koyup arşiv baytlarını karşılaştırır. |
| Geliştirme | `dev_evaluate_baseline.py` | Beş geliştirme kaydının ayrı başlangıç deneyidir. |

Tamamlanmış projeyi sunarken 3 ve 7 yeterlidir; 2 ve geliştirme baseline adımı yeniden çıkarım yapacağı için bu doğrulama akışında kullanılmaz. 4–6 kayıtlı sonuçlardan yeniden üretim içindir; 8 teslim paketini hazırlar. Ana komut: `python src/step3_run_experiments.py`.

Üç değerlendirme betiğinin kaynak baytları ve SHA-256 değerleri korundu. Bu nedenle giriş açıklamalarındaki eski `src/run_evaluation.py` adı tarihsel olarak durur; güncel komut yukarıdadır. Önceki göç envanteri ve manifest değiştirilmedi; 7. adım güncel modül adını tarihsel kimliğe eşler. Mevcut PDF'nin eski komut adları da korunmuştur; güncel adlar bu tablodadır.

Haber → istem → Ollama HTTP POST → response metni → ham JSON → gerekirse temizleme → şema → kategori eşitliği → JSONL checkpoint → metrikler → şekiller/PDF.

Model eğitilmez; hazır qwen2.5:3b ağırlıklarıyla çıkarım yapılır. `true_category` referans etikettir. Varlıklar için insan etiketli altın referans bulunmadığından anlamsal NER başarısı ölçülmez. Dış `response.json()` sunucu zarfını, iç `json.loads(raw)` model metnini açar. JSONL'de her satır ayrı bir kayıttır.

## Veri hazırlama: src/step1_prepare_dataset.py

Kaynak TTC4900 `train` bölümüdür. `--source-arrow` yerel önbelleği okuyabilir. Seed 42 ile kaynak indeksleri karıştırılır, 150–3000 karakter filtresi ve ilk seçimde sınıf başına 20 kota uygulanır. İlk seçimin sırası yeniden üretilir; ilk beş geliştirme kaydı korunur. Ardından mevcut 200 değerlendirme dağılımını sağlayan ekler aynı algoritmayla seçilir. Eklerde tekrarlı ID/metin atlanır; önceden bulunan 2138/2296 metin tekrarı korunur. Bu geçmiş seçim adımları yeniden üretim içindir; etkin veri her zaman 205 kayıttır.

Kanonik manifestteki SHA-256, üyelik ve sırayı sabitler. Hazırlama betiği aynı veriyi doğrular; farklı mevcut dosyanın üzerine yazmaz. Tamamlanmış çıkarımdan sonra yeniden örneklem yapılmaz. Dağılım: dunya/ekonomi/kultur/saglik 29'ar; siyaset/spor/teknoloji 28'er.

## Geliştirme araçları

`src/step2_test_model.py` ilk geliştirme haberini tek istekle sınar ve terminale yazar. `src/dev_evaluate_baseline.py` varsayılan beş geliştirme örneğini `results/baseline_results.jsonl` içine kaydeder. Bunlar ana A/B/C sonuçlarına katılmaz. `step2_test_model.py` ana kontrollü parametre setinin tamamını kullanmaz; eşdeğer deney sayılmaz.

## Ana deneyler ve ortak fonksiyonlar

`src/step3a_evaluate_prompt.py`: A, geliştirilmiş uzun istem. `src/step3b_evaluate_json.py`: B, aynı istem ve JSON Schema. `src/step3c_evaluate_optimized.py`: C, kısa istem, aynı şema, repeat_penalty=1.2 ve repeat_last_n=128. Hepsinde temperature=0, seed=42, num_ctx=4096, num_predict=384; stream=False ve timeout=(5,60). top_k/top_p açıkça ayarlı değildir.

Varsayılan `--limit 200`, `samples[5:5 + args.limit]` üzerinden tam değerlendirmeyi seçer. Kanonik yollar sırasıyla `results/improved_prompt_results.jsonl`, `results/schema_results.jsonl`, `results/optimized_schema_results.jsonl` olur. Her ID yazıldıktan sonra tekrar başlatmada atlanır; hata kaydı da atlanır. İstem, şema, seçenekler ve hata işleme taşınırken değiştirilmedi.

### build_prompt(text)

Parametre haber metnidir; dönüş görev/kategori/varlık kurallarını içeren metindir. A ve B aynı uzun istemi kullanır; C'nin ayrı kısa istemi vardır. İstem sözcükleri modelin seçimini etkileyebilir; bu görevde hiç değiştirilmedi.

### clean_and_parse(raw)

Ham yanıt metni alır, `(True, obj)` veya `(False, None)` döndürür. Markdown çiti, kodu görsel olarak çevreleyen üç ters tırnaktır. LLM bu çiti/açıklamayı ekleyebilir; katı JSON okuyucu tüm metni JSON sanarak hata verir. Temizleme eksik JSON'u yeniden yazmaz; sadece mevcut kurallarla bir nesne bulmayı dener.

```python
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
```

`raw_decode`, başladığı konumdan bir JSON değeri ve bitiş indeksini verir. Burada `_` ile bitiş indeksi kullanılmaz; devamındaki açıklama veya ikinci nesne yok sayılabilir. İlk bulunan nesnenin şemaya uygun olması garanti değildir. Birinci nesne yalnız category, ikincisi yalnız entities içeriyorsa birleştirilmez. Bu sınırlama korunmuştur.

### validate_schema(obj)

Herhangi bir Python değeri alır, bool döndürür. `dict` olmalı; tam olarak category ve entities anahtarları bulunmalı; kategori metin olmalı ve yedi sınıftan biri olmalı; entities tam olarak person/organization/location metin listelerini içermeli. `all(...)` her liste ve elemanda koşulu sınar; boş listeler geçerlidir. Başarısız kontrol hemen False döndürür. Ne isimlerin haberde geçtiği ne de varlık türlerinin doğru olduğu denetlenir.

### evaluate_sample(sample)

`id/text/true_category` sözlüğü alır; ölçüm kaydı döndürür. Önce bütün başarı alanları False yapılır. Kronometre başlar. Ollama'ya HTTP POST gönderilir; dış yanıt alınır; ham JSON denenir. Başarısızsa temizleyici çağrılır. Ayrıştırma başarılıysa şema kontrol edilir. **Yalnız şema uygunsa** kategori gerçek etiketle karşılaştırılır. Hata olursa `api_error` kaydedilir. Süre iki ondalığa yuvarlanır. Bu fonksiyon dosyaya yazmaz; `main` yazar.

```python
response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": MODEL,
                "prompt": build_prompt(sample["text"]),
                # Yanıt parçalar halinde değil tek HTTP JSON gövdesinde beklendiği için False kullanılır.
                "stream": False,
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
```

`temperature=0` rastgeleliği azaltır, `seed=42` model örnekleyicisi içindir; Python veri seçimi tohumu ayrı bir mekanizmadır. `num_ctx=4096` bağlam, `num_predict=384` üretim token sınırıdır. `timeout=(5,60)` bağlantı için 5, okuma sırasında veri bekleme için 60 saniyedir; kesin toplam işlem süresi değildir. Süre `perf_counter` ile istemci tarafında ölçülür: ağ/yerel sunucu beklemesi, model çalışması ve ayrıştırma dahildir.

Dış except, `requests.RequestException`, `ValueError`, `KeyError` yakalar. Hatalı HTTP JSON zarfı veya eksik response alanı da bu kayda girebilir. Dolayısıyla api_error yalnız sunucunun HTTP hata kodu demek değildir. Modelin normal metninin JSON olmaması iç except tarafından ayrıştırma hatası olarak ele alınır.

### percentage(a,b) ve main()

`percentage` pay/payda yüzdesini iki ondalığa yuvarlar; b=0 ise kaydedilmiş yardımcı 0 döndürür. `main`, argümanı okur, ilk beşi atlar, kaydedilmiş checkpoint dosyasını yükler, tamamlanan ID'leri atlar, her yeni sonucu dosyaya append eder. Hata kaydı olan ID de tamamlanmış kabul edilir; otomatik yeniden deneme yoktur. Dosyayı her haber sonrası kapatmak kesintide kaybı azaltır, ancak güç kesintisine karşı işlem günlüğü/atomik kayıt garantisi değildir.

Konsolun `Category accuracy` paydası yanıt alınan sayıdır. Kanonik rapordaki uçtan uca doğruluğun paydası tüm 200 istektir; bu koşuda herkes yanıt aldığı için sayısal fark yoktur. API hataları oluşursa bu ayrım önemlidir. Yeni nihai analiz, tüm 200 kayıt üzerinden oranları ve ayrıca koşullu doğruluğu açıkça ayırır.


## Başlatıcı: src/step3_run_experiments.py

Önce kanonik veri ve kayıtlar doğrulanır. Üç deney tamamlanmışsa Ollama'ya bağlanmadan çıkar; tekrar çıkarım yoktur. Eksik koşuda `/api/version`, `/api/tags`, `/api/show` ile ortam denetlenir. Veri/kod karmaları ve model/runtime kimliği `results/run_identity.json` ile karşılaştırılır. Uyuşmazlık sessizce geçilmez. Üç betik sırayla `--limit 200` ile çağrılır. Aynı dizinde tek başlatıcı çalıştırın.

## Analiz: src/step4_analyze_results.py

`load_jsonl` bozuk satırı gizlemez. `recompute` ilgili deneyin kendi ayrıştırma ve şema işlevleriyle her ham yanıtı yeniden değerlendirir; kaydedilen dört bayrakla eşleşmesini zorunlu tutar. `analyze_experiment` duplicate/yabancı ID'yi reddeder. Eksik koşuda final_metrics null ve matris None olur. Tam koşuda bütün ana oranlar 200 üzerinden, koşullu doğruluk şema geçerli sayısı üzerinden hesaplanır.

`collect_summary` veri hash'i, geliştirme ID'leri, değerlendirme ID sırası, metin tekrarları ve tüm deneyleri dosya yazmadan kontrol eder. `main` kanonik `results/metrics_summary.json`, A/B matrisleri ve `results/v3_confusion_matrix.csv` dosyalarını yazar. INVALID sütunu API/biçim/şema hatalarını tutar; her matris toplamı 200'dür. C varlık listeleri için tekrar ve beş elemanı aşma sayılır; bunlar anlamsal doğruluk değildir.

## Şekiller ve akademik rapor

`src/step5_generate_figures.py` aynı doğrulanmış metriklerden altı şekli PNG/SVG üretir: JSON/şema, sınıflandırma, süre, C matrisi, C kategori doğruluğu, B hata dağılımı. Grafik etiketleri gerçek sayımlardan gelir. `src/step6_build_report.py` metrikleri ve şekilleri yeniler, gömülü DejaVu yazı tipiyle `report.pdf` oluşturur. Beş geliştirme ile 200 değerlendirme raporda ayrı belirtilir.

## Gerçek haber yürüyüşü: ID 4000

İlk değerlendirme kaydının referansı spor. A yanıtı Markdown çiti ve açıklama içerdiğinden raw=False; mevcut temizleme nesneyi bulur, schema=True ve category_correct=True olur. C'nin güncel yanıtı aşağıdadır; tekrar modele üretilmemiştir:

```json
{
  "category": "spor",
  "entities": {
    "person": ["Dario Saric", "Anadolu Efes"],
    "organization": [],
    "location": []
  }
}
```

Anadolu Efes bir kurum olmasına rağmen person listesinde bulunur. Bu semantik tür hatası, metin listesi olma koşulunu bozmaz; şema başarısı NER doğruluğu değildir.

## Güncel sonuçlar

| Metric | A: Prompt only | B: JSON Schema | C: Optimized schema |
|---|---:|---:|---:|
| Raw JSON | 0/200 (0.00%) | 158/200 (79.00%) | 200/200 (100.00%) |
| Clean JSON | 166/200 (83.00%) | 158/200 (79.00%) | 200/200 (100.00%) |
| Schema valid | 162/200 (81.00%) | 158/200 (79.00%) | 200/200 (100.00%) |
| Correct category | 80/200 (40.00%) | 87/200 (43.50%) | 107/200 (53.50%) |
| Conditional accuracy | 80/162 (49.38%) | 87/158 (55.06%) | 107/200 (53.50%) |
| Total time (s) | 689.88 | 505.97 | 241.83 |
| Mean time (s) | 3.45 | 2.53 | 1.21 |

## Doğrulama ve tekrar üretim

```bash
venv/bin/python src/step3_run_experiments.py
venv/bin/python src/step6_build_report.py
venv/bin/python src/step7_verify_project.py
venv/bin/python -m unittest discover -s tests -v
```

`tests/test_evaluation.py` yapay kayıtlarla API/JSON/şema hatalarının paydada kalmasını, eksik koşu davranışını ve ID/bayrak kontrollerini sınar. Devam etme testleri geçici dosyalarda çalışır; gerçek sonuçlara yazmaz ve ağ kullanmaz. `docs/verification.json` ve `docs/migration_manifest.json`, ham yanıt doğrulaması ve kaynak korunum kanıtıdır. Önceki proje etkin dizinin dışındaki yedektedir.
