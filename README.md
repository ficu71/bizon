# 🚀 BIZON SAVE DESTROYER 3000

[![Python Version](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/)
[![UI Style](https://img.shields.io/badge/style-Save--Hacker-ff00ff.svg)](https://github.com/ficu71/bizon)

---

## ⚡ Key Features

- 🧬 **Diff-Based Scanning**: Locate variables by comparing 3 save files with known values.
- 🎨 **Premium Web GUI**: A state-of-the-art "Save Hacker" dashboard with glitch effects and neon glows.
- 🛠️ **Patch Engine**: Direct hex modification with automatic backups (`.bak`) and verification.
- 🔍 **Heuristic Exclusion**: Automatically ignores PNG data, high-entropy regions, and encrypted headers.
- 📊 **Deterministic Scoring**: Smart algorithm to rank candidates based on neighborhood noise and value consistency.

---

## 🛰️ Dashboard (Web GUI)

For the best experience, use our modern, glassmorphic web interface.

### How to Launch

1. **Reset Ports**: `lsof -ti:3000,3001,8000 | xargs kill -9` (optional, if ports are stuck)
2. **Start Backend**: `PYTHONPATH=. python3 -m uvicorn backend.main:app --port 8000`
3. **Start Frontend**: `cd gui-web && npm run dev`
4. **Open**: [http://localhost:3000](http://localhost:3000)

---

## 💻 CLI (Hardcore Mode)

Still available for those who prefer the terminal.

### `scan` - Find the Vulnerability

```bash
python3 -m uese scan \
  --values 111 222 333 \
  --width 4 \
  --dtype u32 \
  --exclude png entropy \
  saveA.sav saveB.sav saveC.sav
```

### `patch` - Rewrite Reality

```bash
python3 -m uese patch \
  --offset 0x1A4 \
  --width 4 \
  --value 999999 \
  input.sav output.sav
```

---

## 🧠 The Science of Destruction

### 1. Heuristics

- **PNG Detection**: Detects `\x89PNG\r\n\x1a\n` magics to avoid corrupting image data inside saves.
- **Entropy Analysis**: Calculates Shannon entropy (threshold ~7.7) to skip encrypted or compressed blobs.

### 2. Scoring Algorithm

- `+300` when values match the A → B → C progression perfectly.
- `+max(0, 500 - noise)` based on local byte stability (±64B).
- `-250` for chaotic neighborhoods (high noise).
- `-500` for excluded regions.

---

## ⚠️ Warning

> [!CAUTION]
> **GAME BALANCE DESTROYED**: Using this tool will irreversibly alter the balance of power. Backup drones are automatically deployed, but proceed with chaotic intent. Physics becomes optional after the first patch.

---

## 🏗️ Technical Stack

- **Backend**: FastAPI (Python)
- **Frontend**: React 19 + Vite + Tailwind CSS v4
- **Branding**: Neon Glitch Aesthetic / Space Grotesk Typography

Developed with ❤️ for the bizon community. (C) 20XX BIZON INDUSTRIES

---

# 🇵🇱 Wersja Polska (Original save-kombajn)

Lokalne narzędzie (Python stdlib) do **diff-based reverse engineeringu** binarnych save'ów Unity / Assembly-CSharp.

## Co robi (MVP)

- `scan` — znajduje kandydatów offsetów na podstawie 3 save'ów i znanych wartości (`--values v1 v2 v3`)
- `delta` — znajduje kandydatów po różnicach (`--deltas d1 d2`)
- `patch` — podmienia pole na offsecie do nowego pliku, bez zmiany rozmiaru, z backupem `.bak`
- raporty: `--json` i `--md`
- heurystyki wykluczania: `png` + `entropy`

## Instalacja / uruchamianie

Brak zewnętrznych zależności. Wystarczy Python 3.

Uruchamianie CLI:

```bash
python3 -m uese --help
# albo
python3 uese/cli/commands.py --help
```

## Workflow: GOLD 111 / 222 / 333

1. Przygotuj 3 save'y (ten sam slot/postać), tylko GOLD zmieniaj: 111, 222, 333.
2. Skan:

```bash
python3 -m uese scan \
  --values 111 222 333 \
  --width auto \
  --dtype auto \
  --exclude png entropy \
  --top 30 \
  examples/save_111.sav examples/save_222.sav examples/save_333.sav
```

1. Weź top-kandydata i zrób patch testowy (`999`).

```bash
python3 -m uese patch \
  --offset 0x80 \
  --dtype u32 \
  --value 999 \
  examples/save_333.sav output/test_999.sav
```

1. Jeśli w grze działa, zrób patch docelowy (`65535`).

```bash
python3 -m uese patch \
  --offset 0x80 \
  --dtype u32 \
  --value 65535 \
  examples/save_333.sav output/gold_65535.sav
```

## Komendy

### `scan`

```bash
python3 -m uese scan --values V1 V2 V3 [opcje] file1 file2 file3
```

Opcje:

- `--width auto|2|4` (domyślnie: `auto`)
- `--dtype auto|u16|u32|s16|s32` (domyślnie: `auto`)
- `--exclude png entropy none` (domyślnie: `png entropy`)

### `patch`

```bash
python3 -m uese patch \
  --offset 0x... \
  --dtype u16|u32|s16|s32 \
  --value N \
  input.sav output.sav
```

Bezpieczeństwo:

- tworzy `input.sav.bak` jeśli nie istnieje,
- patchuje tylko bajty pola,
- rozmiar pliku zostaje bez zmian,
- wypisuje `stare_bajty -> nowe_bajty`.

## Heurystyki wykluczania

- **PNG**: wykrycie magica `\x89PNG\r\n\x1a\n` i parsowanie chunków do `IEND`.
- **Entropy**: Shannon entropy, okno 4096, krok 2048, próg ~7.7.

## Scoring (deterministyczny)

- `+300` gdy bajty pola zmieniają się między A→B i B→C,
- `+max(0, 500 - noise)` gdzie `noise = diff_ab + diff_bc` w oknie ±64B,
- `-250` gdy `noise > 420` (chaotyczna okolica),
- `-500` gdy offset jest w regionie wykluczonym (w praktyce i tak filtrowany wcześniej).

Sortowanie: malejąco po `score`, potem po `offset`, potem `dtype`.
