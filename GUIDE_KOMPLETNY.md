# 📘 Kompletny Guide: Naheulbeuk Save Editing (CLI + GUI)

Ten dokument zbiera w jednym miejscu **pełny workflow** i **wszystkie najważniejsze komendy** dla:

- złota (`patch_gold.py`)
- perków (`patch_perks.py`)
- statystyk postaci (`patch_stats.py`)
- uruchomienia GUI lokalnie i przez Docker

---

## 1) Setup środowiska

```bash
cd /Users/f1cu_71/Desktop/biz/bizon
python3 --version
```

Opcjonalnie (czyste venv):

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Podgląd pomocy:

```bash
python3 patch_gold.py --help
python3 patch_perks.py --help
python3 patch_stats.py --help
```

---

## 2) Backup save (zalecane przed każdą operacją)

```bash
cp "save do analizy/Game_fcu_fcusav.sav" "save do analizy/Game_fcu_fcusav.sav.backup"
```

---

## 3) Złoto (`patch_gold.py`)

### Bezpieczny dry-run (bez zapisu)

```bash
python3 patch_gold.py "save do analizy/Game_fcu_fcusav.sav" 999999 --current 500 --dry-run
```

### Realny patch jednej postaci (tryb `player`)

```bash
python3 patch_gold.py "save do analizy/Game_fcu_fcusav.sav" 999999 --current 500
```

### Patch wszystkich dopasowań (ryzykowny)

```bash
python3 patch_gold.py "save do analizy/Game_fcu_fcusav.sav" 999999 --mode all
```

### Własna ścieżka wyjściowa

```bash
python3 patch_gold.py "save do analizy/Game_fcu_fcusav.sav" 999999 --current 500 --out "save do analizy/Game_fcu_fcusav.gold.patched.sav"
```

---

## 4) Perki (`patch_perks.py`)

W trybie `player` wymagane:

- `--current-active`
- `--current-passive`
- `--current-stats`

### Dry-run

```bash
python3 patch_perks.py "save do analizy/Game_fcu_fcusav.sav" 99 --current-active 1 --current-passive 2 --current-stats 3 --dry-run
```

### Realny patch jednej postaci

```bash
python3 patch_perks.py "save do analizy/Game_fcu_fcusav.sav" 99 --current-active 1 --current-passive 2 --current-stats 3
```

### Patch wszystkich dopasowań (ryzykowny)

```bash
python3 patch_perks.py "save do analizy/Game_fcu_fcusav.sav" 99 --mode all
```

### Własna ścieżka wyjściowa

```bash
python3 patch_perks.py "save do analizy/Game_fcu_fcusav.sav" 99 --current-active 1 --current-passive 2 --current-stats 3 --out "save do analizy/Game_fcu_fcusav.perks.patched.sav"
```

---

## 5) Statystyki (`patch_stats.py`)

Najważniejsze zasady:

- `--mode slot` wymaga `--slot`.
- Dla każdego zmienianego statu musisz podać pasujące `--current-*`.
- W `slot mode` skrypt porównuje `current` z aktualnym `value` i zatrzymuje patch przy mismatch.
- Patch dotyka tylko `m_value` (nie zmienia `m_baseValueOverride`).

### 5.1 Lista slotów

```bash
python3 patch_stats.py "save do analizy/Game_fcu_fcusav.sav" --list-slots
```

### 5.2 Lista slotów wraz z placeholderami (debug)

```bash
python3 patch_stats.py "save do analizy/Game_fcu_fcusav.sav" --list-slots --include-placeholders
```

### 5.3 Dry-run patcha jednej postaci (bez zapisu)

```bash
python3 patch_stats.py "save do analizy/Game_fcu_fcusav.sav" \
  --slot 1 \
  --agility 99 --strength 99 --constitution 99 --intelligence 99 --courage 99 --charisma 99 \
  --current-agility 10 --current-strength 10 --current-constitution 11 --current-intelligence 10 --current-courage 13 --current-charisma 12 \
  --dry-run
```

### 5.4 Realny patch jednej postaci

