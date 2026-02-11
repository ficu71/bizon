# 🚀 BIZON SAVE DESTROYER 3000

<p align="center">
  <img src="https://raw.githubusercontent.com/ficu71/bizon/main2/gui-web/public/hero.png" width="600" alt="BIZON DESTROYER HERO">
</p>

## ⚡ REWRITE THE RULES. DESTROY THE BALANCE

Zaawansowane narzędzie do edycji save'ów Unity, stworzone by siać chaos w statystykach. Nie tylko edytor, ale **kombajn do reverse engineeringu**.

📘 **Kompletny przewodnik (wszystkie komendy)**: [`GUIDE_KOMPLETNY.md`](GUIDE_KOMPLETNY.md)

---

## 🎨 KOZACKIE GUI (v2)

Dla najlepszych wrażeń użyj naszego nowoczesnego, neonowego interfejsu.

<p align="center">
  <img src="https://raw.githubusercontent.com/ficu71/bizon/main2/gui-web/public/card1.png" width="45%" alt="GUI Card 1">
  <img src="https://raw.githubusercontent.com/ficu71/bizon/main2/gui-web/public/card2.png" width="45%" alt="GUI Card 2">
</p>

### Jak odpalić panel lokalnie

1. **Zresetuj porty**: `lsof -ti:3000,8000 | xargs kill -9`
2. **Start Backend**: `PYTHONPATH=. python3 -m uvicorn backend.main:app --port 8000`
3. **Start Frontend**: `cd gui-web && npm run dev`
4. **Link**: [http://localhost:3000](http://localhost:3000)

---

## 💻 CLI (HARDCORE MODE)

Skrypty v2 z wbudowanymi bezpiecznikami.

### 🪙 ZŁOTO

```bash
python3 patch_gold.py "SAVE.sav" 999999 --current 500
```

### ⚔️ PERKI

```bash
python3 patch_perks.py "SAVE.sav" 99 --current-active 1 --current-passive 2 --current-stats 3
```

### 📈 STATYSTYKI POSTACI

```bash
# 1) Podejrzyj sloty postaci i ich staty
python3 patch_stats.py "SAVE.sav" --list-slots

# 2) Patch jednej postaci (bezpiecznie: wymagane --current-* dla patchowanych statów)
python3 patch_stats.py "SAVE.sav" --slot 1 \
  --agility 20 --strength 20 --constitution 20 --intelligence 20 --courage 20 --charisma 20 \
  --current-agility 10 --current-strength 11 --current-constitution 12 --current-intelligence 7 --current-courage 8 --current-charisma 7

# 3) Tryb masowy (ryzykowny)
python3 patch_stats.py "SAVE.sav" --mode all --courage 99
```

---

## 🧠 NAUKA O DESTRUKCJI

Projekt wykorzystuje autorski silnik **UESE** i wspólny rdzeń **Naheulbeuk Patcher**:

- 🧬 **Heurystyki**: Automatyczne omijanie danych PNG i regionów o wysokiej entropii (zaszyfrowanych).
- 🧬 **Smart Matching**: Wymóg podania `--current` eliminuje ryzyko uszkodzenia rekordów NPC.
- 🧬 **Slot-based Stats Patching**: `patch_stats.py` wykrywa kompletne sloty, weryfikuje `--current-*` i patchuje tylko `m_value`.
- 🧬 **Precyzja**: Obsługa `trailing bytes` – save po patchu zachowuje 100% integralności struktury.

---

## ⚠️ UWAGA

> [!CAUTION]
> **GAME BALANCE DESTROYED**: Użycie tego narzędzia nieodwracalnie zaburza balans rozgrywki. Backup Twoich save'ów jest tworzony automatycznie (`.patched`), ale działasz na własną odpowiedzialność. Fizyka w grze staje się opcjonalna po pierwszym patchu.

---

## 🏗️ TECHNICAL STACK

- **Backend**: FastAPI (Python 3.11+)
- **Frontend**: React 19 + Vite + Tailwind CSS v4
- **Aesthetic**: Neon Glitched / Space Grotesk
- **Deployment**: `www.kombajn.f1cu.space` (Static via GH Pages)

---

Developed with ❤️ for the bizon community. **(C) 2026 BIZON INDUSTRIES**
