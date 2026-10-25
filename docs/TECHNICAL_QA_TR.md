# Teknik sözlü sınav soruları ve cevapları

Bu belge kanonik kod ve tamamlanmış 200 örneklik ham çıktılara dayanır. Beş geliştirme kaydı ana ölçümün dışındadır; değerlendirmede 200 ID ve 199 farklı metin vardır (2138/2296 aynı metin). Varsayımsal değişikliklerin hiçbiri kaynakta uygulanmadı. Bir parametrenin olası etkisi, ölçülmüş deney sonucu diye sunulmaz.

Dosyalar işlem sırasına göre adlandırılmıştır: 1 veri hazırlama, 2 geliştirme bağlantı denemesi, 3 başlatıcı, 3a/3b/3c A/B/C deneyleri, 4 analiz, 5 şekiller, 6 rapor, 7 doğrulama ve 8 teslim paketi. [Kod çalışma rehberi](CODE_STUDY_GUIDE_TR.md) her adımın dosya adını ve görevini açıklar. Ana komut `python src/step3_run_experiments.py`; tamamlanmış 600 kayıt varken ağ isteği yapmaz. `dev_evaluate_baseline.py` ayrı beş kayıtlık geliştirme deneyidir. Üç değerlendirme kaynağının baytları ve karmaları korunmuştur; giriş açıklamalarındaki eski başlatıcı adı tarihsel kalıntıdır. Manifestteki tarihsel modül adları 7. adımda güncel adlarla eşlenir.

## 1. Halüsinasyon: tam olarak neyi ölçtük?

Bu görevde halüsinasyon, modelin verilen haberle desteklenmeyen bir isim veya bilgi üretmesidir. Akıcı veya biçimsel olarak kusursuz yazılmış olması bu bilgiyi doğru yapmaz. Ancak her hata halüsinasyon değildir. Haber sınıfını yanlış seçmek, varlığı yanlış türe koymak ve JSON'u yarım bırakmak farklı sorunlardır. Bir çıktıda birden fazla hata aynı anda bulunabilir.

| Hata türü | Anlamı | Gerçek değerlendirme örneği | Kodun gördüğü |
|---|---|---|---|
| Biçim/ayrıştırma | Yanıtın tamamı JSON sözdizimine uymuyor. | A, ID 4000: Markdown çiti ve son açıklama; temizlikten sonra açılır. B, ID 472: tekrarlarla kesilmiş eksik JSON. | raw/clean bayrakları. |
| Şema | JSON açılır ama istenen yapı/değer kümesi sağlanmaz. | A, ID 4558: category=entertainment; A, ID 401: ilk nesnede entities yok. | schema_valid=False. |
| Desteklenmeyen varlık | Çıkarılan isim kaynak haberle desteklenmiyor. | A, ID 4000: İzmir çıktıda var; haber metni Anadolu Efes/Dario Saric transferini anlatıyor, İzmir için dayanak yok. | Otomatik anlamsal denetim yok. |
| Yanlış varlık türü | İsim haberde geçiyor ama kişi/kurum/yer ayrımı yanlış. | C, ID 4000: Anadolu Efes person listesinde. | Metin listesi oldukları için şemayı geçer. |
| Yanlış sınıflandırma | Yedi geçerli etiketten haberin referansına uymayanı seçmek. | C, ID 4558: gerçek teknoloji, tahmin spor; şema geçerli. | category_correct=False. |

ID 472'de B'nin tekrar ettiği `mustafa_kemal_atatürk` ve `ismet_inönü` **haber metninde bulunur**. Bu örnekte sırf çok tekrar var diye bu isimleri uydurma saymak yanlıştır. Sorun tekrar, token bütçesinin tükenmesi ve JSON'un yarım kalmasıdır. C'nin `oguz_kaan_salıcı` yazımı ile metindeki `oğuz kaan salıcı` birebir aynı değildir; bu da düz alt dize kontrolünün neden yeterli olmadığını gösterir.

### Çıktının halüsinasyon olduğunu nasıl anlarsınız?

