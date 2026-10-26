# Yapılandırılmış Metin Sınıflandırma ve Bilgi Çıkarımı

**Doğal Dil İşleme Projesi I — Teknik Rapor (Türkçe Kopya)**

## 1. Giriş ve amaç

Amaç, yerel bir dil modeli ve Python kullanarak yapılandırılmamış Türkçe haberleri makine tarafından okunabilir JSON biçimine dönüştürmektir. Her yanıtta haberin kategorisi belirlenir; kişi, kurum ve yer adları çıkarılır. Ödev, güvenilir yapılandırılmış çıktıyı, açık hata yönetimini ve en az 100 örnek üzerinde ilk denemede JSON ayrıştırma başarı oranının ölçülmesini gerektirir. Bu projede 200 kayıt değerlendirilir; sözdizimsel güvenilirlik ile sınıflandırma doğruluğu birbirinden ayrılır. Bulut LLM API’si, model eğitimi veya ince ayar kullanılmaz.

## 2. Veri kümesi ve model

Depodaki `data/test_samples.jsonl`, TTC4900 Türkçe haber veri kümesinden alınmış sabit bir seçkidir. Özgün projede kaynak, `savasy/ttc4900` veri kümesinin train bölümü olarak belirtilmiştir. 205 kaydın ilk beşi geliştirme için ayrılmıştır; değerlendirmede tam olarak `samples[5:205]` kullanılır. Özgün kimlikler, metinler, sıralama ve referans kategoriler korunmuştur. Seçimde 42 rastgelelik tohumu, 150–3000 karakter filtresi ve kategori kotaları kullanılmıştır. Değerlendirmede dunya, ekonomi, kultur ve saglik için 29’ar; siyaset, spor ve teknoloji için 28’er kayıt bulunur. 200 farklı kimliğe karşılık 199 benzersiz metin vardır: 2138 ve 2296 kimlikli kayıtların metinleri aynıdır. Metrikler kayıt başına hesaplanır.

Yerel açık kaynaklı Qwen2.5:3b modeli, Ollama tarafından `http://localhost:11434/api/generate` adresinde sunulur. Korunan ortam kaydında Ollama sürümü 0.40.2, model özeti ise `357c53fb659c5076de1d65ccb0b397446227b71a42be9d1603d46168015c9e4b` olarak belirtilmiştir. Bunlar yeni ortam ölçümleri değil, geçmiş çalışmanın üstverileridir. Özgün Türkçe istem, üretim şeması ve ayarlar korunmuştur: temperature=0, seed=42, num_ctx=4096, num_predict=384, repeat_penalty=1.2 ve repeat_last_n=128. Yanıtlar akış halinde alınmaz; bağlantı ve okuma zaman aşımları sırasıyla 5 ve 60 saniyedir. Sabit tohum, farklı yazılım veya model sürümlerinde aynı çıktıyı garanti etmez.

## 3. Yöntem

İşlem akışı şöyledir: haber metni → Türkçe görev istemi → yerel LLM → ham JSON ayrıştırma → gerekirse temizleme → şema doğrulama → referans kategoriyle karşılaştırma. `src/llm_pipeline.py` bu adımları uygular; `src/evaluate.py` kayıtları okur, istek sonuçlarını kaydeder ve metrikleri hesaplar.

Ollama’ya verilen JSON Schema, yedi etiketten birini içeren category alanını ve person, organization, location metin listelerini içeren entities nesnesini zorunlu tutar. Her iki nesne düzeyinde ek alanlar reddedilir. İstem, her listede en fazla beş ad bulunmasını, tekrar olmamasını ve haberde bulunmayan adların üretilmemesini ister. Yapısal doğrulama bu anlamsal talimatları garanti etmez; beş ad sınırı şemada tanımlı değildir.

İlk ayrıştırma işlemi, modelin özgün metni üzerinde `json.loads(raw_output)` çağrısıdır. `try-except` bloğu `json.JSONDecodeError` hatasını yakalar. Ancak bundan sonra temizleyici, baştaki ve sondaki boşlukları ve Markdown kod çitlerini kaldırır veya açıklamaların arasındaki ilk tamamlanmış JSON nesnesini bulur. Ayrıştırma yeniden denenir; kurtarılamayan çıktı başarısız olarak kaydedilir. Kurtarma işlemi alan veya kapanış parantezi eklemez. Özgün davranış gereği, kesilmiş dış yanıtın içindeki tamamlanmış bir nesne bulunabilir; bu nesne yine de tam şema denetiminden geçmelidir. Bağlantı, HTTP ve geçersiz API yanıt gövdesi hataları kaydedilerek değerlendirmeye devam edilir. Doğru sınıflandırma için hem yapının geçerli olması hem de tahminin referans etiketle eşleşmesi gerekir.

