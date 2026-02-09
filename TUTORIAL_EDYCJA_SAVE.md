# 🎮 Tutorial: Edycja Save'ów Naheulbeuk (Bezpieczna)

Poradnik krok po kroku jak zmienić złoto i punkty umiejętności w *The Dungeon of Naheulbeuk*.

> [!IMPORTANT]
> **Nowa wersja skryptów (v2)** wprowadza zabezpieczenia. Musisz podać **aktualną wartość**, którą widzi Twoja postać w grze, aby skrypt wiedział dokładnie, który rekord edytować.

---

## 📋 Wymagania

- Python 3 (zainstalowany na Mac/Windows/Linux)
- Pliki `patch_gold.py`, `patch_perks.py` i `naheulbeuk_patch.py` z repozytorium

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

## ⚠️ Tryb Zaawansowany (`--mode all`)

Jeśli chcesz zmienić wartość u **wszystkich** (np. wszystkim postaciom dać 99 perków na raz), użyj flagi `--mode all`. **Uwaga: Może uszkodzić save, jeśli w danych są inne liczby wyglądające jak punkty!**

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

---

## 🔥 Szybka ściąga

```bash
# 1. Złoto: mam 500, chcę milion
python3 patch_gold.py "SAVE.sav" 1000000 --current 500

# 2. Perki: mam postać 1,2,3 chcę 99 u niej
python3 patch_perks.py "SAVE.sav" 99 --current-active 1 --current-passive 2 --current-stats 3

# 3. Podmiana
mv "SAVE.sav.patched" "SAVE.sav"
```

Gotowe! 🎉
