# Son doğrulama — 200 değerlendirme kaydı

Göç, üç deneyin tamamlanmış sonuçları ve son analizi kaydedildikten sonra yapıldı. Son sonuç kaydı 25 Ekim 2026 13:00:03 UTC; yedek başlangıcı 13:08:33 UTC. Dosyaların yedekleme sırasında değişmediği hash karşılaştırmasıyla doğrulandı. Süreç görünürlüğü sandbox ad alanıyla sınırlıydı; tamamlanma kanıtı son analiz durumu, tam kayıtlar ve kararlı dosya karmalarıdır. Bu göçte model çıkarımı yapılmadı.

## Koruma ve kanonik dosyalar

Önceki projenin tam arşivi etkin deponun dışında `/tmp/structured-text-project-backup-20261025T130833Z/project-before-migration.tar.gz` yolundadır. Aynı dizindeki `sha256.json` 82 proje dosyasını listeler; arşiv içindeki baytlar ve yedekleme sonrası kaynak baytları bu karmalarla doğrulandı. Arşiv ayrıca sanal ortamı da içerir. `/tmp` geçici depolama alanıdır; kalıcı tarihçe için bu dış yedeği saklayın.

Arşiv, önceki sonuçları ve tamamlanmış yeni koşunun kaynak dosyalarını içerir. Eski sonuç/PDF/şekiller etkin projeden kaldırıldı; arşivde durur. Aktif veri ve üç ana JSONL sonuç dosyası tamamlanmış kaynaktan bayt düzeyinde aynen taşındı. Sonuçların hiçbiri yeniden üretilmedi veya eksik kayıtla doldurulmadı. Beş geliştirme baseline kaydı ayrı korundu.

## Veri ve ölçüm

- `data/test_samples.jsonl`: 205 kayıt, 205 farklı ID, 204 farklı metin.
- İlk beş geliştirme kaydı; `samples[5:205]` tam 200 değerlendirme kaydıdır.
- Değerlendirme: 200 farklı ID, 199 farklı metin. ID 2138 ve 2296 aynı metindir; üyelik ve sıra korunmuştur.
- A/B/C: 200'er kayıt, aynı sıralı ID listesi, 200'er yanıt, sıfır API hatası.
- 600 ham yanıttan JSON/temizleme/şema/kategori bayraklarının tamamı yeniden hesaplandı ve kaydedilmiş bayraklarla eşleşti.
- A/B/C doğru kategori: 80/200 (%40,00), 87/200 (%43,50), 107/200 (%53,50).
- Koşullu doğruluk: 80/162 (%49,38), 87/158 (%55,06), 107/200 (%53,50).
- Matrislerin toplamı 200; satır toplamları kategori desteği, köşegen doğru sayımıyla eşleşir. INVALID sütunu hataları korur.
- Altı şekil PNG ve SVG olarak güncel ham sonuçlardan üretildi. Akademik PDF altı sayfadır; bütün sayfalar PyMuPDF ile açıldı ve raster olarak oluşturuldu, sayfa dışına taşan metin bulunmadı; bütün sayfaların görünümü incelendi.

## Kod ve devam etme

Üç deney betiğinin yürütülebilir AST'si yalnız kanonik veri/sonuç yolları normalize edildiğinde çalıştırılmış kaynakla aynıdır. Modül başı açıklamalar dışında istemler, JSON Schema, inference options, ayrıştırma, doğrulama ve hata işleme değişmedi. Çalıştırılmış ve kanonik kaynak hash eşleştirmesi `migration_manifest.json` içindedir. `run_identity.json` kanonik adlar/hash'lerle devam etmeyi destekler; özgün kimlik dosyası dış yedektedir.

Beş test geçti: tam/eksik analiz, duplicate/yabancı ID ve yanlış bayrak reddi, üç deneyde tam ve kısmi checkpoint sürdürme, tamamlanmış başlatıcıda ağ/alt süreç çağrısı yapılmaması. Sürdürme testi dolu kayıtta sıfır, 199 kayıtlı geçici dosyada yalnız eksik ID için bir çağrı doğruladı. Testler gerçek sonuç dosyalarını değiştirmedi. Veri hazırlama algoritması yerel TTC4900 Arrow kaynağıyla tekrar çalıştırıldı ve aynı dataset hash'ini üretti.

Bütün etkin Python kaynakları ve testleri sözdizimi kontrolünden geçti. Kanonik dosyalarda eski sürüm yolları yoktur. README ve Türkçe rehberler tamamlanmış koşuyu anlatır. Teknik rehberdeki 26 soru korundu; gerçek örnekler güncel ham yanıtlarla düzeltildi.

## Tekrar çalıştırma

```bash
venv/bin/python src/run_evaluation.py
venv/bin/python src/build_report_pdf.py
venv/bin/python src/verify_project.py
venv/bin/python -m unittest discover -s tests -v
venv/bin/python src/package_submission.py
```

Makine kayıtları: [verification.json](verification.json), [pdf_validation.json](pdf_validation.json), [migration_manifest.json](migration_manifest.json). Tüm değişen/eklenen/kaldırılan dosyalar: [MIGRATION_CHANGES.md](MIGRATION_CHANGES.md). Teslim ZIP'i yalnız güncel dosyaları içerir; içindeki dosya baytları etkin proje ile karşılaştırılır, CRC bütünlüğü denetlenir; eski arşivler ve sanal ortam dahil değildir.