Çevrimdışı testler; JSON temizlemeyi, bozuk çıktıları, şema/kategori hatalarını, API hatalarını, metrik paydalarını ve kanıtların korunmasını kapsar. İstek testlerinde taklit nesneler (mock) kullanılır; yeni çıkarım yapılmamıştır. Çevrimdışı metrikler için `python src/evaluate.py --analyze`, testler için `python -m unittest discover -s tests -v` çalıştırılır. Yeni çıkarım için `--run --results NEW.jsonl` gerekir.

---

## 4. Değerlendirme sonuçları

Tablo, `results/optimized_schema_results.jsonl` dosyasındaki önceden kaydedilmiş 200 ham yanıtın çevrimdışı yeniden analizini gösterir. Yeni bir çıkarım deneyi değildir. Kayıtlı başarı bayrakları doğrudan kullanılmaz: ayrıştırma, şema geçerliliği ve kategori doğruluğu yanıt metinleri ile veri kümesi etiketlerinden bağımsız olarak yeniden hesaplanır. Ham yanıt dosyasının adı ve içeriği değiştirilmemiştir.

| Metrik | Başarılı / toplam istek | Yüzde |
|---|---:|---:|
| İlk denemede JSON ayrıştırma | 200 / 200 | %100 |
| Temizleme sonrası JSON ayrıştırma | 200 / 200 | %100 |
| Şema geçerliliği | 200 / 200 | %100 |
| Sınıflandırma doğruluğu | 107 / 200 | %53,5 |

Her oran `başarılı_sayısı / toplam_istek_sayısı × 100` ile hesaplanır. API hataları, geçersiz JSON ve geçersiz şemalar paydada kalır. İlk deneme başarısı, herhangi bir temizleme yapılmadan doğrudan ayrıştırma gerektirir. Temizleme sonrası başarı, doğrudan başarılı yanıtları ve kurtarılan yanıtları kapsar; bu çalışmada hiçbir yanıtın kurtarılması gerekmemiştir. Şema başarısı, anlamsal doğruluğu değil; zorunlu alanları, türleri ve izin verilen değerleri ölçer. Sınıflandırma doğruluğu, şemaya uygun olup referans kategorisiyle eşleşen tahminleri sayar.

![Her biri toplam 200 isteğe göre hesaplanan dört değerlendirme oranı.](figures/json_success_tr.png)

200 isteğin tamamına yanıt alınmış, API hatası oluşmamıştır. Kaydedilen toplam ölçüm süresi 241,83 saniye; yuvarlanmış ortalama süre kayıt başına 1,21 saniyedir. Bu süre yalnızca model hesaplamasını değil, yanıt beklemeyi ve yerel ayrıştırmayı da içerir. Yeniden analiz, kayıtlı süreleri kullanır; yeni bir çalışmanın süresini ölçmez.

## 5. Sınırlılıklar ve sonuç

%100 JSON ve şema başarısı, bu örneklerde yapılandırılmış çıktının güvenilirliğini gösterir; sınıflandırma doğruluğu ise yalnızca %53,5’tir. Geçerli JSON, içeriğin doğru olduğunun kanıtı değildir. Varlık çıkarımı yapılmıştır; ancak anlamsal varlık doğruluğu elle etiketlenmiş referans verilerle ölçülmemiştir. Halüsinasyon tespitine ilişkin bir iddiada bulunulmaz. Tekrarlanan bir metin, değerlendirme çeşitliliğini azaltır. Bulgular tüm Türkçe haberler veya dil modelleri yerine, bu veri kümesi ve model yapılandırması için geçerlidir.

**Kanıtlar:** Veri kümesinin ve yanıtların SHA-256 değerleri `report/evidence.sha256` dosyasında kayıtlıdır. Özgün uygulama ve Git ile izlenen deneyler, `backup/pre-simplification` dalında `f970b0c9bbb622d8e5a6d3ccf5fe4aea90aca7cb` commit’inde korunur. Küçük uygulama, sözdizimi, yapı ve anlamsal doğruluğu ayrı ayrı açıklanabilir tutarak ders gerekliliklerini karşılar.
