# Skill Optimizer — Brugermanual

## Hvad er det?

Skill Optimizer analyserer dine Antigravity-samtaler og forbedrer dine SKILL.md-filer automatisk. Den finder korrektioner, præferencer og nye trigger-udtryk.

## Quick Start

```bash
cd c:\Users\mikke\Projects\skill-optimizer

# Se status over alle 29 skills
python optimize.py status

# Kør en demo
python optimize.py demo

# Tilføj et forslag manuelt
python optimize.py inject --skill smagskombinator --category preference --content "Brug altid sæsonens grøntsager"

# Preview ændringer
python optimize.py apply

# Skriv ændringer til SKILL.md
python optimize.py apply --confirm
```

## Tre måder at optimere skills på

### 🅰️ Self-Reflection (anbefalet)

Kør `/optimize-skills` i Antigravity ved slutningen af en session. AI'en reflekterer over samtalen og genererer forslag.

**Workflow:**
1. Du bruger skills som normalt (f.eks. Smagskombinator, proofreader)
2. Sig `/optimize-skills` — eller kør workflowet manuelt
3. Antigravity identificerer: "Hvilke skills brugte jeg? Hvad bad brugeren om?"
4. For hvert forslag kører den `optimize.py inject`
5. Du reviewer med `optimize.py apply` og bekræfter med `--confirm`

### 🅱️ Artifact Mining (batch)

Analysér historiske samtaler via artifacts i brain-mappen:

```bash
# Analysér én samtale
python optimize.py mine --conversation cb7f013c-4c84-47c0-99de-9d8e7a013524

# Analysér de seneste 7 dages samtaler
python optimize.py mine --recent 7
```

### 🅲️ Manual Analyse (ad-hoc)

Paste en konversation eller peg på en fil:

```bash
# Fra fil
python optimize.py analyze --skill proofreader --file samtale.txt

# Fra clipboard (paste, afslut med Ctrl+Z/Ctrl+D)
python optimize.py analyze --skill proofreader
```

Konversationsformat:
```
USER: Kan du rette denne tekst?
ASSISTANT: Her er den rettede version...
USER: Nej, behold de danske anførselstegn
ASSISTANT: Beklager, her er teksten med danske anførselstegn...
```

## Kommandooversigt

| Kommando | Beskrivelse |
|----------|-------------|
| `status [--skill X]` | Vis ventende forslag og metrics |
| `inject --skill X --category Y --content "Z"` | Tilføj ét forslag |
| `apply [--confirm] [--skill X] [--all]` | Preview / skriv ændringer |
| `demo` | Kør demo med Smagskombinator |
| `analyze --skill X [--file F]` | Analysér en samtale |
| `mine --conversation ID` / `--recent N` | Mine brain-artifacts |

## Kategorier

| Kategori | Hvornår | Eksempel |
|----------|---------|---------|
| `correction` | Brugeren rettede AI'en | "Brug **ikke** engelske udtryk" |
| `preference` | Brugeren udtrykte en præference | "Skriv altid på dansk" |
| `trigger` | Nyt udtryk der bør aktivere en skill | "madkombination" |
| `improvement` | Generel forbedring | "Tilføj eksempler i svar" |

## Konfiguration

Miljøvariabler (sættes i `.env`):

| Variabel | Default | Beskrivelse |
|----------|---------|-------------|
| `GEMINI_API_KEY` | — | API-nøgle til Gemini |
| `ANTHROPIC_API_KEY` | — | API-nøgle til Anthropic |
| `SKILLS_DIR` | `~/.gemini/antigravity/skills` | Sti til skills |
| `BRAIN_DIR` | `~/.gemini/antigravity/brain` | Sti til samtalelogs |
| `OPTIMIZER_PROVIDER` | `gemini` | LLM-provider |

## Sikkerhedsnet

- **Dry-run by default**: `apply` viser altid et preview uden at skrive
- **Backup**: SKILL.md-filer er i Git — du kan altid rulle tilbage
- **200-tegn grænse**: Beskrivelser afkortes aldrig over Antigravity's max
- **Deduplikering**: Samme forslag tilføjes aldrig to gange
