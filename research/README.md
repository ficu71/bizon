# Research Area

Ta część repo nie jest produktem. Trzymamy tu materiały reverse-engineeringowe, stare szkice i lokalne artefakty, żeby nie mieszały się z głównym onboardingiem BIZON3000.

## Layout

- `research/scripts/`
  Ad-hoc helpery do eksploracji binarek i save'ów. Nie mają stabilnego API ani gwarancji zgodności z głównym workflow.
- `research/notes/`
  Zrzuty heksów, diffy i luźne notatki z analizy.
- `research/plans/`
  Archiwalne plany i szkice spoza wspieranego produktu.
- `research/artifacts/`
  Lokalne binarki, backupy, duplikaty plików i inne ciężkie artefakty. Ten katalog jest ignorowany przez git.

## Zasady

- Produkt wspierany jest opisany w głównym `README.md`.
- Jeśli skrypt researchowy potrzebuje importów z repo, ma sam wyliczać root projektu zamiast zakładać stałą ścieżkę systemową.
- Nic z `research/` nie powinno być wymagane do `doctor`, semantic inspecta, semantic patchingu ani startu GUI.
