# Raport LaTeX

## Co zawiera folder
- `main.tex` - główny dokument raportu
- `sections/` - sekcje merytoryczne
- `figures/model/` - wykresy i metryki z backendu
- `figures/diagrams/` - diagramy architektury / use-case / ERD (TikZ)
- `scripts/refresh_model_assets.ps1` - synchronizacja najnowszych artefaktów modelu

## Aktualizacja danych modelu
Uruchom z katalogu głównego repo:

```powershell
powershell -ExecutionPolicy Bypass -File raport/scripts/refresh_model_assets.ps1
```

## Kompilacja PDF
Przykład z katalogu `raport/`:

```powershell
pdflatex -interaction=nonstopmode main.tex
pdflatex -interaction=nonstopmode main.tex
```

Drugie uruchomienie buduje poprawny spis treści i odwołania.
