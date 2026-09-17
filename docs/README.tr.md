<p align="center">
  <img src="../assets/icon.png" alt="KodYazar Client" width="96" height="96">
</p>

<p align="center">
  <strong>KY-GamePlayer — KodYazar Client</strong><br/>
  Masaüstü Discord paneli: Rich Presence, 24 bin oyunluk katalog, görevler, HypeSquad, science saatleri.
</p>

<p align="center">
  <a href="../README.md">English</a> ·
  <a href="./README.tr.md">Türkçe</a>
</p>

```
Author : Batuhan (KodYazicam)
Project: KY-GamePlayer (KodYazar Client)
Source : https://github.com/KodYazicam/KY-GamePlayer
```

**KYAL-1.0** — kullanmak ve değiştirmek serbest. Atıf **zorunlu**: LICENSE, bu dosya, bu kodu dağıtan her ürün. Örnek: `Powered by KY-GamePlayer — KodYazicam`.

PyPI’de yok. Repoyu klonla. Discord Stable / Canary / PTB / Vesktop / Vencord — **Linux, Windows, macOS**.

Bu bir **yerel kullanıcı istemcisi**. Bu makinedeki açık Discord oturumunun token’ını okur; IPC ve API v9 ile Discord’a gider. KodYazicam sunucusuna kimlik göndermez. Resmi olmayan kullanıcı-token otomasyonu Discord kurallarını ihlal edebilir — risk sende. [`../SECURITY.md`](../SECURITY.md).

İngilizce kök README ile aynı ürün. Ayrıntılı kontrol listesi: [`features.md`](features.md). Mimari: [`architecture.md`](architecture.md). Kurulum: [`install.md`](install.md). Yol haritası: [`roadmap.md`](roadmap.md).

---

## Bu nedir (ve ne değildir)

**Evet:** PySide6 masaüstü uygulaması. KodYazar Discord sunucusuna katıldıktan sonra:

- Discord’un detectable katalogundan (**24 314** oyun, `games.json`) Rich Presence basar
- Çalışan `.exe` / ikiliyi tarayıp Playing yapar
- Rastgele oyun, metin döngüsü, saat aralığı, ek IPC pin
- HypeSquad evine girer/çıkar, profil görünürlüğü, özel durum, clan etiketi
- Kabul edilmiş Quest’leri bitirir (video tick / oynama-yayın heartbeat)
- `POST /science` ile saat / oynandı sayaçlarına paket basar

**Hayır:** bot, SaaS, oyun başlatıcı, hile, Staff/Partner/Bug Hunter rozeti basıcı. Hediye/Nitro görselleri katalogdur, kilit açmaz.

---

## Özellik yüzeyi (1.0.0)

| Alan | Ne var |
| --- | --- |
| Kabuk | Koyu Fusion, tepsi, tek örnek, TR/EN, açılışta başlat |
| Kilit | Discord/Vesktop Local Storage’tan token; yapıştırma; sunucu üyeliği şart |
| Oyunlar | Arama, tema/mağaza/OS/ikon/kapak/overlay, favori, playlist, hariç, ağırlık |
| RPC | Playing…Competing, görsel, party, buton **veya** secret, flag |
| Algıla | 5 sn süreç tarama; Proton/Wine; PID |
| Random | Ağırlıklı havuz, son N’yi tekrarlama, Ctrl+R |
| Ekler | En fazla 8 ek IPC (Vesktop yığabilir; resmi Discord tek Playing) |
| Döngü / zaman | Satır kareleri; saat penceresi; idle temizle; yeniden bağlan |
| Science | Saat veya “oynandı 1 dk”; batch/gecikme/jitter; DPAPI |
| Görev | Tara, enroll, video 1 sn, heartbeat ~20 sn, claim |
| Rozet | HypeSquad; sahip olunan flag; hediye/Nitro katalog |
| Gizlilik | Özel / kısıtlı / herkese açık |
| Hesap | Özel durum, clan, entitlement sayısı |
| Paket | `kurulum.bat` / `windows.bat`; PyInstaller |

Her kontrol: [`features.md`](features.md).

---

## Gereksinimler

