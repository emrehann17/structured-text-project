"""Curated second-pass candidate annotations and review notes for the 100 selected articles.

Every record remains a candidate (status='candidate') until explicitly verified by a human reviewer.
Conventions strictly follow docs/ANNOTATION_GUIDELINES.md:
- person: named real individuals (titles stripped, repeated mentions/aliases grouped with '|').
- organization: companies, institutions, parties, clubs, national sports teams, universities, agencies.
- location: countries, cities, geographic regions, physical venues used as places.
- Maximum five distinct entities per type in order of first mention in the article.
"""

SECOND_PASS_CANDIDATES = {
    4000: {
        "person": ["dario saric | saric"],
        "organization": ["anadolu efes | efes", "kk zagreb", "kk split", "hırvatistan", "litvanya"],
        "location": ["avrupa"],
        "flags": [
            "Type mismatch fixed: 'Anadolu Efes' moved from person to organization.",
            "Missing entities added: 'kk zagreb', 'kk split', 'avrupa'.",
            "Ambiguity: 'hırvatistan' and 'litvanya' act as national basketball teams here (organization per guideline) rather than geographical locations.",
        ],
    },
    933: {
        "person": ["philippe lalliot | lalliot", "el ahdar el ibrahimi"],
        "organization": ["fransa dışişleri bakanlığı | dışişleri bakanlığı", "bm", "arap birliği", "aa"],
        "location": ["suriye", "fransa", "şam"],
        "flags": [
            "Spelling fixed: 'El Ahdar El Ibrahi' -> 'el ahdar el ibrahimi' (exact surface form in text).",
            "Missing organizations and locations added: 'fransa dışişleri bakanlığı', 'bm', 'arap birliği', 'aa', 'suriye', 'şam'.",
        ],
    },
    4558: {
        "person": [],
        "organization": [],
        "location": [],
        "flags": [
            "Likely error fixed: 'family guy online' / 'family guy' is a cartoon/game product, not an organization.",
        ],
    },
    4022: {
        "person": ["ünal aysal | aysal", "özgür gürbulak"],
        "organization": [],
        "location": [],
        "flags": [
            "Type/error fixed: 'ülkelerarası_kupa' (not in text; text has 'kıtalararası_kupa', an event/trophy) removed from person.",
            "Missing person added: 'ünal aysal | aysal'; spacing fixed in 'özgür gürbulak'.",
        ],
    },
    47: {
        "person": ["melih gökçek"],
        "organization": ["twitter", "ankara cumhuriyet başsavcılığı"],
        "location": ["ankara", "abd"],
        "flags": [
            "Missing organizations/locations added: 'twitter', 'ankara cumhuriyet başsavcılığı', 'abd'.",
            "Ambiguity: 'ankara_büyükşehir_belediye_başkanı_melih_gökçek' contains 'ankara'; verify whether 'ankara' should be kept as location.",
        ],
    },
    1578: {
        "person": ["ergun özen"],
        "organization": ["garanti bankası", "avrupa yatırım fonu | ayf"],
        "location": [],
        "flags": [
            "Aliases grouped: 'avrupa yatırım fonu' and 'ayf' merged into one organization entry.",
            "Missing person added: 'ergun özen'.",
        ],
    },
    4772: {
        "person": [],
        "organization": ["gartner"],
        "location": [],
        "flags": [],
    },
    2912: {
        "person": [],
        "organization": [],
        "location": ["avrupa"],
        "flags": [
            "Likely error fixed: 'www.dmgturkey.com' and '+90 (212) 280-8050' are contact details, not named organizations in text.",
            "Missing location added: 'avrupa'. ('gastrotuss' is a product, excluded).",
        ],
    },
    1743: {
        "person": ["zafer çağlayan | çağlayan", "üzeyir doğan | doğan"],
        "organization": ["türkiye istatistik kurumu | tüik", "merkez bankası | mb", "marbaş menkul değerler"],
        "location": [],
        "flags": [
            "Type mismatch fixed: 'en_bakanı_zafer_cağlayan' was in organization with title; moved to person as 'zafer çağlayan | çağlayan'.",
            "Aliases grouped: 'türkiye istatistik kurumu | tüik' and 'merkez bankası | mb'.",
            "Missing person/organizations added: 'üzeyir doğan | doğan', 'marbaş menkul değerler'.",
        ],
    },
    1461: {
        "person": ["mehmet şimşek | şimşek"],
        "organization": ["maliye bakanlığı | maliye", "vergi denetim kurulu | vdk", "tütün ve alkol piyasası düzenleme kurumu"],
        "location": ["türkiye"],
        "flags": [
            "Title stripped & aliases grouped: 'maliye_bakanı_mehmet_şimşek' and 'bakan_şimşek' merged into 'mehmet şimşek | şimşek'.",
            "Missing organizations and location added.",
        ],
    },
    3613: {
        "person": ["ricardo quaresma | quaresma", "ahmet bulut", "uğur asarlı", "jorge mendes | mendes", "ahmet nur çebi"],
        "organization": ["beşiktaş", "sporting lisbon", "radyospor | radyospor com"],
        "location": ["portekiz", "istanbul"],
        "flags": [
            "Missing persons, organizations and locations added: 'uğur asarlı', 'ahmet nur çebi', 'beşiktaş', 'sporting lisbon', 'radyospor', 'portekiz', 'istanbul'.",
        ],
    },
    4667: {
        "person": ["timo ihamuotila"],
        "organization": ["nokia", "exilion"],
        "location": ["finlandiya"],
        "flags": [
            "Missing entities added: 'timo ihamuotila' (person), 'nokia' (organization), 'finlandiya' (location).",
        ],
    },
    430: {
        "person": ["demir çelik | çelik"],
        "organization": ["bdp", "tbmm", "anka"],
        "location": ["muş"],
        "flags": [
            "Type mismatch fixed: 'Bdp' moved from person to organization.",
            "Missing entities added: 'tbmm', 'anka', 'muş'.",
        ],
    },
    418: {
        "person": ["mehmet bedri gültekin", "ahmet kerim gültekin", "ertan ş"],
        "organization": ["terörle mücadele daire başkanlığı", "maoist komünist partisi | mkp | maoist komünist parti", "devrimci gençlik hareketi | dgh", "işçi partisi", "halk kurtuluş ordusu"],
        "location": ["türkiye", "tunceli", "ankara", "diyarbakır", "izmir"],
        "flags": [
            "Fragmented name fixed: 'ahmet' and 'kerim' replaced with full names 'mehmet bedri gültekin', 'ahmet kerim gültekin', 'ertan ş' (shared surname 'gültekin' kept unambiguous).",
            "Capped at 5 locations in first-mention order ('elazığ' omitted due to 5-entity cap).",
        ],
    },
    860: {
        "person": ["abdullah", "6 muhammed"],
        "organization": ["suudi kraliyet basın ofisi", "aa"],
        "location": ["fas", "suudi arabistan", "cidde", "suriye"],
        "flags": [
            "Type mismatch fixed: 'suudi_arabistan' and 'fas' moved from organization to location (countries acting politically remain locations).",
            "Missing persons/organizations/locations added.",
        ],
    },
    1982: {
        "person": ["james turner | turner", "sarah", "edward petre mears", "vladimir antonov"],
        "organization": ["guardian", "bbc", "uluslararası gazetecilik konsorsiyumu | icij", "turner little", "portsmouth"],
        "location": ["washington", "ingiliz virgin adaları", "irlanda", "yeni zelanda", "ingiltere"],
        "flags": [
            "Cleaned descriptions from organization names ('bbc panaroma programı' -> 'bbc', stripped 'washington merkezli').",
            "Capped at 5 locations in first-mention order ('channel adaları', 'karayipler', 'litvanya' omitted).",
        ],
    },
    2686: {
        "person": ["uğur saatçi", "barış erdenk", "aytuğ dereli", "aylin dinler", "nihat bahar"],
        "organization": ["trabzon devlet tiyatrosu", "trabzon devlet güzel sanatlar galerisi"],
        "location": ["atapark haluk ongan sahnesi", "anadolu", "istanbul"],
        "flags": [
            "Likely error fixed: suffix 'nin' and person 'serdar kurutçu' removed from organization.",
            "Capped at first 5 persons in order of mention ('sibel erdenk', 'serdar kurutçu', 'fatih dokgöz', etc. omitted due to 5-entity cap).",
            "Ambiguity: 'atapark haluk ongan sahnesi' is a physical stage/venue used as a location.",
        ],
    },
    2836: {
        "person": ["senai aksoy | aksoy"],
        "organization": ["art tıp merkezi", "vkv amerikan hastanesi"],
        "location": [],
        "flags": [
            "Title 'dr.' stripped from 'senai aksoy | aksoy'; missing organizations 'art tıp merkezi' and 'vkv amerikan hastanesi' added.",
        ],
    },
    3736: {
        "person": ["aziz yıldırım"],
        "organization": ["ael limassol | ael | ael limassol kulübü", "fenerbahçe | f bahçe"],
        "location": ["güney kıbrıs", "kktc"],
        "flags": [
            "Type mismatch fixed: 'ael' and 'ael_limassol' moved from person to organization and grouped as aliases.",
            "Missing organization 'fenerbahçe | f bahçe' and locations 'güney kıbrıs', 'kktc' added.",
        ],
    },
    2138: {
        "person": ["eivind aarset"],
        "organization": ["gevende", "baykuş müzik", "balbazar"],
        "location": ["garajistanbul", "eskişehir", "istanbul", "katmandu", "amsterdam"],
        "flags": [
            "Likely error fixed: common noun 'sevenleri' removed from organization; 'paris' (only 'parisli' adjective in text) removed from location.",
            "Capped at first 5 locations ('lyon', 'fransa', 'norveç', 'avrupa' omitted). 'garajistanbul' treated as venue/location (or organization).",
        ],
    },
    2768: {
        "person": [],
        "organization": ["devlet tiyatroları | devlet tiyatroları genel müdürlüğü", "bursa devlet tiyatrosu", "istanbul devlet tiyatrosu", "diyarbakır devlet tiyatrosu", "izmir devlet tiyatrosu"],
        "location": ["kahramanmaraş", "gaziantep", "elazığ", "malatya", "balıkesir"],
        "flags": [
            "Type mismatch fixed: cities 'şanlıurfa', 'kahramanmaraş', 'gaziantep' were in organization; moved to location.",
            "Capped at first 5 organizations and first 5 locations in order of mention.",
        ],
    },
    1128: {
        "person": ["dina talat seyid muhammed | dina", "hz muhammed", "hz ali", "hz fatıma", "hasan"],
        "organization": ["el sabah", "el ezher", "newsweek", "kültür bakanlığı"],
        "location": ["mısır"],
        "flags": [
            "Spelling normalized to match text ('dina talat seyid muhammed', 'hz fatıma').",
            "Ambiguity: religious/historical figures ('hz muhammed', 'hz ali', 'hz fatıma', 'hasan', 'hüseyin') appear before contemporary persons ('baha enver muhammed', 'abdülsetta fethi', 'ahmed el subki'); review whether to include religious figures under person cap.",
        ],
    },
    3653: {
        "person": ["lebron james", "dwyane wade", "chris bosh", "deron williams", "kris humpries"],
        "organization": ["miami heat | heat", "brooklyn nets | nets"],
        "location": [],
        "flags": [
            "Type mismatch fixed: 'miami_heat' and 'brooklyn_nets' moved from person to organization.",
            "Hallucinated spelling fixed: 'chase_bosh' -> 'chris bosh'; added 'deron williams' and 'kris humpries'.",
        ],
    },
    1001: {
        "person": ["ali uzun | uzun", "jandos tatiyev | tatiyev"],
        "organization": ["cihan"],
        "location": ["kazakistan", "astana"],
        "flags": [
            "Missing organization 'cihan' and location 'kazakistan' added.",
        ],
    },
    337: {
        "person": ["mehmet sağlam"],
        "organization": ["tbmm | meclis | tbmm genel kurulu", "mhp"],
        "location": [],
        "flags": [
            "Hallucination/typo fixed: 'mehmet sağman' -> 'mehmet sağlam'; 'muhammed sliman mhp' removed from person and 'mhp', 'tbmm' placed in organization.",
        ],
    },
    2003: {
        "person": ["roubini", "nihat ergün | ergün"],
        "organization": ["skytürk360"],
        "location": ["türkiye"],
        "flags": [
            "Missing organization 'skytürk360' and location 'türkiye' added.",
        ],
    },
    4758: {
        "person": ["paul marek | marek"],
        "organization": ["zookeys", "arizona üniversitesi"],
        "location": ["california", "san francisco"],
        "flags": [
            "Type mismatch fixed: 'Paul Marek' moved from organization to person.",
            "Missing locations 'california', 'san francisco' and journal 'zookeys' added.",
        ],
    },
    3412: {
        "person": ["haldun gündoğdu"],
        "organization": ["klinik enteral parenteral nütrisyon derneği | kepan | kepan derneği", "abbott nutrisyon", "beyoğlu belediyesi", "avrupa birliği"],
        "location": ["taksim", "odakule", "beyoğlu", "avrupa", "türkiye"],
        "flags": [
            "Typo fixed: 'Abbott Nutriyon' -> 'abbott nutrisyon'; grouped 'kepan' aliases.",
            "Missing person 'haldun gündoğdu', organizations and locations added.",
        ],
    },
    1525: {
        "person": [],
        "organization": ["aa"],
        "location": [],
        "flags": [
            "Type mismatch fixed: 'Türkiye' (part of survey title 'türkiye emekli profili anketi') removed from organization; agency 'aa' added.",
        ],
    },
    1612: {
        "person": ["obama", "mario draghi | draghi"],
        "organization": ["ab", "abd merkez bankası", "avrupa komisyonu", "avrupa merkez bankası | ecb", "imkb"],
        "location": ["almanya", "abd", "avrupa", "euro bölgesi"],
        "flags": [
            "Typo fixed: 'ebd' -> 'avrupa merkez bankası | ecb', 'komisyonu' -> 'avrupa komisyonu'.",
            "Missing persons ('obama', 'mario draghi'), organizations and locations added.",
        ],
    },
    2794: {
        "person": ["howard phillips lovecraft | lovecraft"],
        "organization": ["ithaki yayınları | ithaki"],
        "location": ["antarktika", "rhode island", "providence"],
        "flags": [
            "Likely error fixed: generic noun 'universite' removed from organization.",
            "Missing person 'howard phillips lovecraft' and locations 'antarktika', 'rhode island', 'providence' added.",
        ],
    },
    2734: {
        "person": ["özcan deniz", "fahriye evcen", "ata demirer", "hakan akgül", "ozan açıktan"],
        "organization": ["box office türkiye"],
        "location": [],
        "flags": [
            "Typos fixed: 'hakan_äkgül' -> 'hakan akgül', 'ozan_acıkta' -> 'ozan açıktan'.",
            "First-5 person order enforced: 'fahriye evcen' appears 2nd in text before 'ata demirer' (so 'turgut özakman' is 7th after 'tolga çevik').",
        ],
    },
    2722: {
        "person": ["peter jackson", "claude levi strauss", "julien greimas", "vladimir iakovlevitch propp", "sebla kutsal"],
        "organization": [],
        "location": ["abd", "hollywood"],
        "flags": [
            "All entities were missed by historical model; added 5 persons and 2 locations ('orta_dünya' is fictional, excluded).",
        ],
    },
    3995: {
        "person": ["barbaros mutlu kadıoğlu", "dursun şen", "murat dokuyucu", "mustafa koçoğlu", "ali pektaş"],
        "organization": ["hentbol federasyonu", "çankaya belediyesi anka | çankaya belediyesi anka spor kulübü | çankaya belediyesi", "ardeşen gençlik spor kulübü | ardeşenspor", "üsküdar belediyesi spor kulübü", "orduspor kulübü"],
        "location": [],
        "flags": [
            "Type/hallucination fixed: 'anka ardeşen_gençlik spor_kulübü' was in person; 'izzet dursun' -> 'dursun şen'; 'genel merkezi' removed from location.",
            "Capped at first 5 organizations in order of mention in text.",
        ],
    },
    101: {
        "person": ["recep akdağ", "aytuğ atıcı | atıcı"],
        "organization": ["chp", "ak parti | akp", "tbmm", "sosyal güvenlik kurumu", "sağlık bakanlığı"],
        "location": ["mersin"],
        "flags": [
            "Untranslated hallucination fixed: 'health_minister_recep_akdağ' -> 'recep akdağ'; stripped title from 'aytuğ atıcı'.",
            "Added 5 organizations (capped; 'anka' is 6th) and location 'mersin'.",
        ],
    },
    393: {
        "person": ["atatürk", "şahin"],
        "organization": ["içişleri bakanlığı"],
        "location": [],
        "flags": [
            "Type mismatch fixed: 'İçişleri Bakanlığı' moved from person to organization; generic noun 'Valiliklere' removed.",
            "Ambiguity: 'atatürk' appears in 'atatürk anıtı' / '10 kasım atatürk ü anma'; minister 'şahin' (İdris Naim Şahin) is mentioned by surname only.",
        ],
    },
    1447: {
        "person": ["mustafa satılmış | satılmış"],
        "organization": [],
        "location": ["akkuyu | akkuyu nükleer santrali", "mersin"],
        "flags": [
            "Malformed entry 'satılmış çed sürecinin' removed; grouped 'mustafa satılmış | satılmış'.",
            "Added locations 'akkuyu' and 'mersin'.",
        ],
    },
    1088: {
        "person": ["lilian king | king"],
        "organization": ["colonial coin collectors club", "newsday", "aa"],
        "location": ["abd", "massachusetts", "maryland", "baltimore", "new york"],
        "flags": [
            "Stripped suffix/location prefix from organizations ('newsday', 'colonial coin collectors club').",
            "Added person 'lilian king | king', agency 'aa', and first 5 locations ('east hampton' is 6th).",
        ],
    },
    726: {
        "person": ["nuri el maliki | maliki", "adnan enver | enver", "saddam hüseyin | saddam", "vladimir putin | putin"],
        "organization": ["stk federasyonu", "rusya başkonsolosluğu | erbil başkonsolosluğu"],
        "location": ["bağdat", "rusya", "irak", "erbil"],
        "flags": [
            "Fused name fixed: 'Enver Saddam' in historical prediction came from 'adnan enver saddam döneminde'; separated into 'adnan enver | enver' and 'saddam hüseyin | saddam'.",
            "Added organizations and locations.",
        ],
    },
    3677: {
        "person": ["kerem gönlüm", "lucas", "farmar", "dusko savanovic"],
        "organization": ["efes | a efes | lacivert beyazlılar", "banvit"],
        "location": ["bandırma"],
        "flags": [
            "Type mismatch fixed: 'Efes' and nickname 'Lacivert Beyazlılar' moved from person to organization.",
            "Added 'dusko savanovic', 'banvit', and 'bandırma'.",
        ],
    },
    1576: {
        "person": ["dj geveze", "yaşar arslan | arslan", "emre sayın"],
        "organization": ["turkcell", "apple"],
        "location": ["suadiye", "türkiye"],
        "flags": [
            "Added missing persons ('dj geveze', 'yaşar arslan', 'emre sayın'), organization 'apple', and locations 'suadiye', 'türkiye'.",
        ],
    },
    3970: {
        "person": ["nedim türkmen | türkmen"],
        "organization": ["orduspor kulübü | orduspor", "sivasspor"],
        "location": ["istanbul", "ordu"],
        "flags": [
            "Type mismatch fixed: 'sivasspor' moved from person to organization; added 'orduspor kulübü | orduspor' and locations 'istanbul', 'ordu'.",
        ],
    },
    4786: {
        "person": [],
        "organization": ["digitimes", "acer", "asus", "hp", "samsung"],
        "location": ["orta amerika", "orta asya"],
        "flags": [
            "Capped at first 5 organizations ('sony', 'toshiba' omitted); added locations 'orta amerika', 'orta asya'.",
        ],
    },
    3480: {
        "person": [],
        "organization": ["amerika travma cerrahisi derneği", "abd savunma bakanlığı | pentagon"],
        "location": ["hawaii", "kauai"],
        "flags": [
            "Untranslated hallucination fixed: 'americansurgeryassociation' -> 'amerika travma cerrahisi derneği'.",
            "Added locations 'hawaii' and 'kauai'.",
        ],
    },
    2487: {
        "person": ["alfred nobel", "jean paul sartre", "henry kissinger", "le duc tho", "adolf hitler"],
        "organization": [],
        "location": ["stockholm", "vietnam", "abd", "almanya", "sovyetler birliği"],
        "flags": [
            "Type mismatch fixed: 'fransız' (adjective) removed; 'abd' and 'sovyetler_birliği' moved from organization to location.",
            "Added first 5 persons and first 5 locations in order of mention.",
        ],
    },
    1830: {
        "person": ["michael bloomberg | bloomberg", "chris christie | christie", "charkes hynes", "andrew cuomo"],
        "organization": [],
        "location": ["new york", "long island", "new jersey", "brooklyn"],
        "flags": [
            "Type mismatch fixed: all 3 persons with titles were in organization; moved to person with titles stripped and added 'andrew cuomo'.",
            "Added locations 'new york', 'long island', 'new jersey', 'brooklyn'.",
        ],
    },
    3814: {
        "person": ["andy murray | murray", "novak djokovic | djokovic", "tomas berdych | berdych", "jo wilfried tsonga | tsonga"],
        "organization": [],
        "location": ["ingiltere", "londra", "o2 arena", "wimbledon"],
        "flags": [
            "Added missing locations 'ingiltere', 'londra', 'o2 arena', 'wimbledon'.",
        ],
    },
    3072: {
        "person": [],
        "organization": ["emniyet genel müdürlüğü", "türkiye psikiyatri derneği", "türkiye şizofreni dernekleri federasyonu"],
        "location": ["türkiye", "abd"],
        "flags": [
            "Added missing locations 'türkiye' and 'abd'.",
        ],
    },
    1134: {
        "person": [],
        "organization": [],
        "location": ["suudi arabistan", "irak", "kerbela", "arar sınır kapısı"],
        "flags": [
            "Type mismatch & typo fixed: 'irak' and 'suudi-arabistan' moved from organization to location; 'kerbeli' -> 'kerbela'; added 'arar sınır kapısı'.",
        ],
    },
    4292: {
        "person": [],
        "organization": [],
        "location": ["abd", "finlandiya"],
        "flags": [
            "Type mismatch fixed: 'Abd' and 'Finlandiya' moved from organization to location.",
        ],
    },
    2854: {
        "person": ["steven woolf | woolf"],
        "organization": ["bilimler akademisi", "tıp kurumu"],
        "location": ["avustralya", "kanada", "japonya"],
        "flags": [
            "Added missing person 'steven woolf | woolf', organization 'bilimler akademisi', and locations 'avustralya', 'kanada', 'japonya'.",
        ],
    },
    809: {
        "person": ["recep tayyip erdoğan | erdoğan", "angela merkel", "mahmut gürer"],
        "organization": [],
        "location": ["berlin", "türkiye", "almanya", "bonn", "suriye"],
        "flags": [
            "Added reporter 'mahmut gürer' and first 5 locations ('ankara' dateline is 6th).",
        ],
    },
    1579: {
        "person": ["remzi gür"],
        "organization": ["tasarruf mevduatı sigorta fonu | tmsf", "adabank | adabank aş", "resmi gazete", "rekabet kurumu", "vakıflar bankası"],
        "location": ["türkiye", "istanbul"],
        "flags": [
            "Fixed typo/fusion in organization ('tmsf adabankı', 'tasarruf mevduatı sigorta fonsu'); added person 'remzi gür', organizations and locations.",
        ],
    },
    4711: {
        "person": ["miriam makeba | makeba | afrika ana", "mandela", "harry belafonte", "stokely carmichael", "roberto saviano"],
        "organization": ["google", "birleşmiş milletler | birleşmiş milletler genel kurulu"],
        "location": ["johannesburg", "güney afrika", "abd", "gine", "italya"],
        "flags": [
            "Type mismatch fixed: 'google' moved from person to organization; 'apartheid' (political system) removed from person.",
            "Added 'harry belafonte', 'roberto saviano', 'birleşmiş milletler', and locations.",
        ],
    },
    1173: {
        "person": ["muhammed ikbal | ikbal"],
        "organization": ["moro islami kurtuluş cephesi | mikc", "aa"],
        "location": ["filipinler"],
        "flags": [
            "Type mismatch fixed: news agency 'aa' moved from person to organization; added 'moro islami kurtuluş cephesi | mikc' and 'filipinler'.",
        ],
    },
    3214: {
        "person": ["robin franklin | franklin", "may hay | hay"],
        "organization": ["cambridge üniversitesi | cambridge üniversitesi veterinerlik fakültesi", "wellcome trust mrc kök hücre enstitüsü", "brain"],
        "location": [],
        "flags": [
            "Fused breed fixed: 'May Hay Dachshund' -> 'may hay | hay' ('dachshund' is the dog breed; 'jasper' is a dog, excluded).",
            "Added organizations 'cambridge üniversitesi', 'wellcome trust mrc kök hücre enstitüsü', 'brain'.",
        ],
    },
    741: {
        "person": ["visam el hasan | hasan"],
        "organization": ["hizbullah", "aa"],
        "location": ["lübnan", "beyrut", "sayda", "kuturmaya", "kaskas"],
        "flags": [
            "Type/suffix errors fixed: 'hasan a' merged as alias; 'hizbullah' moved from person to organization; 'sayda şehrine' moved to location as 'sayda'.",
            "Cleaned descriptive location phrases and capped at first 5 locations ('dahye', 'trablusşam', 'cebel muhsin', 'tibbane' omitted).",
        ],
    },
    4660: {
        "person": [],
        "organization": ["twitter"],
        "location": ["türkiye"],
        "flags": [
            "Added missing location 'türkiye'. ('blackberry' and 'android' are products/platforms).",
        ],
    },
    1429: {
        "person": [],
        "organization": [],
        "location": [],
        "flags": [
            "Likely error fixed: generic common noun 'bankalar' removed from organization (no named entities in text).",
        ],
    },
    2311: {
        "person": ["kürşat kayral | kayral", "mahir çayan", "nazım hikmet", "saidi nursi", "abdürrahim karakoç"],
        "organization": ["ankara emniyet müdürlüğü", "ankara devlet güvenlik mahkemeleri", "ankara cumhuriyet başsavcılığı", "içişleri bakanlığı"],
        "location": ["ankara"],
        "flags": [
            "Type mismatch fixed: 'ankara emniyet müdürlüğü' moved from person to organization; stripped title from 'kürşat kayral'.",
            "Added first 5 persons ('aziz nesin', 'karl marx', 'engels' omitted due to cap) and organizations/location.",
        ],
    },
    401: {
        "person": ["ali yavuz | yavuz", "bülent arınç | arınç"],
        "organization": ["şehitler derneği", "pkk", "dha"],
        "location": ["fransa", "kayseri"],
        "flags": [
            "Type mismatch fixed: 'sayın_arınç' and 'Bülent Arınç' moved from organization to person as 'bülent arınç | arınç'.",
            "Added 'ali yavuz | yavuz', organizations ('şehitler derneği', 'pkk', 'dha'), and locations ('fransa', 'kayseri').",
        ],
    },
    2996: {
        "person": ["ali baki | baki"],
        "organization": ["karadeniz teknik üniversitesi | ktü"],
        "location": ["türkiye"],
        "flags": [
            "Added missing organization 'karadeniz teknik üniversitesi | ktü' and location 'türkiye'.",
        ],
    },
    3508: {
        "person": ["mesut özil | mesut"],
        "organization": ["real madrid", "facebook"],
        "location": ["ispanya", "gelsenkirchen"],
        "flags": [
            "Type mismatch fixed: 'Real Madrid' moved from person to organization.",
            "Added 'facebook' and locations 'ispanya', 'gelsenkirchen'.",
        ],
    },
    4325: {
        "person": [],
        "organization": ["nokia", "the guardian"],
        "location": [],
        "flags": [],
    },
    1229: {
        "person": [],
        "organization": ["müslüman kardeşler | müslüman kardeşler teşkilatı | ihvan", "aa", "mena"],
        "location": ["mısır", "kahire"],
        "flags": [
            "Cleaned 'aa muhabir' -> 'aa'; grouped 'müslüman kardeşler | ihvan'; added 'mena' and 'kahire'.",
        ],
    },
    1197: {
        "person": ["cemal ed devl", "ahmet", "abdullah", "ahmet davutoğlu"],
        "organization": ["cihan haber ajansı | cihan"],
        "location": ["israil", "gazze", "en nasr mahallesi", "türkiye", "istanbul"],
        "flags": [
            "Fused token fixed: 'Ahmed Türkiye' came from 'ahmet_türkiye de'; split into person 'ahmet' and location 'türkiye'.",
            "Added 'abdullah', 'ahmet davutoğlu', 'cihan haber ajansı | cihan', and first 5 locations ('filistin', 'yağfe' omitted).",
        ],
    },
    4534: {
        "person": [],
        "organization": ["pnas"],
        "location": [],
        "flags": [
            "Likely error fixed: descriptive phrase 'Amerikalı bilim adamları' replaced with journal 'pnas'.",
        ],
    },
    165: {
        "person": ["adnan keskin | keskin", "kemal kılıçdaroğlu"],
        "organization": ["chp | chp parti meclisi | parti meclisi | pm", "ak parti", "cihan"],
        "location": ["siirt", "diyarbakır"],
        "flags": [
            "Turkish character fixed: 'kemal_kilicdaroglu' -> 'kemal kılıçdaroğlu'; added organizations and locations.",
        ],
    },
    3140: {
        "person": ["gül yıldırım | yıldırım"],
        "organization": [],
        "location": [],
        "flags": [
            "Title 'dr.' stripped from 'gül yıldırım | yıldırım'.",
        ],
    },
    3207: {
        "person": ["osman yaşar öz | öz", "ahmet kaplan"],
        "organization": ["alsancak nevvar salih işgören hastanesi", "türk kamu hastaneler birliği"],
        "location": ["ege"],
        "flags": [
            "Duplicate/split person fixed: 'dr öz' and 'dr osman yaşar' are the same person ('uzm dr osman yaşar öz'); merged into 'osman yaşar öz | öz'.",
            "Added organizations and location 'ege'.",
        ],
    },
    2676: {
        "person": ["orhan pamuk | pamuk", "jacques tardi | tardi", "louis aragon", "albert camus", "claude monet"],
        "organization": ["le parisien", "cihan"],
        "location": ["fransa"],
        "flags": [
            "Type mismatch fixed: 'pamuk' and 'orhan_pamuk' were in organization; moved to person and merged; removed generic 'fransız yazar'.",
            "Capped at first 5 persons ('hector berlioz', 'jean paul sartre', 'simone de beauvoir', 'napoleon bonaparte' omitted).",
        ],
    },
    3749: {
        "person": ["quaresma | q7", "ibrahim güneş", "alex"],
        "organization": ["beşiktaş", "fener", "cim bom"],
        "location": ["akaretler"],
        "flags": [
            "Hallucinated surname fixed: 'İbrahim Güzey' -> 'ibrahim güneş'; added 'quaresma | q7', organizations and location 'akaretler'.",
        ],
    },
    294: {
        "person": [],
        "organization": ["ak parti"],
        "location": ["almanya"],
        "flags": [
            "Unsupported entity fixed: 'Türkiye' does not appear in text (only 'türk'); moved focus to location 'almanya'.",
        ],
    },
    2075: {
        "person": ["murat yalçıntaş | yalçıntaş"],
        "organization": ["istanbul ticaret odası | ito", "tbmm | meclis"],
        "location": [],
        "flags": [
            "Duplicate/titled person entries cleaned: 'murat yalçıntaş | yalçıntaş' separated from 'istanbul ticaret odası | ito'; added 'tbmm | meclis'.",
        ],
    },
    2547: {
        "person": ["madonna", "beyonce"],
        "organization": ["disney", "istanbul çocuk tiyatrosu", "c + c music factory", "baha men", "pixar"],
        "location": ["trump towers mall", "türkiye"],
        "flags": [
            "Moved venue 'trump towers mall' from organization to location; added persons 'madonna', 'beyonce', organizations and 'türkiye' (fictional characters excluded).",
        ],
    },
    3370: {
        "person": ["ülkü bayındır"],
        "organization": ["izmir kent hastanesi"],
        "location": [],
        "flags": [
            "Guideline fix: 'İzmir' only appears inside 'izmir kent hastanesi' (nested organization location not split); added 'ülkü bayındır' and 'izmir kent hastanesi'.",
        ],
    },
    4610: {
        "person": [],
        "organization": ["burger king", "twitter", "mcdonald s"],
        "location": [],
        "flags": [
            "Normalized 'mcdonald s' to match exact text surface form; added 'twitter'.",
        ],
    },
    78: {
        "person": ["ekrem erdem | erdem", "menderes", "erdal düzgün"],
        "organization": ["ak parti", "has parti"],
        "location": ["atatürk kültür sarayı", "karadeniz", "akdeniz", "türkiye", "tokat"],
        "flags": [
            "Merged duplicate 'erdem' and 'ekrem erdem'; added 'menderes', 'erdal düzgün', organizations 'ak parti', 'has parti', and locations.",
        ],
    },
    4319: {
        "person": [],
        "organization": ["samsung"],
        "location": [],
        "flags": [],
    },
    2829: {
        "person": ["saim kerman | kerman"],
        "organization": ["sağlık bakanlığı", "interpol", "türkiye ilaç ve tıbbi cihaz kurumu", "bilgi teknolojileri kurumu", "radyo televizyon üst kurulu | rtük"],
        "location": [],
        "flags": [
            "Type mismatch fixed: 'saim kerman' moved from organization to person; removed non-entity 'takip_sistemi'.",
            "Capped at first 5 organizations ('gümrük ve ticaret bakanlığı', 'reklam kurulu' omitted).",
        ],
    },
    4811: {
        "person": ["jani radebaugh | radebaugh"],
        "organization": ["abd ulusal havacılık ve uzay dairesi | nasa", "brigham young üniversitesi"],
        "location": ["mısır", "nil nehri | nil"],
        "flags": [
            "Translated name fixed: 'Brigham Young University' -> 'brigham young üniversitesi' (Turkish form in text); grouped 'nasa' alias; added 'jani radebaugh' and terrestrial locations.",
        ],
    },
    977: {
        "person": ["celal talabani | talabani", "ali xeydan | xeydan | eli xeydan", "nuri el maliki | maliki", "adnan müfti | müfti"],
        "organization": ["bölgesel kürt yönetimi", "kürdistan yurtseverler birliği | kyb", "dicle operasyon birliği | dicle operasyon gücü", "irak ordusu"],
        "location": ["irak", "kuzey irak", "kerkük", "diyala", "selahaddin"],
        "flags": [
            "Added 'adnan müfti', organizations, and locations.",
        ],
    },
    2392: {
        "person": ["mark rothko | rothko", "jackson pollock", "francis bacon", "willem de kooning", "andy warhol"],
        "organization": ["the new york times", "sotheby s | sotheby s müzayede evi", "manhattan bölge mahkemesi", "sanat enstitüsü", "christie s | christie s müzayede evi"],
        "location": ["kamboçya", "new york", "chicago"],
        "flags": [
            "Matched exact text surface form for 'sotheby s' and 'christie s'; added 5 artists, organizations, and locations.",
        ],
    },
    1078: {
        "person": ["visam el hasan", "necip mikati | mikati", "fuad sinyora | sinyora"],
        "organization": ["14 mart grubu", "müstakbel hareketi", "aa"],
        "location": ["lübnan", "beyrut", "suriye"],
        "flags": [
            "Added missing person 'necip mikati', organizations, and locations.",
        ],
    },
    3575: {
        "person": ["tomas berdych", "radek stepanek", "lukas rosol", "ivo minar", "jaroslav navratil"],
        "organization": ["ispanya", "çek cumhuriyeti | çekler", "çekoslovakya", "arjantin", "tr eurosport com"],
        "location": ["prag"],
        "flags": [
            "Type mismatch fixed: 'davis_kupası' (tournament event) removed from person; added 'jaroslav navratil' (5th person; 'rafael nadal' is 6th).",
            "Ambiguity: 'ispanya', 'çek cumhuriyeti', 'çekoslovakya', 'arjantin' act as Davis Cup national teams (organization per guideline).",
        ],
    },
    1274: {
        "person": ["denizhan murat üresin | murat", "piet van dijk"],
        "organization": ["amsterdam cosmicus montesorri lisesi", "cihan"],
        "location": ["hollanda"],
        "flags": [
            "Added missing organizations 'amsterdam cosmicus montesorri lisesi', 'cihan' and location 'hollanda'.",
        ],
    },
    3472: {
        "person": ["rıza dündar", "fuat kızılay | kızılay"],
        "organization": ["sağlık bakanlığı", "mardin devlet hastanesi"],
        "location": ["türkiye", "güneydoğu anadolu bölgesi | güneydoğu anadolu | güneydoğu", "mardin"],
        "flags": [
            "Type mismatch fixed: 'dr rıza dündar' moved from organization to person (title stripped); added 'fuat kızılay', 'sağlık bakanlığı', and locations.",
        ],
    },
    117: {
        "person": ["recep tayyip erdoğan | erdoğan", "hale tuana hançerkıran | hali tuana hançerkıran | tuana"],
        "organization": ["ak parti", "turhan fevzioğlu ilköğretim okulu", "meclis"],
        "location": [],
        "flags": [
            "Type mismatch fixed: 'Turhan Feyzioglu' (part of 'turhan fevzioğlu ilköğretim okulu') moved from person to organization.",
            "Normalized Turkish characters and grouped aliases for 'erdoğan' and 'tuana'.",
        ],
    },
    545: {
        "person": ["erdoğan", "bülent tezcan", "mehmet şimşek", "deniz baykal", "oktay ekşi"],
        "organization": ["meclis | tbmm | tbmm genel kurulu", "chp", "tbmm plan ve bütçe komisyonu", "darbeleri araştırma komisyonu", "aa"],
        "location": ["aydın"],
        "flags": [
            "Added first 5 persons (many more politicians follow in text), 5 organizations, and location 'aydın'.",
        ],
    },
    1534: {
        "person": ["mehmet yiğiner"],
        "organization": ["maliye bakanlığı", "ankara umum otomobilciler ve şoförler esnaf odası"],
        "location": ["ankara", "türkiye"],
        "flags": [
            "Added missing organizations and locations 'ankara', 'türkiye'.",
        ],
    },
    3713: {
        "person": ["obi mikel | john obi mikel | obi | mikel", "mark clattenburg | clattenburg", "roberto di matteo | di matteo", "eddie newton", "john terry | terry"],
        "organization": ["m united", "chelsea | chelsea kulübü", "daily mirror", "futbol federasyonu | fa"],
        "location": [],
        "flags": [
            "Likely error fixed: quote 'ayaklarını kıracağım', description 'Mavilerin Nijeryalı Yıldızı', and 'Ada Da Chelsea' removed from person.",
            "Capped at first 5 persons ('juan mata' is 6th) and added organizations.",
        ],
    },
    472: {
        "person": ["oğuz kaan salıcı | salıcı", "levent kırca | levent kirca", "ismet inönü", "mustafa kemal atatürk | atatürk", "kemal kılıçdaroğlu"],
        "organization": ["cumhuriyet halk partisi | chp", "akp", "sanatçılar girişimi", "işçi partisi"],
        "location": ["istanbul", "bostancı gösteri merkezi", "maçka", "türkiye"],
        "flags": [
            "Added missing persons ('ismet inönü', 'mustafa kemal atatürk', 'kemal kılıçdaroğlu'), organizations, and locations.",
        ],
    },
    2998: {
        "person": ["yüksel kaş | kaş"],
        "organization": [],
        "location": [],
        "flags": [
            "Type mismatch fixed: 'dr yüksel kaş' moved from organization to person as 'yüksel kaş | kaş'.",
        ],
    },
    2665: {
        "person": ["muhsin ertuğrul", "rutkay aziz", "taner barlas", "ümit denizer", "sokrates"],
        "organization": ["perdeci oyuncuları", "aysa prodüksiyon tiyatrosu", "beş yüzler meclisi", "engizisyon"],
        "location": ["atina", "roma", "boston"],
        "flags": [
            "Capped at first 5 persons ('galileo', 'sacco', 'vanzetti', 'metin deniz', 'bülent işcan' omitted); added organizations and locations.",
        ],
    },
    1409: {
        "person": [],
        "organization": ["eurogroup", "imkb", "tcmb", "dallas fed"],
        "location": ["avrupa", "yunanistan", "ispanya", "abd", "almanya"],
        "flags": [
            "Type mismatch fixed: 'Abd', 'Yunanistan', 'İspanya' moved from organization to location; 'Dow Jones' (stock index) removed.",
            "Added 'imkb', 'tcmb', 'dallas fed' and capped at first 5 locations ('fransa', 'türkiye' omitted).",
        ],
    },
    3618: {
        "person": ["oğuzhan | fabregas oğuzhan", "fernandes", "samet aybaba | aybaba", "veli", "necip"],
        "organization": ["beşiktaş", "trabzon", "kasımpaşa", "arsenal"],
        "location": ["avrupa"],
        "flags": [
            "Fused/suffixed names fixed: 'Oguzhan Dan' -> 'oğuzhan | fabregas oğuzhan'; 'Samet Aybaba Kasimpasa' split into person 'samet aybaba' and organization 'kasımpaşa'.",
            "Added 'fernandes', 'veli', organizations and location 'avrupa'.",
        ],
    },
    4485: {
        "person": ["abdullah gül | gül", "hayrünnisa"],
        "organization": ["instagram", "youtube", "flickr", "facebook", "twitter"],
        "location": ["çankaya köşkü", "türkiye", "afganistan", "pakistan", "adıyaman"],
        "flags": [
            "Stripped title from 'cumhurbaşkanı_gül' and merged with 'abdullah gül | gül'; added 'hayrünnisa'.",
            "Capped at first 5 organizations ('trt', 'türk silahlı kuvvetleri' omitted) and first 5 locations ('kars', 'ankara', 'doğubeyazıt', 'tarabya' omitted).",
        ],
    },
    2379: {
        "person": ["claude monet | monet", "philippe piguet | piguet"],
        "organization": ["sabancı üniversitesi sakıp sabancı müzesi | sakıp sabancı müzesi", "fransız kültür merkezi"],
        "location": ["giverny"],
        "flags": [
            "Corrupted/wrong tokens fixed: removed 'toruşa yi', '˧abanci ľli', '(fr)'; moved museum from person to organization; added 'fransız kültür merkezi' and 'giverny'.",
        ],
    },
    2462: {
        "person": [],
        "organization": ["gripin"],
        "location": ["jolly joker"],
        "flags": [
            "Ambiguity: 'jolly_joker' ('jolly_joker sahnesinde') moved from organization to location as a concert venue (could also be considered an organization).",
        ],
    },
    543: {
        "person": ["mehmet ali kayacı | kayacı", "kemal kılıçdaroğlu | kılıçdaroğlu", "mevlana"],
        "organization": ["chp", "konya tv"],
        "location": ["konya"],
        "flags": [
            "Added 'mevlana', organizations 'chp', 'konya tv', and location 'konya'.",
        ],
    },
}
