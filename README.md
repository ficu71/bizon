# 🚀 UESE — Universal Epic Save Editor

**UESE** to narzędzie do reverse engineeringu binarnych save’ów (Unity / C#) metodą **diff-based scanning**.
Zamiast zgadywać „na pałę” w hexie, UESE pomaga znaleźć kandydatów offsetów przez porównanie 3 save’ów z różnymi wartościami, a potem bezpiecznie patchować wybrane pole.

---

## ✨ Co potrafi

- 🔎 **`scan`** — szuka offsetów po dokładnych wartościach (`v1 v2 v3`)
- 📈 **`delta`** — szuka offsetów po wzorcu przyrostów (`d1 d2`)
- 🧠 heurystyki wykluczania śmieci:
  - `png` (detekcja + parsowanie do chunku `IEND`)
  - `entropy` (Shannon, okna wysokiej entropii)
- 🏆 ranking kandydatów po score + składowe (`diff_ab`, `diff_bc`)
- 🧾 kontekst `hexdump` przy każdym kandydacie
- 🧷 **`patch`** z backupem + opcją zapisu do nowego pliku (`--out`)
- 📦 eksport raportów: **JSON / Markdown / CSV**

---

## 🛠 Instalacja

```bash
pip install -r requirements.txt
```

Uruchamianie:

```bash
python3 uese.py --help
# albo
python3 -m uese --help
```

---

## ⚡ Quick Start (Gold 111 / 222 / 333)

Przygotuj 3 save’y z tego samego slotu/postaći, zmieniając tylko jedną wartość (np. gold):

- save A: `111`
- save B: `222`
- save C: `333`

Skan:

```bash
python3 uese.py scan \
  -s save_111.sav save_222.sav save_333.sav \
  -v 111 222 333 \
  -w 4 \
  --dtype u32 \
  --exclude png entropy \
  --json output/report_gold.json \
  --md output/report_gold.md
```

Potem test patcha (np. 999):

```bash
python3 uese.py patch \
  -s save_333.sav \
  -o 0x40 \
  -v 999 \
  -w 4 \
  --out output/test_999.sav
```

Jeśli działa — patch docelowy (np. 65535):

```bash
python3 uese.py patch -s save_333.sav -o 0x40 -v 65535 -w 4 --out output/gold_65535.sav
```

---

## 📚 Komendy

### 1) `scan`

Szukaj offsetów po dokładnym patternie wartości.

```bash
python3 uese.py scan -s A.sav B.sav C.sav -v V1 V2 V3 [opcje]
```

Najważniejsze opcje:

- `-w, --width 2|4`
- `--dtype auto|u16|u32|s16|s32`
- `--exclude png entropy none`
- `--json PATH`
- `--md PATH`
- `--csv PATH`

---

### 2) `delta`

Szukaj offsetów po przyrostach:

- `vb - va = d1`
- `vc - vb = d2`

```bash
python3 uese.py delta -s A.sav B.sav C.sav -d 111 111 --dtype auto --exclude png entropy
```

---

### 3) `patch`

Bezpieczna podmiana wartości na offsecie.

```bash
python3 uese.py patch -s input.sav -o 0x1f2a -v 999 -w 4 --out output/patched.sav
```

Opcje:

- `--out` zapisuje patch do nowego pliku
- domyślnie tworzy backup (`~/.uese_backups/...`)
- `--no-backup` wyłącza backup

---

## 🔐 Bezpieczeństwo pracy

1. Zawsze zaczynaj od patch testowego (`999`), nie od maksów.
2. Najpierw pracuj na kopii (`--out`), nie na oryginale.
3. Trzymaj backupy — UESE robi je automatycznie.
4. Jeśli save po patchu nie działa: możliwe checksumy / kompresja / zły offset.

---

## 🧪 Przykładowy flow RE

1. Zbierasz 3 save’y z kontrolowanymi wartościami.
2. `scan` lub `delta`.
3. Bierzesz top-kandydata i testujesz `patch`.
4. Weryfikujesz w grze.
5. Dopiero potem robisz patch docelowy.

---

## 📁 Struktura projektu

```text
uese.py
uese/
  cli/
    commands.py
  core/
    universal_scanner.py
    patch_engine.py
    profile_manager.py
```

---

## 🧯 Troubleshooting

### `ModuleNotFoundError: yaml`

```bash
pip install -r requirements.txt
```

### Brak kandydatów

- sprawdź, czy save’y są z tego samego slotu
- upewnij się, że zmieniałeś tylko jedną wartość
- przetestuj `--dtype auto`
- przetestuj skan bez części filtrów: `--exclude none`

---

## ⚖️ Disclaimer

Narzędzie przeznaczone do edukacji, debugowania i analizy własnych zapisów gry.
Używasz na własną odpowiedzialność.