1. Ham çıktıyı ve aynı ID'li **tam haber metnini** yan yana açarım. Temizlenmiş nesne ile ham metni karıştırmam; eksik JSON'daki isimler de nitel inceleme için görülebilir ama yapısal ölçüme geçerli çıktı diye eklenmez.
2. İsim için kaynakta dayanak ararım: tam yazım, boşluk/alt çizgi, büyük-küçük harf, Türkçe karakter, çekim eki, kısaltma ve bağlamsal eşdeğerlik.
3. İsmin doğru türde olup olmadığını ayrıca kontrol ederim. Takım adı haberde bulunsa bile person olması yanlıştır.
4. Destek yoksa “metinle desteklenmeyen varlık adayı” diye işaretlerim; insan incelemesiyle bağlamı doğrularım. Gerçek dünyada var olan bir yer de bu haberden çıkarılmamışsa desteklenmeyen eklemedir.
5. Güvenilir bir ölçüm için örneklerin varlık sınırlarını ve türlerini insanlar önceden etiketlemeli; ortak bir yönerge, iki değerlendirici ve anlaşmazlık çözümü kullanılmalıdır. Kesin/gevşek eşleşme politikasını önceden belirleyip precision, recall ve F1 hesaplanabilir. Bu, **gelecek çalışma önerisidir; mevcut uygulama değildir**.

`entity in article` tek başına kanıt değildir. “Ali” başka bir sözcüğün içinde bulunabilir; “Dario Saric” ile “dario_saric” eşleşmeyebilir; “İzmir”/“izmir” karşılaştırması Unicode/Türkçe harfler nedeniyle sorun çıkarabilir. Metinde bir isim geçmesi doğru kişiyle ilişkilendirildiğini veya doğru türde olduğunu kanıtlamaz. Tam eşleşmenin bulunmaması da tek başına uydurma olduğunu kanıtlamaz. ID 4000'de İzmir değerlendirmesi, sadece substring testine değil tam haberin okunmasına dayanan nitel bir bulgudur; corpus geneli halüsinasyon oranı değildir.

**Dürüst sunum cümlesi:** “JSON ve şema geçerliliği ile belge sınıflandırmasını ölçtüm. Varlıklarda tekrar ve liste uzunluğu denetimi yaptım; elle etiketlenmiş NER referansı olmadığı için anlamsal NER başarısı veya halüsinasyon oranı raporlamadım.”

### Dosyadan kısa kanıtlar

Aşağıdaki örnekler dosyalardan alınmıştır; metinler yeniden modele ürettirilmemiştir.

`results/improved_prompt_results.jsonl`, ID 4558, gerçek etiket `teknoloji`:

````text
```json
{
  "category": "entertainment",
  "entities": {
    "person": [],
    "organization": [],
    "location": []
  }
}
```

**Açıklama:** Bu haber, popüler çizgi film "Family Guy" ile ilgili olarak yazılmıştır. Ancak, haberin ana konusu "Family Guy Online" projesinin veda kararıdır. Bu konu, sanat ve eğlence kategorisine aittir. Haberin metninde person, organization ve location gibi özel varlıkları bulunmamaktadır.
````

`results/optimized_schema_results.jsonl`, ID 4000, gerçek etiket `spor`:

```text
{
  "category": "spor",
  "entities": {
    "person": ["Dario Saric", "Anadolu Efes"],
    "organization": [],
    "location": []
  }
}
```

`results/optimized_schema_results.jsonl`, ID 4558, gerçek etiket `teknoloji`:

```text
{
  "category": "spor",
  "entities": {
    "person": [],
    "organization": [
      "family guy online"
    ],
    "location": []
  }
}
```

## 2. Token seçimi: temperature, top-k ve top-p

Token, modelin ürettiği metnin bir parçasıdır; her zaman bir kelime değildir. Türkçe bir sözcük birkaç token olabilir; tırnak, virgül ve süslü parantezler de üretimin parçalarıdır. Model her adımda olası devamları puanlar. Çözümleme (decoding), bu puanlardan bir sonraki tokenın nasıl seçileceğidir.

