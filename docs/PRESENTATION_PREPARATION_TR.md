# Sunuma hazırlık — Türkçe

Tamamlanmış 200 örneklik çalışmanın 10 slaytlık planı (10–12 dakika anlatım; kod gösterimi ve sorularla 15–20 dakika). Beş geliştirme örneği ana sonuçlara dahil değildir.

## 1. Amaç

Slayt: Türkçe haberden kategori ve kişi/kurum/yer listeleri çıkarılır. Model eğitimi yok; yerel qwen2.5:3b kullanılır.

Konuşma: “Yapılandırılmış çıktı başka programların kullanabileceği veri üretmeyi hedefler.”

## 2. Üç başarı kavramı

Slayt: Geçerli JSON, şema uyumu ve doğru bilgi farklıdır.

Konuşma: “{"category":"spor"} geçerli JSON olabilir ama entities eksik olduğundan uygulama şemasını geçmez.”

## 3. Veri ve sınır

Slayt: 205 kayıt = 5 geliştirme + 200 değerlendirme. Dilim samples[5:205]. 2138/2296 aynı metin: 200 ID, 199 metin.

Konuşma: “Çıkarımdan sonra üyeliği değiştirmedim; metin bağımsızlığı sınırlamasını açıkça belirtiyorum.”

## 4. Mimari

Slayt: İstem → Ollama → response → JSON/şema kontrolü → referans etiket → JSONL → analiz.

Konuşma: “Sunucu JSON zarfı ve modelin response metni iki ayrı ayrıştırma katmanıdır.”

## 5. Deneyler

Slayt: A uzun istem; B aynı istem + şema; C kısa istem + aynı şema + tekrar kontrolü.

Konuşma: “Cde birden fazla değişiklik birlikte olduğu için yalnız repeat_penalty etkisi diye sunamam.”

## 6. Sabit ayarlar

Slayt: temperature=0, seed=42, num_ctx=4096, num_predict=384; C: repeat_penalty=1.2, repeat_last_n=128.

Konuşma: “top_k/top_p açıkça ayarlanmadı; bunlar için ayrı deney yapmadım. Kayıtlı runtime Ollama 0.40.2; GPU kullanımını bu göçte ölçmedim.”

## 7. Paydalar

Slayt: Ana oranlar 200 üzerinden; koşullu doğruluk A=162, B=158, C=200 şema-geçerli yanıt üzerinden.

Konuşma: “API veya biçim hatalarını değerlendirmeden düşürmem; INVALID matris sütununda tutarım.”

## 8. Gerçek sonuçlar

Slayt: A/B/C ham JSON: %0/%79/%100; kategori: %40/%43,50/%53,50. Süre: 689,88/505,97/241,83 saniye.

Konuşma: “Her deney aynı 200 ID için tamamlandı, 200 yanıt alındı ve API hatası yok. Bu sayılar saklanmış yanıtlardan yeniden hesaplandı.”

## 9. Hata analizi ve sınırlar

Slayt: Cde 107 doğru, 93 yanlış kategori; dunya 0/29. ID 4000de Anadolu Efes person içinde.

Konuşma: “Biçimsel başarı anlamsal doğruluk değildir. Altın NER etiketleri olmadan halüsinasyon yüzdesi veya NER F1 söylemiyorum.”

## 10. Tekrar üretim ve sonuç

Slayt: Kanonik dosyalar, hash doğrulaması, altı şekil ve kayıtları atlayan başlatıcı.

Konuşma: “Aynı 200 kimliği ve ham yanıtlardan hesaplanan metrikleri doğrulayabiliyorum; tamamlanmış koşuda yeni model isteği yapılmıyor.”

## Sonuç tablosu

