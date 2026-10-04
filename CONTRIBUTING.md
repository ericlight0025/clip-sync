# Contributing to Shared Paste Dashboard

Thank you for your interest in contributing!

## How to Contribute

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature-name`
3. Commit your changes: `git commit -m "feat: describe your change"`
4. Push to your fork: `git push origin feature/your-feature-name`
5. Open a Pull Request

## Guidelines

- Keep changes focused — one feature or fix per PR
- Follow the existing code style (snake_case, Traditional Chinese comments)
- Test your changes before submitting

Run `python -m unittest discover -s tests -v` and `python -m compileall -q .` before committing. Tests must use temporary directories and must not access production shared folders. For changes to synchronization or packaging, also follow the Windows checks in `docs/review-fixes-2026-10-04.md`.

## Reporting Issues

Please open an issue with a clear description and steps to reproduce.

## License

By contributing, you agree that your contributions will be licensed under the [MIT License](LICENSE).
