Plan: Skill Optimizer → Antigravity Adaptation
Hvad er skill-optimizer?
Et Python-bibliotek (MIT-licens) der:

Tracker bruger-AI-konversationer (beskeder + skill-brug).
Analyserer dem med en LLM (Claude) for at finde korrektioner, præferencer og nye triggers.
Opdaterer SKILL.md-filer automatisk med forbedringer.
IMPORTANT

Projektet er bygget til Claude Code (.claude/skills/). Din setup bruger Google Antigravity (.gemini/antigravity/skills/). Formatet er tæt nok til, at en adaptation er praktisk mulig.

Trin-for-trin plan
Trin 1: Fork og klargør
 Fork meet-rocking/skill-optimizer på GitHub.
 Klon din fork lokalt: git clone <din-fork-url>
 Opret et Python virtual environment: python -m venv .venv
 Installer afhængigheder: pip install -e . (editable mode)
Trin 2: Tilpas stier (Directory Mapping)
Ændr standardstien fra Claude's format til Antigravity's:

diff
- skills_dir = ".claude/skills"
+ skills_dir = "C:/Users/mikke/.gemini/antigravity/skills"
NOTE

Antigravity bruger mappenavne med mellemrum og danske tegn (f.eks. Djævelens Advokat/SKILL.md). Tjek at koden håndterer Unicode-stier korrekt.

Trin 3: Tilpas SKILL.md-formatet
Skill-optimizer forventer denne struktur:

yaml
---
name: dashboard
description: "Create dashboards. Triggers: 'analytics', 'charts'"
---
# Dashboard Skill
...
Antigravity bruger næsten samme format:

yaml
---
name: proofreader
description: Korrekturlæsning, sproglig præcision og litterær flow-optimering (Dansk).
---
# SKILL: proofreader
...
Ændringer:

 Sikr at parseren bevarer dine eksisterende sektioner (## 🎭 Persona, ## 🛠️ Protokoller) og kun tilføjer nye sektioner (## User Preferences, ## Learned Corrections, ## Metrics).
 Find apply()-funktionen i kildekoden og justér den, så den appender nye sektioner i bunden af filen i stedet for at overskrive.
 Beskrivelsesgrænsen i Antigravity er 200 tegn. Sørg for at description-feltet ikke overskrides, når nye triggers tilføjes.
Trin 4: Skift LLM-backend (Claude → Gemini)
Skill-optimizer bruger Claude's API via anthropic-biblioteket. Du har to muligheder:

Option A: Behold Claude (nemmest)

 Brug din eksisterende Anthropic API-nøgle.
 Ingen kodeændringer nødvendige i LLM-laget.
Option B: Skift til Gemini API (fuld kontrol)

 Erstat anthropic-klienten med google-genai (Gemini API).
 Find analyse-prompten i kildekoden (den der sender konversationshistorik til Claude) og portér den til Gemini's format.
 Opdatér model-parameteren fra claude-sonnet-4-20250514 til f.eks. gemini-2.0-flash.
TIP

Anbefaling: Start med Option A for hurtig validering. Skift til Option B senere, hvis du vil undgå afhængighed af Anthropic.

Trin 5: Byg en integrationsbro
Skill-optimizer kræver, at du manuelt feeder konversationer ind via session.add_message(). Den integrerer ikke automatisk med Antigravity's chat-flow.

Praktiske muligheder:

 Manuel brug: Kør optimizer'en som et separat script efter en session. Kopiér relevante samtale-uddrag ind.
 Samtale-log mining: Skriv et script der læser Antigravity's konversationslogs fra C:\Users\mikke\.gemini\antigravity\brain\<conversation-id>\.system_generated\logs\ og konverterer dem til add_message()-kald.
 Periodisk batch-kørsel: Opret et cron-job / scheduled task der kører optimizeren dagligt på de seneste konversationer.
Trin 6: Test med én skill
 Vælg én lav-risiko skill (f.eks. Smagskombinator).
 Kør optimizer med en håndfuld faktiske konversationer.
 Gennemgå de genererede forslag (suggestions.json) — godkend med dry_run=True før du applicerer.
 Verificér at SKILL.md-filen stadig er valid og loadbar af Antigravity.
Trin 7: Skalér og automatisér
 Kør optimizer på alle 26+ skills.
 Commit ændringerne til Git (du har allerede versionering!).
 Overvej at bygge en daglig optimize.py-rutine.
Risici og overvejelser
Risiko	Konsekvens	Mitigation
Optimizer overskriver eksisterende sektioner	Tab af persona/protokol-instrukser	Brug dry_run=True og review altid først
Unicode-stier fejler	Skills med danske tegn ignoreres	Test tidligt med Djævelens Advokat
Description overskrider 200 tegn	Antigravity kan ikke routers skill	Tilføj maxlength-check i apply()
Konversationslogs mangler kontekst	Dårlig analyse fra LLM	Feed kun relevante samtaler ind
Estimeret tidsforbrug
Trin	Tid
Fork + setup	15 min
Sti-tilpasning	30 min
SKILL.md format	1-2 timer
LLM-backend (Option A)	5 min
LLM-backend (Option B)	1-2 timer
Integrationsbro	2-4 timer
Test + validering	1 time
Total (Option A)	~5-8 timer
