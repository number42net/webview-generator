# Contributing to WebView Generator

Thank you for your interest in contributing to WebView Generator!

## How to Contribute

### Reporting Bugs

If you find a bug, please open an issue with:
- A clear description of the problem
- Steps to reproduce
- Expected vs actual behavior
- Your environment (OS, Python version, etc.)

### Suggesting Features

Feature requests are welcome! Please open an issue describing:
- The feature you'd like to see
- Why it would be useful
- Any implementation ideas

### Pull Requests

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Test thoroughly
5. Commit your changes (`git commit -m 'Add amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

## Development Setup

```bash
# Clone your fork
git clone https://github.com/yourusername/webview-generator.git
cd webview-generator

# Install dependencies
pip install -r requirements.txt

# Run tests (if you add any)
python -m pytest
```

## Code Style

- Follow PEP 8 for Python code
- Use meaningful variable names
- Add comments for complex logic
- Update documentation for new features

## Testing

Before submitting a PR:
1. Test the generator with various URLs
2. Verify APK builds successfully
3. Test the generated app on an Android device
4. Ensure no regressions in existing features

## Areas for Contribution

Some ideas for contributions:
- Add unit tests
- Support for additional icon sources
- App signing configuration
- Custom splash screens
- Advanced WebView options
- CI/CD integration
- Docker support
- GUI interface

## Questions?

Feel free to open an issue for any questions!
