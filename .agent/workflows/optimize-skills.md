---
description: Optimér Antigravity skills baseret på samtale-feedback
---

# Optimize Skills Workflow

Denne workflow bruges til at forbedre SKILL.md-filer baseret på feedback fra samtaler.

## Forudsætninger
- `skill-optimizer` projektet er klonet og installeret (se README.md)
- `GEMINI_API_KEY` er sat i `.env`

## Trinvis guide

### 1. Se nuværende status
// turbo
```
python c:\Users\mikke\Projects\skill-optimizer\optimize.py status
```

### 2. Reflektér over samtalen

Tænk over den aktuelle session:
- Hvilke skills blev brugt (direkte eller indirekte)?
- Bad brugeren om rettelser eller ændringer?
- Udtrykte brugeren præferencer ("jeg foretrækker...", "brug altid...")?
- Er der nye udtryk der burde trigge en skill?

### 3. Injicér forslag

For hver observation, kør `inject`-kommandoen. Vælg den relevante kategori:

- **correction** — fejl der skal rettes ("det er forkert, det skal være...")
- **preference** — brugerpræferencer ("skriv altid på dansk", "brug korte sætninger")
- **trigger** — nye udtryk der bør aktivere skill'en ("madkombination", "hvad passer til")
- **improvement** — generelle forbedringer ("tilføj eksempler", "forklar mere")

```
python c:\Users\mikke\Projects\skill-optimizer\optimize.py inject --skill <skill-navn> --category <kategori> --content "<forslag>"
```

### 4. Preview ændringer
// turbo
```
python c:\Users\mikke\Projects\skill-optimizer\optimize.py apply
```

### 5. Bekræft og skriv ændringer
```
python c:\Users\mikke\Projects\skill-optimizer\optimize.py apply --confirm
```

### 6. Verificér
// turbo
```
python c:\Users\mikke\Projects\skill-optimizer\optimize.py status
```
