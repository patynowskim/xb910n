# Własne komunikaty głosowe w Sony WH-XB910N

Opis, jak wgrać własne dźwięki (`boot`, `pass`, `fail`) do słuchawek WH-XB910N
przez aplikację Sound Connect i lokalne proxy. Przetestowane na firmware 1.2.2.

## Efekt

| Slot | Komunikat Sony          | Własny dźwięk |
|------|-------------------------|---------------|
| 00   | Power on                | `boot.raw`    |
| 03   | Bluetooth connected     | `pass.raw`    |
| 04   | Bluetooth disconnected  | `fail.raw`    |

Numery slotów sprawdziłem korelacją PCM z komunikatami XM4 (korelacja 0.985-0.987).

## Dlaczego wcześniejsze próby nie działały

1. Skrypty w repo były pisane pod WH-1000XM4 (`VGIDLPB0401`, 54 sloty, inny klucz AES).
   XB910N używa `VGIDLPB0601`..`0610` (44 sloty, obraz `0x131000` bajtów).
2. `repack.py` nie przeliczał sumy kontrolnej całego pliku `SHA-256(plik[0x100:])`
   w bajtach `0x000..0x01F`. Słuchawki sprawdzają ją na końcu (`CheckIntegrity`, `0x1C01`),
   stąd błąd na 99%.
3. Certyfikat proxy i APK wygasły (2026-10-10), firewall blokował port 8848,
   a tryb 3 w `script.js` serwował `http://` zamiast `https://`.

## Krok po kroku

### 1. Klucze AES
Na firmware 1.2.2 działa odczyt pamięci przez RACE (`0x0403`). Zrzut bootloadera
(`0x00003000`, 64 KB) zawiera klucze:

```
KEY = Quah8gangeizagie
IV  = ahcee8Yo1iekiu6e
```

Weryfikacja: paczka `VP_english_UPG_enc_xb910n.bin` odszyfrowuje się (AES-CBC),
rozpakowuje (LZMA) i zgadza się SHA-256.

### 2. Format paczki
`nagłówek 0x1000 B` + `AES-CBC( 13 B nagłówka LZMA + strumień LZMA )`.
Po rozpakowaniu: tablica 44 wpisów (rozmiar, adres), potem surowe MP3
(48 kHz, mono, 64 kbps, bez ID3) i na końcu napis `1.0.3` pod `0x130FC0`.
W nagłówku TLV trzeba poprawić: `0x11` (rozmiar ciała), `0x12` (rozmiar po
rozpakowaniu), `0x14` (SHA-256 obrazu) oraz globalną sumę w `0x000`.

### 3. Konwersja dźwięków
Źródła: 24 kHz, mono, `s16le`. Konwersja do MP3 48 kHz mono 64 kbps (ffmpeg,
libmp3lame, bez znaczników ID3/Xing). `boot` ma ok. -4 dB.

### 4. Budowa paczki
```
python repack.py VP_english_UPG_enc_xb910n.bin \
  mdr_proxy/firmware/VP_english_custom_boot.bin \
  --slot 0=boot.mp3 --slot 3=pass.mp3 --slot 4=fail.mp3
```
Skrypt sam wykrywa klucz (XB910N / XM4), zachowuje ogon `1.0.3` i przelicza sumy.

### 5. Proxy i aplikacja
- Nowy certyfikat (10 lat) dla proxy, aplikacja Sound Connect 13.3.1
  spatchowana (APKEditor + własny CA + `network_security_config.xml`),
  podpisana uber-apk-signerem.
- Firmware słuchawek 1.3.1 zdegradowany do 1.2.2 (tylko na 1.2.2 działa odczyt RACE).
- `tools/mdr_proxy_script.js` -> opcja 4: `MDRID*` zostaje aktualne (brak propozycji
  aktualizacji do 1.3.1), a `info.xml` paczki `VGIDLPB*` dostaje poprawne `MAC` (SHA-1)
  i `Size` wgrywanego pliku.
- Telefon przez USB: `adb reverse tcp:8848 tcp:8848` i
  `adb shell settings put global http_proxy 127.0.0.1:8848`.
- Słuchawki połączone z telefonem (nie z komputerem), w aplikacji zmiana
  Voice Guidance na English.

### 6. Sprzątanie
```
adb shell settings put global http_proxy :0
adb shell settings delete global http_proxy
adb reverse --remove-all
```
Samo `delete` nie czyści proxy w pamięci Androida. Bez `:0` telefon traci internet
(walidacja sieci idzie przez martwy `127.0.0.1:8848`).

## Uwagi

- Pierwsza próba z tą samą paczką skończyła się `0%` i błędem. Kolejna przeszła
  bez zmian w pliku, więc przyczyną było połączenie lub stan aplikacji.
- Pliki `*.bin`, `*.pem`, `mdr_proxy/` są w `.gitignore` (firmware Sony, klucze, APK).
