# 🎮 Tutorial: Edycja Save'ów Naheulbeuk

Poradnik krok po kroku jak zmienić złoto i punkty umiejętności w *The Dungeon of Naheulbeuk*.

---

## 📋 Wymagania

- Python 3 (zainstalowany na Mac/Windows/Linux)
- Pliki `patch_gold.py` i `patch_perks.py` z repozytorium

---

## 🪙 Zmiana ilości złota

### Krok 1: Znajdź swój plik save

**Na Mac:**

```text
~/Library/Application Support/Artefacts Studio/Naheulbeuk/Save/
```

lub

```text
~/Library/Application Support/Save/
```

**Na Windows:**

```text
%USERPROFILE%\AppData\LocalLow\Artefacts Studio\Naheulbeuk\Save\
```

Szukaj plików typu `Game_*.sav` (np. `Game_fcu_fcusav.sav`).

### Krok 2: Zrób kopię zapasową

**WAŻNE: Zawsze rób backup przed edycją!**

```bash
cp "Game_fcu_fcusav.sav" "Game_fcu_fcusav.sav.backup"
```

### Krok 3: Uruchom skrypt

Otwórz Terminal (Mac) lub PowerShell (Windows) i przejdź do folderu z repozytorium:

```bash
cd /Users/f1cu_71/Desktop/biz/bizon
```

Uruchom skrypt z dwoma argumentami:

1. Ścieżka do pliku save
2. Nowa ilość złota

```bash
python3 patch_gold.py "/sciezka/do/Game_fcu_fcusav.sav" 999999
```

**Przykład z pełną ścieżką na Mac:**

```bash
python3 patch_gold.py ~/Library/Application\ Support/Save/Game_fcu_fcusav.sav 999999
```

### Krok 4: Sprawdź output

Powinieneś zobaczyć coś takiego:

```text
Found compressed payload at offset 0x12DE4
Decompressed 5456956 bytes.
Patched 'm_gold' at 0x149522 (Old value: 500)
...
Patched 26 instances of 'm_gold' in decompressed data.
Successfully created patched save: .../Game_fcu_fcusav.sav.patched
```

### Krok 5: Podmień plik

1. Przenieś oryginalny plik do bezpiecznego miejsca (backup)
2. Zmień nazwę `.patched` na oryginalną:

```bash
mv "Game_fcu_fcusav.sav.patched" "Game_fcu_fcusav.sav"
```

### Krok 6: Uruchom grę

Załaduj save w grze - powinieneś mieć nową ilość złota! 💰

---

## ⚔️ Zmiana punktów umiejętności

Proces jest identyczny, tylko używasz innego skryptu:

```bash
python3 patch_perks.py "/sciezka/do/Game_fcu_fcusav.sav" 99
```

To da ci **99 punktów** do:

- Active Skill Points (aktywne umiejętności)
- Passive Skill Points (pasywne umiejętności)  
- Stats Points (statystyki postaci)

---

## ❓ Rozwiązywanie problemów

| Problem | Rozwiązanie |
| :--- | :--- |
| `python3: command not found` | Zainstaluj Python 3 ze strony python.org |
| `No such file or directory` | Sprawdź ścieżkę do pliku (użyj `ls` żeby zobaczyć zawartość folderu) |
| `Could not find GZIP payload` | Plik może być uszkodzony lub to nie jest save z Naheulbeuk |
| Gra nie widzi zmian | Upewnij się że zamieniłeś `.patched` na oryginalną nazwę |

---

## 🔥 Szybka ściąga

```bash
# 1. Przejdź do folderu z narzędziami
cd /Users/f1cu_71/Desktop/biz/bizon

# 2. Złoto na 999999
python3 patch_gold.py "TWOJ_SAVE.sav" 999999

# 3. Perki na 99
python3 patch_perks.py "TWOJ_SAVE.sav" 99

# 4. Podmień plik
mv "TWOJ_SAVE.sav.patched" "TWOJ_SAVE.sav"
```

Gotowe! 🎉
