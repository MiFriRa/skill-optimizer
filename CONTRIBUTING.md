# Contributing to Skill Optimizer

Thanks for your interest! This is a small project, but contributions are welcome.

## Getting Started

```bash
git clone https://github.com/MiFriRa/skill-optimizer.git
cd skill-optimizer
python -m venv .venv
.venv\Scripts\activate    # Windows
pip install -e ".[dev]"
```

## Running Tests

```bash
pytest test/
```

## Making Changes

1. Fork the repo
2. Create a feature branch (`git checkout -b feature/my-idea`)
3. Make your changes
4. Run tests (`pytest test/`)
5. Commit with a descriptive message
6. Open a pull request

## Suggestion Categories

When adding new suggestion types, follow the existing categories:
- `correction` — mistakes to fix
- `preference` — user style preferences
- `trigger` — new activation phrases
- `improvement` — general improvements

## Code Style

- Python 3.9+
- Type hints where practical
- Docstrings on public methods

## Attribution

This project is forked from [meet-rocking/skill-optimizer](https://github.com/meet-rocking/skill-optimizer). Please respect the original MIT license.
