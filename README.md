# save-kombajn

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
python3 -m save_kombajn --help
# albo
python3 save_kombajn/cli.py --help
```

## Workflow: GOLD 111 / 222 / 333

1. Przygotuj 3 save'y (ten sam slot/postać), tylko GOLD zmieniaj: 111, 222, 333.
2. Skan:

```bash
python3 save_kombajn/cli.py scan \
  --values 111 222 333 \
  --width auto \
  --dtype auto \
  --exclude png entropy \
  --top 30 \
  --json output/report_gold.json \
  --md output/report_gold.md \
  examples/save_111.sav examples/save_222.sav examples/save_333.sav
```

3. Weź top-kandydata i zrób patch testowy (`999`).

```bash
python3 save_kombajn/cli.py patch \
  --offset 0x80 \
  --dtype u32 \
  --value 999 \
  examples/save_333.sav output/test_999.sav
```

4. Jeśli w grze działa, zrób patch docelowy (`65535`).

```bash
python3 save_kombajn/cli.py patch \
  --offset 0x80 \
  --dtype u32 \
  --value 65535 \
  examples/save_333.sav output/gold_65535.sav
```

## Komendy

### `scan`

```bash
python3 save_kombajn/cli.py scan --values V1 V2 V3 [opcje] file1 file2 file3
```

Opcje:
- `--width auto|2|4` (domyślnie: `auto`)
- `--dtype auto|u16|u32|s16|s32` (domyślnie: `auto`)
- `--exclude png entropy none` (domyślnie: `png entropy`)
- `--json PATH`, `--md PATH`

Wynik kandydata:
- offset hex
- width
- dtype
- wartości `(va, vb, vc)`
- `score`, `diff_ab`, `diff_bc`
- hexdump kontekstu

### `delta`

```bash
python3 save_kombajn/cli.py delta --deltas D1 D2 [opcje] file1 file2 file3
```

Szukane warunki:
- `vb - va == D1`
- `vc - vb == D2`

### `patch`

```bash
python3 save_kombajn/cli.py patch \
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

W `score.py`:

- `+300` gdy bajty pola zmieniają się między A→B i B→C,
- `+max(0, 500 - noise)` gdzie `noise = diff_ab + diff_bc` w oknie ±64B,
- `-250` gdy `noise > 420` (chaotyczna okolica),
- `-500` gdy offset jest w regionie wykluczonym (w praktyce i tak filtrowany wcześniej).

Sortowanie: malejąco po `score`, potem po `offset`, potem `dtype`.

## Self-test

```bash
python3 -m save_kombajn.selftest
```

Generuje przykładowe save'y w `examples/`, uruchamia skan, patch, i raporty.
