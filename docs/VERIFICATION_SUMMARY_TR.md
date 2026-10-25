# Sunum sürümü doğrulaması — 200 değerlendirme kaydı

Etkin akış veri hazırlama, yerel model denemesi, A/B/C deneyleri, analiz, şekiller ve doğrulamadan oluşur. Ana komut `python src/step3_run_experiments.py`; doğrulama komutu `python src/step6_verify_project.py` olur. Bu sadeleştirme sırasında model çıkarımı, yeniden örnekleme veya şekil üretimi yapılmadı.

## Veri ve korunmuş sonuçlar

- `data/test_samples.jsonl`: 205 kayıt = 5 geliştirme + 200 değerlendirme; değerlendirme dilimi `samples[5:205]`.
- 205 farklı ID ve 204 farklı metin vardır. Değerlendirmede 200 farklı ID, 199 farklı metin bulunur; 2138 ve 2296 aynı metindir. Üyelik ve sıra korunmuştur.
- A/B/C aynı sıralı 200 ID için 200'er yanıt içerir; toplam 600 yanıt ve sıfır API hatası vardır.
- Ham JSON, temizlenmiş JSON, şema ve kategori bayraklarının tamamı ham yanıtlardan yeniden hesaplandı; kayıtlı bayraklar ve metriklerle eşleşti.

| Ölçüm | A | B | C |
|---|---:|---:|---:|
| Yanıt | 200 | 200 | 200 |
| Ham JSON | %0 | %79 | %100 |
| Temiz JSON | %83 | %79 | %100 |
| Şema | %81 | %79 | %100 |
| Doğru kategori | 80/200 (%40) | 87/200 (%43,5) | 107/200 (%53,5) |
| Koşullu doğruluk | 80/162 (%49,38) | 87/158 (%55,06) | 107/200 (%53,50) |
| Toplam süre | 689,88 s | 505,97 s | 241,83 s |
| Ortalama süre | 3,45 s | 2,53 s | 1,21 s |

Üç karışıklık matrisinin her biri 200 kayıt içerir. Satır toplamları kategori desteğine, köşegen doğru kategori sayısına eşittir; INVALID sütunu başarısız çıktıları korur. Altı şeklin PNG ve SVG kopyaları, toplam 12 dosya, yerinde ve değişmeden durur.

Veri ve veri manifesti, bütün kayıtlı sonuçlar, metrik özeti, üç matris, 12 şekil, `results/run_identity.json` ve üç değerlendirme betiğinin SHA-256 değerleri sadeleştirme öncesiyle aynı kaldı. İstemler, JSON Schema, çıkarım parametreleri ve sınıflandırma mantığı değiştirilmedi.

## Kod, testler ve checkpoint

Etkin 10 kaynak dosyası ve bir test dosyası sözdizimi kontrolünden geçti. 73 Python import ifadesi ve README ile dört etkin rehberdeki 37 yerel bağlantı çözümlendi. Veri/sonuç/kaynak/test ve tarihsel kanıtları kapsayan 39 korunan dosyanın baytları değişmedi. Mevcut beş birim testi geçti:

1. Tam analizde API/biçim/şema hataları paydada ve INVALID sütununda kalır.
2. Eksik analiz nihai metrik ve matris üretmez.
3. Yinelenen/yabancı ID ve yanlış kayıtlı bayrak reddedilir.
4. Üç deneyde tam checkpoint sıfır çıkarım yapar; 199 kayıtlı geçici checkpoint yalnız eksik ID için bir taklit çağrı yapar.
5. Tamamlanmış başlatıcı ağ veya alt süreç çağrısı yapmaz.

Testler gerçek sonuç dosyalarını değiştirmedi. Ana başlatıcı ayrıca mevcut 600 kaydı doğrulayıp çıkarım gerekmediğini bildirdi. `step6_verify_project.py` veri/kaynak karmalarını, ID'leri, ham bayrakları, kayıtlı metrikleri, matrisleri ve şekilleri kontrol etti. Güncel makine kaydı [verification.json](verification.json) içindedir.

## Etkin kapsam ve tarihçe

İsteğe bağlı PDF, teslim ZIP'i ve bunları üreten iki betik yerel `legacy/` dizinine taşındı. Her dosyanın taşıma öncesi SHA-256 değeri kaydedildi ve taşınan kopyayla karşılaştırıldı; yerel kayıt `legacy/archive_manifest.json` içindedir. Dosyalar yerel makinede korunur, Git tarafından izlenmez ve `.gitignore` ile dışlanır. `reportlab` yalnız arşivlenen üretici tarafından kullanıldığı için etkin bağımlılıklardan çıkarıldı.

Güncel doğrulama PDF veya ZIP gerektirmez; `verification.json` içinde PDF doğrulama alanı yoktur. Önceki [migration_manifest.json](migration_manifest.json), [MIGRATION_CHANGES.md](MIGRATION_CHANGES.md), [validation_results.json](validation_results.json) ve [pdf_validation.json](pdf_validation.json) tarihsel kanıtlardır ve değiştirilmedi. Bu dosyalardaki eski PDF/teslim kontrolleri önceki sürüme aittir; bu sunum sürümünde yeniden yapılmış kontroller değildir. Önceki dış yedeğin konumu ve hash envanteri de tarihsel manifestte kayıtlıdır.

Üç değerlendirme betiği bayt düzeyinde korunduğu için giriş açıklamalarındaki eski başlatıcı adı durur; güncel komutu aşağıdan kullanın. Doğrulayıcı güncel modül adlarını manifestteki tarihsel adlarla eşleyerek aynı kaynak korunum kanıtını kontrol eder.

## Ağsız sunum kontrolü

Proje kökünde, bağımlılıklar kurulu ortamla:

```bash
venv/bin/python src/step3_run_experiments.py
venv/bin/python src/step6_verify_project.py
venv/bin/python -m unittest discover -s tests -v
```

Tamamlanmış koşuda bu komutlar yeni model yanıtı üretmez. Altı mevcut şekli README bağlantılarından açın. Adımların teknik açıklaması [kod çalışma rehberinde](CODE_STUDY_GUIDE_TR.md), 10–20 dakikalık anlatım planı [sunum hazırlığında](PRESENTATION_PREPARATION_TR.md) yer alır.
