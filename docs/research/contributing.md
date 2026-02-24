# Contributing

We welcome contributions to AdversarialIaC-Bench!

## Ways to Contribute

### 🐛 Report Issues

Found a bug? [Open an issue](https://github.com/brianterry/Adversarial-IaC-Evaluation/issues/new).

### 📝 Improve Documentation

Documentation improvements are always welcome. Edit files in `docs/` and submit a PR.

### 🔧 Add Features

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a PR

### 🧪 Add Scenarios

Help expand our scenario coverage:

- New cloud providers (Azure, GCP)
- New IaC languages
- Domain-specific scenarios

### 📊 Share Results

Run experiments and share your findings:

- Model comparisons
- Vulnerability type analysis
- Multi-agent mode evaluations

## Development Setup

```bash
# Clone your fork
git clone https://github.com/YOUR_USERNAME/Adversarial-IaC-Evaluation.git
cd Adversarial-IaC-Evaluation

# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run linting
ruff check src/
```

## Code Style

- Use `ruff` for linting
- Follow PEP 8
- Add type hints
- Write docstrings for public APIs

## Pull Request Process

1. Update documentation if needed
2. Add tests for new features
3. Ensure all tests pass
4. Request review from maintainers

## Code of Conduct

Be respectful and constructive. We're all here to improve security research.