```bash
python3 patch_stats.py "save do analizy/Game_fcu_fcusav.sav" \
  --slot 1 \
  --agility 99 --strength 99 --constitution 99 --intelligence 99 --courage 99 --charisma 99 \
  --current-agility 10 --current-strength 10 --current-constitution 11 --current-intelligence 10 --current-courage 13 --current-charisma 12
```

### 5.5 Patch wszystkich slotów (ryzykowny, bez `--current-*`)

```bash
python3 patch_stats.py "save do analizy/Game_fcu_fcusav.sav" --mode all --courage 99
```

### 5.6 Alias inteligencji

Możesz użyć:

- `--intelligence` lub `--cleverness`
- `--current-intelligence` lub `--current-cleverness`

Przykład:

```bash
python3 patch_stats.py "save do analizy/Game_fcu_fcusav.sav" --slot 1 --cleverness 77 --current-cleverness 10 --dry-run
```

### 5.7 Własna ścieżka wyjściowa

```bash
python3 patch_stats.py "save do analizy/Game_fcu_fcusav.sav" --slot 1 --agility 20 --current-agility 10 --out "save do analizy/Game_fcu_fcusav.stats.custom.sav"
```

---

## 6) Podmiana patched save na oryginał

Złoto:

```bash
mv "save do analizy/Game_fcu_fcusav.sav.patched" "save do analizy/Game_fcu_fcusav.sav"
```

Perki:

```bash
mv "save do analizy/Game_fcu_fcusav.sav.perks.patched" "save do analizy/Game_fcu_fcusav.sav"
```

Statystyki:

```bash
mv "save do analizy/Game_fcu_fcusav.sav.stats.patched" "save do analizy/Game_fcu_fcusav.sav"
```

---

## 7) Szybka weryfikacja po patchu

Sprawdzenie slotów na pliku wyjściowym:

```bash
python3 patch_stats.py "save do analizy/Game_fcu_fcusav.sav.stats.patched" --list-slots
```

Pełne testy lokalne:

```bash
python3 -m unittest -v test_naheulbeuk_patchers.py
```

---

## 8) GUI lokalnie

Backend + frontend:

```bash
lsof -ti:3000,8000 | xargs kill -9
PYTHONPATH=. python3 -m uvicorn backend.main:app --port 8000
```

W drugim terminalu:

```bash
cd gui-web
npm install
npm run dev
```

Otwórz:

```text
http://localhost:3000
```

---

## 9) Docker

Build:

```bash
docker build -t bizon-save-destroyer .
```

Run:

```bash
docker run --rm -p 8080:8080 bizon-save-destroyer
```

Otwórz:

```text
http://localhost:8080
```

---

## 10) Najczęstsze błędy i szybkie fixy

- `Error: --current is required in 'player' mode`
  - Dodaj `--current` w `patch_gold.py`.
- `Error: --current-active, --current-passive, and --current-stats are required`
  - Dodaj wszystkie trzy flagi w `patch_perks.py`.
- `Missing required current stat flags in 'slot' mode`
  - Dla każdego patchowanego statu w `patch_stats.py` dodaj odpowiedni `--current-*`.
- `Current stat mismatch for selected slot`
  - Uruchom `--list-slots` i przepisz dokładne `value` dla wybranego slotu.
- `--slot out of range`
  - Numer slotu nie istnieje; sprawdź listę slotów ponownie.

---

## 11) Minimalny bezpieczny flow (TL;DR)

```bash
cd /Users/f1cu_71/Desktop/biz/bizon
cp "save do analizy/Game_fcu_fcusav.sav" "save do analizy/Game_fcu_fcusav.sav.backup"
python3 patch_stats.py "save do analizy/Game_fcu_fcusav.sav" --list-slots
python3 patch_stats.py "save do analizy/Game_fcu_fcusav.sav" --slot 1 --agility 99 --current-agility 10 --dry-run
python3 patch_stats.py "save do analizy/Game_fcu_fcusav.sav" --slot 1 --agility 99 --current-agility 10
```
