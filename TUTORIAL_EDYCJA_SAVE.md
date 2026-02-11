# 🎮 Tutorial: Edycja Save'ów Naheulbeuk (Bezpieczna)

Poradnik krok po kroku jak zmienić złoto, punkty umiejętności i statystyki postaci w *The Dungeon of Naheulbeuk*.

> [!IMPORTANT]
> **Nowa wersja skryptów (v2)** wprowadza zabezpieczenia. Musisz podać **aktualną wartość**, którą widzi Twoja postać w grze, aby skrypt wiedział dokładnie, który rekord edytować.

---

## 📋 Wymagania

- Python 3 (zainstalowany na Mac/Windows/Linux)
- Pliki `patch_gold.py`, `patch_perks.py`, `patch_stats.py` i `naheulbeuk_patch.py` z repozytorium

---

## 🪙 Zmiana ilości złota

### Krok 1-2: Znajdź plik i spisz stan

Sprawdź w grze, ile **dokładnie** masz złota przed edycją (np. 500). Zrób kopię zapasową pliku `.sav`.

### Krok 3: Uruchom skrypt z flagą `--current`

Przejdź do folderu z repozytorium:

```bash
cd /Users/f1cu_71/Desktop/biz/bizon
```

Uruchom skrypt podając:

1. Ścieżkę do save'a
2. Nową ilość złota
3. **`--current <ile_masz_teraz>`** (Zabezpieczenie przed edycją innych wartości)

```bash
python3 patch_gold.py "Game_fcu_fcusav.sav" 999999 --current 500
```

---

## ⚔️ Zmiana punktów umiejętności

Dla perków musisz podać **trzy wartości** swojej wybranej postaci:

1. Active Skill Points
2. Passive Skill Points
3. Stats Points

**Przykład:** Postać ma 1 pkt aktywny, 2 pasywne i 3 statystyki.

```bash
python3 patch_perks.py "Game_fcu_fcusav.sav" 99 --current-active 1 --current-passive 2 --current-stats 3
```

---

## 📈 Zmiana statystyk postaci (Agility/Strength/...)

Nowy skrypt `patch_stats.py` działa w trybie bezpiecznym przez wybór slotu postaci.
W trybie `--slot` musisz podać także bieżące wartości `--current-*` dla statystyk, które zmieniasz.

### Krok 1: Podejrzyj sloty

```bash
python3 patch_stats.py "Game_fcu_fcusav.sav" --list-slots
```

Skrypt pokaże:

- `Slot 1..N`
- offset `statsManager`
- `level`
- aktualne wartości `base` i `value` dla statystyk

> [!TIP]
> Do flag `--current-*` bierz wartości z kolumny `value`.

### Krok 2: Patch jednej postaci (bezpiecznie)

Przykład: ustaw Agility=13, Strength=10 i Intelligence=12 dla slotu 1
(z weryfikacją bieżących wartości):

```bash
python3 patch_stats.py "Game_fcu_fcusav.sav" --slot 1 --agility 13 --strength 10 --intelligence 12 --current-agility 10 --current-strength 11 --current-intelligence 7
```

> [!NOTE]
> W save inteligencja jest zapisana jako `m_cleverness`. Dlatego możesz użyć zarówno `--intelligence`, jak i `--cleverness`.
> Patch zmienia tylko `m_value`; `m_baseValueOverride` pozostaje bez zmian.

### Krok 3: (Opcjonalnie) patch wszystkich slotów

```bash
python3 patch_stats.py "Game_fcu_fcusav.sav" --mode all --courage 99
```

### Krok 4: Dry-run (bez zapisu)

```bash
python3 patch_stats.py "Game_fcu_fcusav.sav" --slot 1 --agility 20 --current-agility 10 --dry-run
```

---

## ⚠️ Tryb Zaawansowany (`--mode all`)

Jeśli chcesz zmienić wartość u **wszystkich** (np. wszystkim postaciom dać 99 perków lub courage), użyj flagi `--mode all`. **Uwaga: To tryb ryzykowny i może uszkodzić balans lub save.**

```bash
python3 patch_gold.py "save.sav" 1000000 --mode all
```

---

## ❓ Rozwiązywanie problemów

| Problem | Rozwiązanie |
| :--- | :--- |
| `Multiple 'm_gold' fields found` | Masz kilka rekordów z tą samą wartością. Zmień ilość złota w grze i spróbuj ponownie. |
| `No such file: naheulbeuk_patch` | Upewnij się, że plik `naheulbeuk_patch.py` jest w tym samym folderze. |
| `Error: --current is required` | Od wersji v2 musisz podawać aktualną wartość dla bezpieczeństwa. |
| `--slot out of range` | Uruchom `patch_stats.py --list-slots` i wybierz poprawny numer slotu. |
| `At least one stat flag is required` | Dodaj przynajmniej jedną flagę statystyki, np. `--agility 20`. |
| `Conflict: --intelligence and --cleverness...` | Podaj jedną z flag albo ustaw identyczną wartość dla obu. |
| `Missing required current stat flags` | W trybie `--slot` dodaj `--current-*` dla każdej zmienianej statystyki. |
| `Current stat mismatch for selected slot` | Podane `--current-*` nie zgadzają się z wybranym slotem; sprawdź ponownie `--list-slots`. |

---

## 🔥 Szybka ściąga

```bash
# 1. Złoto: mam 500, chcę milion
python3 patch_gold.py "SAVE.sav" 1000000 --current 500

# 2. Perki: mam postać 1,2,3 chcę 99 u niej
python3 patch_perks.py "SAVE.sav" 99 --current-active 1 --current-passive 2 --current-stats 3

# 3. Staty: sprawdzam sloty
python3 patch_stats.py "SAVE.sav" --list-slots

# 4. Staty: patch jednej postaci (slot 1)
python3 patch_stats.py "SAVE.sav" --slot 1 --agility 20 --strength 20 --constitution 20 --intelligence 20 --courage 20 --charisma 20 --current-agility 10 --current-strength 11 --current-constitution 12 --current-intelligence 7 --current-courage 8 --current-charisma 7

# 5. Podmiana
mv "SAVE.sav.stats.patched" "SAVE.sav"
```

Gotowe! 🎉
