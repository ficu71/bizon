# BIZON3000

BIZON3000 to lokalny save editor dla `The Dungeon of Naheulbeuk`, zbudowany wokół typed semantic workflow:

`doctor -> inspect -> choose record -> choose field -> preview -> patch -> verify -> reparse`

To nie jest już tylko skaner offsetów. Głównym produktem jest semanticzny editor rekordów Naheulbeuka. Raw scan i raw patching nadal istnieją, ale jako `Expert Mode`.

## Quick Start

### 1. Python deps

```bash
pip install -r requirements.txt
```

### 2. Frontend deps

```bash
cd gui-web
npm install
cd ..
```

`gui-web/.npmrc` wymusza project-local cache, więc `npm run build` i `npm run dev` nie zależą od `~/.npm/_cacache`.

### 3. Sprawdź środowisko

```bash
python3 -m uese naheulbeuk doctor
python3 -m uese naheulbeuk doctor --json
```

Jeśli masz lokalną instalację gry, możesz wskazać ją jawnie przez:

```bash
export UESE_NAHEULBEUK_GAME_DIR='/Users/Shared/Epic Games/DungeonOfNaheulbeuk'
```

### 4. Uruchom aplikację lokalnie

Wspierany launcher:

```bash
./start_local.sh
```

Compatibility wrapper:

```bash
./start_gui.sh
```

Backend startuje na `http://127.0.0.1:8000`, frontend na `http://127.0.0.1:3000`.

## Główny workflow

### CLI-first

#### Doctor

```bash
python3 -m uese naheulbeuk doctor
python3 -m uese naheulbeuk doctor --save 'save do analizy/Game_fcu_elo.sav'
```

`doctor` raportuje:
- gotowość semantic editora
- wykrycie `UnityPy`
- wykrycie katalogu gry
- stan `CharacterAsset resolver`
- stan `scene-hint resolver`
- opcjonalny probe inspect save'a

#### Inspect

```bash
python3 -m uese naheulbeuk inspect input.sav
python3 -m uese naheulbeuk inspect input.sav --json
```

#### Lista rekordów

```bash
python3 -m uese naheulbeuk list-characters input.sav
python3 -m uese naheulbeuk list-characters input.sav --risk safe
python3 -m uese naheulbeuk list-characters input.sav --risk risky --classification npc
python3 -m uese naheulbeuk list-characters input.sav --classification environment
python3 -m uese naheulbeuk list-characters input.sav --json
```

#### Szczegóły jednego rekordu

```bash
python3 -m uese naheulbeuk show-stats input.sav --character-id character-001-13ec71f4576f
python3 -m uese naheulbeuk show-stats input.sav --character-id character-001-13ec71f4576f --json
```

#### Patch jednego pola

```bash
python3 -m uese naheulbeuk patch input.sav \
  --character-id character-001-13ec71f4576f \
  --field stats_points \
  --value 77
```

#### Patch pola niejednoznacznego

Bazowe atrybuty typu `agility` są override-driven, więc wymagają jawnego opt-in:

```bash
python3 -m uese naheulbeuk patch input.sav \
  --character-id character-001-13ec71f4576f \
  --field agility \
  --value 14 \
  --allow-ambiguous
```

#### Patch rekordu o niepełnej tożsamości

```bash
python3 -m uese naheulbeuk patch input.sav \
  --character-id character-037-743edf77773b \
  --field stats_points \
  --value 55 \
  --allow-identity-ambiguous
```

#### Batch semantic patching

```bash
python3 -m uese naheulbeuk patch-batch input.sav --spec semantic_batch.json
```

Format `semantic_batch.json`:

```json
{
  "patches": [
    {
      "record_id": "character-001-13ec71f4576f",
      "field_id": "stats_points",
      "value": 77
    },
    {
      "record_id": "character-001-13ec71f4576f",
      "field_id": "agility",
      "value": 14,
      "allow_ambiguous": true
    }
  ]
}
```

### Exit codes dla semantic CLI

- `0`: sukces
- `1`: błąd wejścia / walidacja
- `2`: verify lub reparse mismatch
- `3`: semantic block (`environment` albo `unresolved` target)

## Thin Web GUI

Główny ekran prowadzi przez wspierany flow:
- wybór jednego save'a
- `doctor` status
- inspect rekordów
- filtry `safe/risky/unresolved`
- wybór rekordu
- edycja pól
- preview queue
- apply semantic batch

Raw scan i raw offset patching są schowane w rozwijanym `Expert Mode`.

## Wspierane pola semanticzne

- `health`
- `energy`
- `agility`
- `charisma`
- `cleverness`
- `constitution`
- `courage`
- `strength`
- `level`
- `current_xp`
- `stats_points`
- `active_skill_points`
- `passive_skill_points`
- `dodge`
- `parry`

## Klasy rekordów

Semantic editor klasyfikuje rekordy jako:
- `party`
- `companion`
- `npc`
- `environment`
- `unknown`

I osobno nadaje status edycji:
- `safe`
- `risky`
- `unresolved`
- `economy`

### Ważne ograniczenia

- `environment` jest inspect-only w semantic mode.
- `gold` jest nadal wystawiane jako `economy slots`; owner mapping nie jest jeszcze wystarczająco pewny.
- Bazowe atrybuty są zapisane przez `CharacterStatistic` override/cached pairs. Gdy rekord jest w `auto mode`, save nie daje zawsze jednej absolutnie pewnej wartości runtime.
- `dodge` i `parry` nie są prostymi integerami; są mapowane semantycznie z ich obiektów.
- Jeśli lokalne assety gry nie są dostępne, semantic inspect działa dalej, ale w degraded mode i z gorszym identity resolution.

## Expert Mode

Raw tooling nadal istnieje dla reverse-engineeringu i fallbacku:

```bash
python3 -m uese scan ...
python3 -m uese delta ...
python3 -m uese patch ...
```

Dodatkowe skrypty:
- `patch_gold.py`
- `patch_perks.py`
- `patch_stats.py`

Te skrypty są teraz oznaczone jako deprecated expert helpers. Nie są głównym interfejsem produktu.

## Backend API

Wspierane endpointy semanticzne:
- `GET /naheulbeuk/doctor`
- `GET /naheulbeuk/inspect`
- `GET /naheulbeuk/characters`
- `GET /naheulbeuk/character/{character_id}`
- `POST /naheulbeuk/patch-semantic`
- `POST /naheulbeuk/patch-batch-semantic`

Legacy expert fallback:
- `POST /scan`
- `POST /patch`
- `POST /patch-batch`

## Testy i smoke checks

```bash
python3 -m unittest tests.test_naheulbeuk_semantic \
  tests.test_naheulbeuk_app \
  tests.test_naheulbeuk_cli \
  tests.test_naheulbeuk_api

cd gui-web && npm run build
```

## Repo notes

Materiały reverse-engineeringowe zostały wyniesione do `research/`:
- `research/scripts/` dla ad-hoc helperów
- `research/notes/` dla dumpów i diffów
- `research/plans/` dla archiwalnych szkiców
- `research/artifacts/` dla lokalnych binarek i ciężkich artefaktów

Nie są one traktowane jako główny onboarding produktu. Wspierana ścieżka to CLI semanticzne i thin web GUI nad tym samym backendem.
