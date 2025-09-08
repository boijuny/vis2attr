# Contributing to vis2attr

Thank you for your interest in contributing to vis2attr! This document provides guidelines and information for contributors.

## 🚀 Quick Start

1. **Fork the repository** on GitHub
2. **Clone your fork** locally
3. **Create a feature branch** from `dev`
4. **Make your changes** and add tests
5. **Submit a pull request** to `dev`

## 🛠️ Development Setup

```bash
# Clone your fork
git clone https://github.com/boijuny/vis2attr.git
cd vis2attr

# Create virtual environment
uv venv && source .venv/bin/activate

# Install in development mode
uv pip install -e ".[dev]"

# Install pre-commit hooks
pre-commit install
```

## 📋 Development Workflow

### Branch Strategy
- `main`: Production-ready code
- `dev`: Development branch (default for PRs)
- `feature/*`: Feature branches
- `fix/*`: Bug fix branches

### Code Style
- **Python**: Black formatting, isort imports, mypy type checking
- **Line length**: 88 characters
- **Type hints**: Required for all functions
- **Docstrings**: Google style for all public functions

### Testing
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src/vis2attr

# Run specific test file
pytest tests/test_cli_analyze.py
```

### Pre-commit Checks
```bash
# Run all checks
pre-commit run --all-files

# Run specific check
pre-commit run black
pre-commit run mypy
```

## 📝 Pull Request Guidelines

### Before Submitting
- [ ] Code follows project style guidelines
- [ ] All tests pass
- [ ] New features have tests
- [ ] Documentation updated if needed
- [ ] Pre-commit hooks pass

### PR Description
Include:
- **What**: Brief description of changes
- **Why**: Motivation and context
- **How**: Implementation details
- **Testing**: How you tested the changes

### Example PR Title
```
feat: add progress indicators to CLI analyze command
fix: resolve storage query interface issue
docs: update installation instructions
```

## 🐛 Bug Reports

When reporting bugs, please include:
- **Environment**: OS, Python version, package versions
- **Steps to reproduce**: Clear, minimal steps
- **Expected behavior**: What should happen
- **Actual behavior**: What actually happens
- **Error messages**: Full error output if applicable

## 💡 Feature Requests

For new features:
- **Use case**: Why is this needed?
- **Proposed solution**: How should it work?
- **Alternatives**: Other approaches considered
- **Implementation**: Any technical details

## 🔧 Code Review Process

### For Contributors
- Address all review comments
- Keep PRs focused and reasonably sized
- Respond to feedback promptly
- Be open to suggestions

### For Reviewers
- Be constructive and respectful
- Focus on code quality and maintainability
- Test the changes locally when possible
- Provide clear, actionable feedback

## 📚 Documentation

### Code Documentation
- **Docstrings**: All public functions and classes
- **Type hints**: Required for all functions
- **Comments**: Explain complex logic

### User Documentation
- **README**: Keep up to date
- **Examples**: Add usage examples
- **API docs**: Document public interfaces

## 🧪 Testing Guidelines

### Test Coverage
- **New features**: Must have tests
- **Bug fixes**: Include regression tests
- **Coverage target**: Maintain >90% coverage

### Test Types
- **Unit tests**: Individual components
- **Integration tests**: Component interactions
- **CLI tests**: Command-line interface
- **End-to-end tests**: Full pipeline

### Test Structure
```python
def test_feature_name():
    """Test description."""
    # Arrange
    input_data = create_test_data()
    
    # Act
    result = function_under_test(input_data)
    
    # Assert
    assert result.expected_property == expected_value
```

## 🚨 Security

- **API Keys**: Never commit API keys or secrets
- **Dependencies**: Keep dependencies updated
- **Vulnerabilities**: Report security issues privately
- **Input validation**: Validate all user inputs

## 📞 Getting Help

- **GitHub Issues**: For bugs and feature requests
- **Discussions**: For questions and general discussion
- **Code Review**: Ask questions in PR comments

## 📄 License

By contributing to vis2attr, you agree that your contributions will be licensed under the MIT License.

---

Thank you for contributing to vis2attr! 🎉