Temel tanımlar için [Ollama parametre başvurusu](https://docs.ollama.com/modelfile) kullanıldı. Aşağıdaki olasılık örnekleri ders amaçlıdır; proje tarafından ölçülmüş token olasılıkları değildir. API/model sürümü ve örnekleyici sırası ayrıntıları etkileyebilir; güncel belgedeki varsayılan değerleri kaydedilen koşunun ölçülmüş ayarı diye sunmuyoruz.

### Temperature — dağılımın ne kadar keskin olduğu

Pozitif sıcaklıkta olasılıklar genellikle `softmax(logit / T)` biçiminde ele alınır. T küçülünce yüksek puanlı tokenlar daha baskın, büyüyünce dağılım daha yayvan olur. T=0 matematiksel olarak bu formüle bölme değildir; çalışma zamanı genellikle en yüksek puanı seçen özel bir yol kullanır. Bizde açıkça **temperature=0** vardır; 0.8 veya başka sıcaklıklarla kontrollü karşılaştırma yapılmadı.

- **Artırılırsa:** alternatif devamların seçilme olasılığı artabilir. Yaratıcı görevlerde çeşitlilik yararlı olabilir; aynı haber için tutarlılık düşebilir. Sıcaklık doğruluk ölçüsü değildir.
- **Azaltılırsa:** baskın devam daha düzenli seçilir. Sabit biçimli görevlerde tekrarlanabilirliğe yardımcı olabilir; baskın devam hatalıysa hata da düzenli tekrarlanabilir. Düşük sıcaklık halüsinasyonu sıfırlamaz.
- **JSON etkisi:** şema olmadan gereksiz açıklama veya farklı yazım üretilebilir; şema varsa geçerli token alanı ayrıca sınırlandırılır. Hangi sıcaklığın daha iyi olacağı bu veriyle ölçülmeden bilinmez; sıcaklık artışı mutlaka JSON bozar diye söylenmez.
- **Örnek:** sıradaki adayların puanları kapanış parantezini güçlü destekliyorsa düşük sıcaklık onu seçmeye eğilimlidir; daha yüksek sıcaklık başka devamı seçebilir. C'de şemanın izin vermediği bir tokenı sırf sıcaklık yükseldi diye serbest bıraktığını varsaymayız.

### Top-k — en iyi kaç adayın tutulduğu

Pozitif bir k için en yüksek puanlı k aday korunur; diğerleri sonraki seçimin dışında kalır. **k yükseldikçe** aday havuzu genişleyebilir; çeşitli sözcükler için alan açılır ama düşük olasılıklı hatalar da aday olabilir. **k küçüldükçe** havuz daralır; çıktı daha tutarlı olabilir ama doğru bir aday ilk k dışında kalabilir. k=1 yalnız en üst adayı bırakır. Sıfır gibi özel değerlerin anlamı çalışma zamanına bağlıdır; burada o değerleri sınamadık.

Ders örneği: A=.50, B=.25, C=.15, D=.10 olsun. Top-k=2, A ve B'yi tutar; yeniden ölçeklenirse .667/.333 olur. Top-k=3 C'yi de aday yapar. Bunlar kelime/sınıf olasılıkları olmak zorunda değildir; modelin sıradaki tokenlarıdır.

JSON için daha dar havuz biçimi daha düzenli yapabilir, ama gerekli düşük olasılıklı kapanış/isim tokenını dışarıda da bırakabilir; net etkiyi ölçmek gerekir. Bir şema bu havuzu ayrıca etkiler. Temperature=0 koşulunda birçok örnekleyicide en yüksek puan seçildiği için top-k değişikliği hiçbir fark yaratmayabilir; bizim kaydedilen çalışma zamanında ayrı bir top-k etkisi ölçülmedi.

### Top-p — toplam olasılığı yeterli olan adaylar

Adaylar büyükten küçüğe sıralanır; toplam olasılık p eşiğine ulaşana kadar bir havuz oluşturulur. Top-k sabit sayıyı, top-p dağılıma göre değişen sayıyı sınırlar. **p büyüdükçe** daha geniş havuza izin verilir; **p küçüldükçe** en güçlü adaylara odaklanılır. Küçük p tutarlılığa yardımcı olabilir ama doğru az olası devamı eleme riski taşır; büyük p çeşitlilik ve hata olasılığını birlikte artırabilir. p, cevabın doğru olma olasılığı değildir.

Ders örneği aynı dağılımda A=.50, B=.25, C=.15, D=.10 olsun. p=.70 için ilk iki adayın toplamı .75 yeterlidir; p=.90 için ilk üç toplamı .90 olur. Gerçek uygulamalar eşik ve minimum aday sayısı gibi ayrıntılar kullanabilir. Yüksek/düşük p'nin yapılandırılmış çıktıya net etkisini ölçmedik. Temperature=0 özel seçimi varsa top-p değişikliğinin görünür etkisi olmayabilir.

### Biz gerçekte hangi ayarları kullandık?

| Açık seçenek | A | B | C |
|---|---|---|---|
| temperature | 0 | 0 | 0 |
| seed | 42 | 42 | 42 |
| num_ctx | 4096 | 4096 | 4096 |
| num_predict | 384 | 384 | 384 |
| format | İstekte yok | JSON_SCHEMA | JSON_SCHEMA |
| repeat_penalty | Açıkça ayarlanmadı | Açıkça ayarlanmadı | 1.2 |
| repeat_last_n | Açıkça ayarlanmadı | Açıkça ayarlanmadı | 128 |
| top_k | Açıkça ayarlanmadı | Açıkça ayarlanmadı | Açıkça ayarlanmadı |
| top_p | Açıkça ayarlanmadı | Açıkça ayarlanmadı | Açıkça ayarlanmadı |

**top_k ve top_p kodda yapılandırılmamıştır. Ollama çalışma zamanı/model varsayılanları kullanılır; kontrollü top-k/top-p karşılaştırması yapmadık.** Bu değerler sonuç kayıtlarında da yoktur. “Varsayılanları kullandık” demek bu mekanizmalar hiç yok demek değildir. Yeni başlatıcı `/api/show` bilgilerini kaydeder ama model seçeneklerini değiştirmez. `step2_test_model.py` kısa denemesi bu tablonun dışında, yalnız temperature ve num_ctx ayarlar.

## 3. Kod değişirse ne olur? 26 savunma sorusu

Her kod parçası mevcut kanonik kaynaktan alınmıştır. “Kuramsal” ifadesi kaynak akışından veya örnekleyici bilgisinden beklenen etkidir; o değişiklikle yeni bir model deneyi yapıldığı anlamına gelmez.

### 1. temperature=0 yerine 0.8 olursa?

Kaynak: `src/step3a_evaluate_prompt.py`

```python
"temperature": 0,
```

**Şimdi:** Üretimde rastgeleliği azaltan sıfır sıcaklık kullanılıyor.

**Varsayımsal değişiklik / beklenen etki:** Değer 0.8 yapılırsa olasılıklı alternatif seçimler daha görünür olabilir; aynı haber farklı isim/sınıf verebilir. Şema varsa biçim ayrıca sınırlandırılır; kesin doğruluk veya JSON kaybı oranı öngörülemez.

**Kanıt durumu:** Kuramsal. Bu değişiklik denenmedi; bütün ana deneylerde 0 var.

### 2. num_predict=384 yerine 128 olursa?

Kaynak: `src/step3c_evaluate_optimized.py`

```python
"num_predict": 384,
```

**Şimdi:** En fazla 384 çıktı tokenına izin verilir; token karakter değildir.

**Varsayımsal değişiklik / beklenen etki:** 128 daha erken durmaya yol açabilir; uzun varlık listesinde kapanış gelmeden kesilirse JSON başarısız olur. Kısa yanıtlar etkilenmeyebilir. Gecikmenin mutlaka üçte bire düşeceği söylenemez.

**Kanıt durumu:** 128 koşulu denenmedi. B sonuçlarında 384 sınırına ulaşan kesilmeler gözlendi; bu yalnız mevcut sınır için kanıttır.

### 3. JSON Schema format seçeneği kaldırılırsa?

Kaynak: `src/step3b_evaluate_json.py`

```python
"format": JSON_SCHEMA,
```

**Şimdi:** Ollama üretimi şemaya göre sınırlandırır; Python validate_schema ayrıca çalışır.

**Varsayımsal değişiklik / beklenen etki:** B isteğinden format kaldırılırsa üretim sınırlaması kalkar, sonradan doğrulama kalır. B istemi A ile aynı olduğundan A buna en yakın mevcut deneydir.

**Kanıt durumu:** A/B karşılaştırması aynı 200 ID üzerinde tamamlandı: ham JSON A %0, B %79; kategori doğruluğu A %40, B %43,50. Yeniden çıkarımın birebir aynı metni üretmesi garanti değildir.

### 4. try-except kaldırılırsa?

Kaynak: `src/step3a_evaluate_prompt.py`

```python
except (requests.RequestException, ValueError, KeyError) as e:
```

**Şimdi:** Bilinen bağlantı/zarf hataları api_error alanına yazılır, ölçüm kaydı döner.

**Varsayımsal değişiklik / beklenen etki:** İstisna yukarı taşabilir ve döngüyü kesebilir; o haberin kaydı yazılmayabilir. Daha önce diske yazılan sonuçlar kalır.

**Kanıt durumu:** Kaynak akışından beklenen sonuç; try-except kaldırılarak model deneyi yapılmadı.

### 5. json.loads(raw) başarısız olursa?

Kaynak: `src/step3a_evaluate_prompt.py`

```python
parsed = json.loads(raw)
```

**Şimdi:** Ham metnin tamamının JSON olması denenir; değilse JSONDecodeError iç except tarafından yakalanır.

**Varsayımsal değişiklik / beklenen etki:** Mevcut durumda clean_and_parse denenir. Bu satırı başarısız olacak metinle karşılaştırınca raw False, temizleme sonucuna göre clean True/False olur. İkinci LLM çağrısı yapılmaz.

**Kanıt durumu:** A: 0/200 ham başarı, 166/200 temiz başarı; mevcut davranış gözlendi. Kod değişikliği uygulanmadı.

### 6. stream=False yerine True olursa?

Kaynak: `src/step3a_evaluate_prompt.py`

```python
"stream": False,
```

**Şimdi:** Tek yanıt gövdesi response.json() ile okunur.

**Varsayımsal değişiklik / beklenen etki:** Sunucu parçalı yanıt döndürürse mevcut tek JSON okuyucu çoğunlukla extra data/ValueError verir; parçaların birleştirilmesi yoktur. Modelin ürettiği çıktı değil HTTP zarfı okunamayabilir.

**Kanıt durumu:** Kuramsal; streaming koşusu yapılmadı. API davranışı resmi belgede açıklanır.

### 7. seed=42 kaldırılırsa?

Kaynak: `src/step3a_evaluate_prompt.py`

```python
"seed": 42,
```

**Şimdi:** Model tarafındaki rastgele üreteç için açık tohum verilir.

**Varsayımsal değişiklik / beklenen etki:** Runtime varsayılanına geçilir. Tekrarlanabilirlik güvencesi azalabilir; temperature=0 altında görünür fark oluşmayabilir. Kaynak/Donanım farkını seed zaten ortadan kaldırmaz.

**Kanıt durumu:** Kuramsal. Ayrıca step1_prepare_dataset içindeki SEED bağımsızdır; bu satırı silmek veri sırasını değiştirmez.

### 8. Kategori enum kaldırılırsa?

Kaynak: `src/step3b_evaluate_json.py`

```python
"enum": sorted(CATEGORIES)
```

**Şimdi:** Sunucuya yedi izin verilen kategori bildirilir.

**Varsayımsal değişiklik / beklenen etki:** Üretim şeması başka stringlere izin verebilir. Yerel validate_schema içindeki CATEGORIES kontrolü kaldığı için bilinmeyen kategori yine reddedilir.

**Kanıt durumu:** Kuramsal kaldırma; A ID 4558 entertainment örneği enum olmadan görülen olası soruna gerçek örnektir, birebir bu değişikliğin deneyi değildir.

### 9. additionalProperties=False kaldırılırsa?

Kaynak: `src/step3b_evaluate_json.py`

```python
"additionalProperties": False
```

**Şimdi:** Bulunduğu nesne düzeyinde fazladan anahtar yasaktır; hem dış hem entities düzeyinde bulunur.

**Varsayımsal değişiklik / beklenen etki:** İlgili düzeyde üretim şeması ek anahtara izin verebilir. Yerel tam anahtar kümesi kontrolü yine reddeder. Sadece dış satırı silmek iç kısıtlamayı kaldırmaz.

**Kanıt durumu:** Kuramsal; şema değişikliği yapılmadı.

### 10. JSON temizleme devre dışı bırakılırsa?

Kaynak: `src/step3a_evaluate_prompt.py`

```python
success, parsed = clean_and_parse(raw)
```

**Şimdi:** Ham ayrıştırma olmazsa mevcut metinden nesne kurtarılır.

**Varsayımsal değişiklik / beklenen etki:** Başarısız ham çıktılarda clean False bırakılan bir uygulamada Markdown içindeki geçerli nesneler de kaybedilir. Satırı yalnız silmek parsed/success değişkenlerini tanımsız bırakabilir; bu farklı bir Python hatasıdır.

**Kanıt durumu:** Saklanmış A ham metinlerinin hiçbirinin direkt loads geçmemesi gözlendi. Temizlemesiz yeniden inference deneyi yapılmadı; sabit kayıtlar için etkisi çıkarılabilir.

### 11. Timeout azaltılırsa?

Kaynak: `src/step3a_evaluate_prompt.py`

```python
timeout=(5, 60)
```

**Şimdi:** Bağlantı ve okumada bekleme süreleri ayrıdır.

**Varsayımsal değişiklik / beklenen etki:** Örneğin okuma 1 saniye olursa model henüz yanıt vermeden timeout kaydı oluşabilir. Süreç devam eder; o ID sonraki çalışmada atlanır. Timeout modeli daha hızlı hale getirmez ve sunucudaki hesaplamayı mutlaka durdurmaz.

**Kanıt durumu:** Kuramsal; yeni timeout değeri denenmedi.

### 12. Aynı entity tekrar edilirse?

Kaynak: `src/step4_analyze_results.py`

```python
if len(normalized) != len(set(normalized)):
```

**Şimdi:** Analiz aynı listedeki normalleştirilmiş tekrarları sayar.

**Varsayımsal değişiklik / beklenen etki:** Tekrar içeren liste string array ise şemayı geçer; bu koşul sadece kalite sayacını artırır, listeyi silmez/düzeltmez. C istemi tekrar istemese de bunu garanti etmez.

**Kanıt durumu:** Tarihsel C ID 2138 location içinde istanbul tekrarı kaydedilmiştir.

### 13. Sonuç dosyası IDyi zaten içeriyorsa?

Kaynak: `src/step3a_evaluate_prompt.py`

```python
if sample["id"] in results:
```

**Şimdi:** Checkpoint sözlüğünde görülen kimlik yeniden işlenmez.

**Varsayımsal değişiklik / beklenen etki:** Daha önce aynı ID için hata olsa da continue çalışır. İstemi değiştirip aynı dosyada sürdürmek yeni/eski koşulları karıştırabilir; bu görevde ayrı yollar kullanıldı.

**Kanıt durumu:** Mevcut akış doğrudan kodda doğrulandı; yeni parametre koşusu yapılmadı.

### 14. Veri kümesinde duplicate kayıt varsa?

Kaynak: `src/step3a_evaluate_prompt.py`

```python
results[item["id"]] = item
```

**Şimdi:** Sonuç sözlüğü ID ile anahtarlanır; aynı ID yüklenirse son kayıt öncekinin yerini alır.

**Varsayımsal değişiklik / beklenen etki:** Aynı ID veri listesinde iki kez bulunursa döngü ikinci isteği atlar ama özet seçimi aynı sonucu iki kez sayabilir. Farklı ID/aynı metin ise iki ayrı kayıt olarak ölçülür.

**Kanıt durumu:** Yeni analiz duplicate IDyi reddeder. Eski 2138/2296 aynı metindir; korunup açıkça belgelenmiştir. Algoritma değişmedi.

### 15. Geçerli JSONda kategori yanlışsa?

Kaynak: `src/step3c_evaluate_optimized.py`

```python
parsed["category"] == sample["true_category"]
```

**Şimdi:** Yalnız şema geçtiğinde tahmin referans kategoriyle eşitlik açısından karşılaştırılır.

**Varsayımsal değişiklik / beklenen etki:** İzin verilen fakat yanlış sınıf: raw/clean/schema True, category_correct False. İzin verilmeyen sınıfsa önce schema False olur.

**Kanıt durumu:** Gerçek örnek C ID 4558: teknoloji → spor. Bu ordinary sınıflandırma hatasıdır; otomatik halüsinasyon tespiti değildir.

### 16. Yanıtta iki JSON nesnesi varsa?

Kaynak: `src/step3a_evaluate_prompt.py`

```python
obj, _ = decoder.raw_decode(cleaned[i:])
```

**Şimdi:** İlk çözülen { başlangıcındaki nesne döndürülür; bitiş indeksi yok sayılır.

**Varsayımsal değişiklik / beklenen etki:** İki nesne birleştirilmez. İlk nesne eksik alanlıysa şema başarısız; ilk nesne geçerliyse ikinci nesne atlanabilir. raw loads ise sonda başka nesne olduğunda başarısız olur.

**Kanıt durumu:** A ID 401 gerçek örnek: önce category, sonra entities. Temizleme True, schema False.

### 17. repeat_penalty artırılırsa?

Kaynak: `src/step3c_evaluate_optimized.py`

```python
"repeat_penalty": 1.2,
```

**Şimdi:** Cde tekrar eden token seçimi caydırılır.

**Varsayımsal değişiklik / beklenen etki:** Daha güçlü ceza tekrar döngüsünü azaltabilir; aynı ismin gerekli parçalarını veya doğal yazımı da bozabilir. En yüksek değer en iyi sonuç değildir; yeni etki oranı verilemez.

**Kanıt durumu:** Kuramsal. Cde 1.2 var; ayrı ceza taraması/ablasyon yok. C istemi de Bden farklı.

### 18. top_p değiştirilirse?

Kaynak: `src/step3c_evaluate_optimized.py`

```python
"temperature": 0,
```

**Şimdi:** Seçeneklerde top_p yok; sıfır sıcaklık açıkça var.

**Varsayımsal değişiklik / beklenen etki:** Yeni top_p eklemek çalışma koşulunu değiştirir. Pozitif sıcaklıkta olasılık havuzu genişleyip daralabilir; sıfırda etkisiz kalabilir. Varsayılan gerçek değeri parametreleri kaydetmeyen kayıttan çıkaramayız.

**Kanıt durumu:** Kuramsal; hiçbir kontrollü top_p karşılaştırması yok, kodda eklenmedi.

### 19. top_k değiştirilirse?

Kaynak: `src/step3c_evaluate_optimized.py`

```python
"num_predict": 384,
```

**Şimdi:** Seçeneklerde token limiti var ama top_k yok. Bu snippet bir options alanıdır; top_k için mevcut satır yoktur.

**Varsayımsal değişiklik / beklenen etki:** top_k eklemek aday sayısını kontrol edebilir; 384 ile ilgisi yoktur, 384 token bütçesidir. Küçük k çeşitliliği azaltabilir; temperature=0 nedeniyle fark oluşmayabilir.

**Kanıt durumu:** Kuramsal; kontrollü top_k deneyi yok. Ek seçenek eklenmedi.

### 20. Değerlendirme yarıda kesilirse?

Kaynak: `src/step3a_evaluate_prompt.py`

```python
with open(RESULT_PATH, "a", encoding="utf-8") as f:
```

**Şimdi:** Her sonuç tek satır eklenip dosya kapatılır; yalnız en son terminal özeti beklenmez.

**Varsayımsal değişiklik / beklenen etki:** Tam yazılmış IDler yeniden başlatmada atlanır. O anda çıkarımı süren haber kayıtsızsa yeniden işlenir. Yazım sırasında kesinti son satırı bozabilir; kod bunu otomatik düzeltmez.

**Kanıt durumu:** Mevcut checkpoint mantığından açıklama; güç kesintisi deneyi yapılmadı.

### 21. num_ctx azaltılırsa?

Kaynak: `src/step3c_evaluate_optimized.py`

```python
"num_ctx": 4096,
```

**Şimdi:** İstemin ve üretimin sığdığı bağlam penceresi token cinsinden ayarlanır.

**Varsayımsal değişiklik / beklenen etki:** Haber ve talimat sığmayabilir; runtime bağlamı kısaltabilir veya hata verebilir. 3000 karakter filtresi, her zaman 3000 token demek değildir.

**Kanıt durumu:** Kuramsal; başka num_ctx ölçülmedi.

### 22. Şema kontrolü kaldırılıp sadece kategoriye bakılırsa?

Kaynak: `src/step3a_evaluate_prompt.py`

```python
if result["schema_valid"]:
```

**Şimdi:** Uçtan uca başarı için önce uygulamanın beklediği yapı istenir.

**Varsayımsal değişiklik / beklenen etki:** Eksik entities içeren nesneye doğru etiket puanı vermek metriğin tanımını değiştirir; kullanılabilir yapılandırılmış çıktı üretilememişken başarıyı şişirebilir. Doğrudan alan erişimi ayrıca KeyError yaratabilir.

**Kanıt durumu:** Kuramsal değişiklik; A ID 401 örneği bu ayrımı gösterir. Bu projede yapılmadı.

### 23. samples[5:5+limit] yerine ilk 200 alınırsa?

Kaynak: `src/step3a_evaluate_prompt.py`

```python
selected = samples[5:5 + args.limit]
```

**Şimdi:** İlk beş geliştirme haberi ayrılır.

**Varsayımsal değişiklik / beklenen etki:** Geliştirmede kullanılan haberler teste girer, sondaki beş değerlendirme haberi dışarıda kalır. A/B/C aynı kimlikleri değerlendirmeyebilir; metrik karşılaştırması bozulur.

**Kanıt durumu:** Dilim ve ID kontrolleriyle belirlenen mantıksal etki; böyle bir deney yapılmadı.

### 24. raw_json_valid temizleme sonrasında True yapılırsa?

Kaynak: `src/step3a_evaluate_prompt.py`

```python
result["raw_json_valid"] = True
```

**Şimdi:** Bu bayrak yalnız doğrudan json.loads(raw) başarılı olunca ayarlanır.

**Varsayımsal değişiklik / beklenen etki:** Temizleme başarısını raw saymak modelin ilk deneme başarısını olduğundan yüksek gösterir. İki aşamayı ayrı ölçmenin anlamı kaybolur.

**Kanıt durumu:** Kuramsal değişiklik; A ham 0, temiz 166 sayımları neden ayrılması gerektiğinin gerçek kanıtıdır.

### 25. repeat_last_n=128 değişirse?

Kaynak: `src/step3c_evaluate_optimized.py`

```python
"repeat_last_n": 128
```

**Şimdi:** Tekrar kontrolü son 128 tokenı dikkate alır; haber sayısı değildir.

**Varsayımsal değişiklik / beklenen etki:** Pozitif değeri büyütmek daha geniş geçmişi cezaya dahil edebilir; küçültmek uzak tekrarları gözden kaçırabilir. İsimler ve JSON işaretleri üzerindeki net etki ölçülmelidir.

**Kanıt durumu:** Kuramsal; 128 dışında kontrollü koşu yok.

### 26. required kaldırılırsa?

Kaynak: `src/step3b_evaluate_json.py`

```python
"required": ["category", "entities"],
```

**Şimdi:** Üretim şemasında iki üst alanın bulunması zorunludur.

**Varsayımsal değişiklik / beklenen etki:** Properties alan türlerini tarif etmeye devam eder ama zorunluluk kalkar. Yerel tam anahtar kontrolü eksik alanları yine reddeder; alt entities required listesi ayrıca durur.

**Kanıt durumu:** Kuramsal; gerçek şema değiştirilmedi. A ID 401 eksik alan sorununa örnektir.

## 4. Savunmada kullanılacak üç kısa ayrım

- “JSON geçerli” = metin ayrıştırılabiliyor. “Şema geçerli” = uygulamanın alan/tür kuralları sağlanıyor. “Doğru bilgi” = kaynak içerikle anlamsal uyum. Üçü aynı şey değil.
- “Deneyler arasında fark gördüm” = ortak değişikliklerin birlikte etkisi gözlendi. “Sadece repeat_penalty bunu sağladı” = elimizde olmayan ayrı bir nedensel iddia.
- “200 haber seçtim” = veri hazır. “200 haberde sonuç aldım” = her deneyin 200 benzersiz ölçümü tamamlanmalı. İkinci cümle artık doğrulanmıştır: A/B/C aynı 200 ID için tamamlanmıştır; 200 ID, 199 farklı metin içerir.

Python ayrıştırma davranışları için [Python 3.12 JSON belgeleri](https://docs.python.org/3.12/library/json.html); alan zorunluluğu ve ek anahtarlar için [JSON Schema nesne başvurusu](https://json-schema.org/understanding-json-schema/reference/object); HTTP yanıt akışı için [Ollama generate API](https://docs.ollama.com/api/generate) kullanılabilir. Bu dış kaynaklar kavramları açıklar; deneyin gerçekten kullandığı değerlerin kanıtı yerel kaynak dosyalarıdır.

## Tamamlanmış çalışmanın ölçümleri

| Metric | A: Prompt only | B: JSON Schema | C: Optimized schema |
|---|---:|---:|---:|
| Raw JSON | 0/200 (0.00%) | 158/200 (79.00%) | 200/200 (100.00%) |
| Clean JSON | 166/200 (83.00%) | 158/200 (79.00%) | 200/200 (100.00%) |
| Schema valid | 162/200 (81.00%) | 158/200 (79.00%) | 200/200 (100.00%) |
| Correct category | 80/200 (40.00%) | 87/200 (43.50%) | 107/200 (53.50%) |
| Conditional accuracy | 80/162 (49.38%) | 87/158 (55.06%) | 107/200 (53.50%) |
| Total time (s) | 689.88 | 505.97 | 241.83 |
| Mean time (s) | 3.45 | 2.53 | 1.21 |

Ana oran paydası 200; koşullu payda A=162, B=158, C=200. Kaynak: `results/metrics_summary.json`. Beş geliştirme kaydı dahil değildir.