- Python **3.11+**
- `PySide6>=6.6,<7`
- `cryptography>=42` (çerez `v10`/`v11`)
- IPC için açık Discord masaüstü
- [KodYazar Client](https://discord.gg/rS42FCPfKZ) üyeliği (`1549516395010854912`)

Chrome App-Bound `v20` çözülmez; gerekirse çerezi yapıştır.

---

## Kurulum ve ilk açılış

```bash
git clone https://github.com/KodYazicam/KY-GamePlayer.git
cd KY-GamePlayer
python3 -m pip install -r requirements.txt
python3 run.py
```

Windows:

- **Release zip:** [Releases](https://github.com/KodYazicam/KY-GamePlayer/releases) → klasörün **hepsini** aç → `KodYazar\KodYazar.exe` (`_internal` yanında kalsın). SmartScreen uyarabilir; aşağıya bak.
- **Kaynak:** bir kez `kurulum.bat`, sonra `windows.bat`.
- **Yerel EXE:** `packaging\windows\build.bat` → `dist\KodYazar\KodYazar.exe`.

macOS: aynı pip + `run.py`.

İlk açılış: Discord açık → sunucuya katıl → bu program → kilit token’ı okur → üyelik doğrulanınca sekmeler.

Ayrıntı: [`install.md`](install.md).

---

## Windows EXE ve antivirüs

GitHub’daki zip **imzasız bir PyInstaller klasörü**. Microsoft Store uygulaması değil. Windows bu yayımcıyı hiç görmediği için SmartScreen “Windows PC’nizi korudu” der veya Defender karantinaya atar. Bu tür derlemelerde normal. “Zararlıdır” demek değil; “yüzde yüz temizdir” demek de değil.

Paketlenmiş exe’ye güvenmek istemiyorsan zip’i indirme. Repoyu klonla, `python run.py` veya `kurulum.bat` / `windows.bat` çalıştır. Aynı program, paketleyici yok.

### VirusTotal ne dedi (v1.0.0, 17 Eyl 2026)

Zip ve `KodYazar.exe` **ayrı** tarandı:

| İndirdiğin şey | Skor | Link |
| --- | --- | --- |
| Zip | **0 / 66** | [analiz](https://www.virustotal.com/gui/file-analysis/Y2ZmZjE3NmQ3NGI2ODAyYTM4MDVjOTE5YjVkY2I1ZTk6MTc4OTY3NjgwNw==/detection) |
| İçindeki `KodYazar.exe` | **3 / 65** | [tespit](https://www.virustotal.com/gui/file/aa7cd98bba263e8ac8948b66137352f88310f8eebac1ad512d00e12b21f62595/detection) · [davranış](https://www.virustotal.com/gui/file/aa7cd98bba263e8ac8948b66137352f88310f8eebac1ad512d00e12b21f62595/behavior) |

**Zip’te 0/66, exe’nin temiz olduğu anlamına gelmez.** VirusTotal kutuyu baktı. Windows PE’ye bakar. Önemli satır exe satırı.

Exe’deki üç işaret:

1. **Microsoft** — `Trojan:Win32/Wacatac.B!ml`  
   `!ml` = makine öğrenmesi, elle yazılmış imza değil. Microsoft bunu imzasız / paketlenmiş programlara sık yapıştırır. “KodYazar = Wacatac” demek değil; genel bir kova.
2. **Arctic Wolf** — `Unsafe` (aile adı yok)
3. **SecureAge** — `Malicious` (aile adı yok)

Kaspersky, ESET, Bitdefender, Malwarebytes, CrowdStrike, ClamAV, Avast, Sophos, Symantec **işaretlemedi**. VirusTotal’ın başlıktaki “trojan” kelimesi bu üç satırın toplanması.

Sonra sandbox çalıştırdı (CAPE ve Zenbox). Asıl bakılacak yer burası:

- ekstra dosya bırakmadı
- ağa çıkmadı
- IDS / Sigma yok
- tek süreç `KodYazar.exe`

Statik motorların “garip” dediği şey **overlay**: PE’nin sonuna yapışmış ~1,8 MB yüksek entropili veri (entropi ~8,0). PyInstaller Python yükünü böyle taşır. Heuristik “paketli / gizlenmiş” deyip durur. PE derleme saati 17 Eyl 2026 19:26 UTC — GitHub Actions’ın derlediği dakika.

Byte’ları kendin doğrula: [`HASHES-v1.0.0.md`](HASHES-v1.0.0.md).

### Windows hâlâ kesiyorsa

1. Yapabiliyorsan kaynaktan çalıştır (`python run.py`).
2. Zip kullanıyorsan `_internal` exe’nin yanında kalsın. Sadece `KodYazar.exe`’yi Masaüstü’ne kopyalamak sandbox’ın gördüğü şey; Qt ve `games.json` bulunamaz.
3. SmartScreen: Diğer bilgiler → Yine de çalıştır. Defender: bu repoya güveniyorsan karantinadan geri al.

Sahte “0/70” rozeti koymuyoruz. Sayı her taramada değişir.

---

## Sunucu kilidi

`brand.py`: sunucu **KodYazar Client**, id `1549516395010854912`, davet `https://discord.gg/rS42FCPfKZ`. `GET /users/@me/guilds` bu id’yi içermezse ana arayüz açılmaz. 20 sn zaman aşımı. Token yapıştırma yedek yoldur.

---

## Sekmeler

1. Rozet kontrol — Bravery / Brilliance / Balance
2. Tüm rozetler — katalog + hesaptakiler
3. Oyun menüsü — katalog + RPC
4. Profil gizliliği
5. Görevler
6. Hesap
7. Yardım

---

## Oyun menüsü / Rich Presence

`games.json` Discord detectable listesi. Satırın `id` alanı IPC `client_id`.

Bağlantı:

- Windows `\\.\pipe\discord-ipc-N`
- Linux `$XDG_RUNTIME_DIR/discord-ipc-N` (+ Flatpak/Snap/Vesktop)
- macOS tmp / Application Support

`SET_ACTIVITY` `ActivityConfig.build()` ile üretilir. Önizleme Discord kartına benzer. Algılama `executables[]` (launcher hariç).

Kısayollar: Ctrl+R random, Ctrl+U RPC, Ctrl+L temizle, Ctrl+P pin, Ctrl+D tara, Ctrl+F favori, Ctrl+Shift+S mağaza butonu.

---

## Science farm

Rich Presence değil. `POST /science`: `launch_game` + `running_game_heartbeat`. `analytics_token` `@me?with_analytics_token=true` ile gelir.

| Mod | Etki |
| --- | --- |
| Saat ekle | `duration_tracked_ms = saat × 3600 × 1000` |
| Oynandı | 60 sn; başarılı id `profiles.json` `played` listesine yazılır |

Token + çerez şart. `executable_fingerprint` resmi client’ın gerçek oyun algısından gelir; yoksa bazı sayaçlar paketi yok sayabilir. 24 bin oyunun hepsine basmadan önce [`discord.md`](discord.md) ve Discord ToS.

Kimlik: `science_state.json` (Windows DPAPI, diğerlerinde `0600`).

---

## Görevler

`GET /quests/@me`. Destek: `WATCH_VIDEO*`, `PLAY_ON_DESKTOP`, `STREAM_ON_DESKTOP`, `PLAY_ACTIVITY`. Önce Quest Home’da kabul et.

---

## Diskteki veri

| | Config | Cache / log |
| --- | --- | --- |
| Windows | `%APPDATA%\kodyazar` | `%LOCALAPPDATA%\kodyazar` |
| Linux | `~/.config/kodyazar` | `~/.cache/kodyazar` |
| macOS | `~/Library/Application Support/kodyazar` | `~/Library/Caches/kodyazar` |

`science_state.json` yüksek gizlilik. Şema: [`data.md`](data.md).

---

## Dizinler

```
run.py, games.json, ky_gameplayer/, assets/, packaging/, tests/, docs/
```

Paket haritası: [`../ky_gameplayer/README.md`](../ky_gameplayer/README.md).

---

## Geliştirme planı (yol haritası)

Tam liste: [`roadmap.md`](roadmap.md).

| Aşama | Hedef |
| --- | --- |
| **1.0.x şimdi** | Dokümantasyon, CI, GitHub, `icon.ico`, Windows release zip. Sosyal önizleme açık. |
| **1.1** | Katalog senkron CLI, Linux desktop’u git kopyasını ezmeden kurmak, macOS `.app`, pencere geometrisi |
| **1.2** | Kendi uygulamanın asset tarayıcısı, Listening yardımcısı, resmi Discord’da ek slot uyarısı |
| **1.3** | Science dry-run, fingerprint yakalama, tüm kataloğa basmadan onay |
| **2.0** | Script kancası, çok hesaplı kimlik dosyası, imzalı ikili. Telemetri yok (isteğe bağlı olmadan) |

Kapsam dışı: v20 çerez, token barındırma, bot token modu, sahte Staff rozeti.

---

## Test ve CI

```bash
python -m compileall -q ky_gameplayer run.py tests
python -m unittest discover -s tests -v
```

GitHub Actions: Python 3.11 / 3.12 / 3.13, PySide6 kurulmaz.

---

## Sorun giderme

[`troubleshooting.md`](troubleshooting.md). Kısa:

- **Bağlan** öncesi Discord açık olsun
- Kilit, token’ın **aynı** hesabının sunucuda olmasını ister
- WSL, Windows named pipe görmez
- EXE için `dist\KodYazar` klasörünün tamamı

---

## SSS

**Neden token okunuyor?** HypeSquad, görev, science ve üyelik, masaüstü kullanıcısı olarak çalışsın diye. Token `discord.com` dışında gitmez.

**Neden sunucu kilidi?** KodYazar Client ürün kapısı. Çatallarda `brand.py` değişir.

**Özel Application ID?** Kimlik grubuna yaz. Onaylı oyunlarda özel `name` çoğu zaman yok sayılır.

**İki oyun birden?** Resmi Discord hayır. Vesktop/arRPC belki.

**`games.json` güncel mi?** Yayın anındaki detectable dökümü. 1.1’de CDN’den yenileme planı var.

**VirusTotal 3 tespit — virüs mü?** Hayır diyecek kadar emin değiliz; evet diyecek kadar da değil. Üçü de aile adı olmayan ML/heuristic. Sandbox ağ ve drop görmedi. Paketlenmiş exe istemiyorsan `python run.py`.

---

## Lisans — KYAL-1.0

[`../LICENSE`](../LICENSE). Çatallarda ve herkese açık ikililerde yukarıdaki atıf bloğu kalsın.
