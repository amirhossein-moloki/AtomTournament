# Test Suite

This directory contains the automated tests for the project.

## Running Tests Locally

To run the tests locally, ensure you have the project's dependencies installed, then run the following command from the root of the project:

```bash
python -m pytest tests/
```

## CI/CD

The tests are automatically run on each push and pull request using GitHub Actions. The workflow is defined in `.github/workflows/test.yml`.