| Metric | A: Prompt only | B: JSON Schema | C: Optimized schema |
|---|---:|---:|---:|
| Raw JSON | 0/200 (0.00%) | 158/200 (79.00%) | 200/200 (100.00%) |
| Clean JSON | 166/200 (83.00%) | 158/200 (79.00%) | 200/200 (100.00%) |
| Schema valid | 162/200 (81.00%) | 158/200 (79.00%) | 200/200 (100.00%) |
| Correct category | 80/200 (40.00%) | 87/200 (43.50%) | 107/200 (53.50%) |
| Conditional accuracy | 80/162 (49.38%) | 87/158 (55.06%) | 107/200 (53.50%) |
| Total time (s) | 689.88 | 505.97 | 241.83 |
| Mean time (s) | 3.45 | 2.53 | 1.21 |

## Ağsız canlı gösterim

1. `data/test_samples.jsonl` içindeki ilk beş kayıt ve `[5:205]` ayrımını gösterin.
2. ID 4000 haberini A/C ham yanıtlarıyla yan yana açın; biçim ve varlık türü farkını anlatın.
3. `venv/bin/python src/step3_run_experiments.py` çalıştırın: tamamlanmış kayıtlar doğrulanır ve model çağrısı yapılmaz.
4. `venv/bin/python src/step6_verify_project.py` ile aynı 200 ID ve ham metrik kontrolünü gösterin.
5. `results/figures/json_success_comparison.png`, `results/figures/classification_accuracy.png` ve `results/figures/confusion_matrix.png` dosyalarını açın. Ham JSON, sınıflandırma ve hata dağılımını karşılaştırın; diğer üç şekle README üzerinden ulaşın.

Dosya sırasını anlatırken 1 veri hazırlama, 2 geliştirme bağlantı denemesi, 3 deney başlatıcı, 3a A istem, 3b B JSON Schema, 3c C optimize şema, 4 analiz, 5 şekiller, 6 doğrulama olarak ilerleyin. [Kod çalışma rehberindeki tablo](CODE_STUDY_GUIDE_TR.md) her dosyanın görevini açıklar. Başlatıcı A → B → C sırasını korur. `dev_evaluate_baseline.py` ayrı geliştirme aracıdır.

Bu tamamlanmış projede canlı gösterim için 2. adımı veya geliştirme baseline'ını çalıştırmayın: bunlar gerçek model isteği yapar. 3. adım tam checkpoint'i doğrulayıp çıkar; 6. adım ham sonuçlarla metrik/karmaları karşılaştırır. Üç değerlendirme betiğinin giriş açıklamalarındaki eski başlatıcı adı kaynak korunumu nedeniyle durur; güncel komutları README ve bu rehberden alın.

## İki dakikalık açılış

“Projem Türkçe haberleri yedi kategoriye ayırıyor ve kişi, kurum, yer adlarını JSON biçiminde çıkarıyor. Hazır yerel Qwen modeline üç yapılandırmayla aynı 200 değerlendirme kaydını gönderdim. İlk beş geliştirme haberini bu ölçümün dışında tuttum. 200 kayıt farklı kimlikler taşıyor ancak iki kimlik aynı metin; dolayısıyla 199 farklı metin var.

Sadece istem kullanan yöntemde ham JSON başarısı sıfır, şema kullanılan yöntemde yüzde 79, kısa istem ve tekrar kontrolünü birleştiren yöntemde yüzde 100 oldu. Kategori doğrulukları sırasıyla yüzde 40, 43,50 ve 53,50. En son yöntemin toplam süresi 241,83 saniye. Bu karşılaştırma birlikte değişen ayarların sonucudur; tek parametrenin nedensel etkisini ölçmedim.

Bütün JSONL sonuçlarını korudum, bayrakları ham yanıtlardan yeniden hesapladım ve aynı kimlikleri kontrol ettim. Şemanın geçmesi haberin veya varlığın doğru anlaşıldığı anlamına gelmiyor. İnsan etiketli varlık referansım olmadığı için anlamsal NER veya halüsinasyon başarı oranı raporlamıyorum.”
