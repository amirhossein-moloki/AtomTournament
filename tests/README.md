# Test Suite

This directory contains the automated tests for the Django project.

## Running Tests Locally

To run the full test suite and generate coverage reports, use the following command from the root of the project:

```bash
export PYTHONPATH=$PYTHONPATH:$(pwd) && python -m pytest tests/ --ds=tournament_project.settings --cov=. --cov-report=term-missing --cov-report=json:reports/coverage.json --junitxml=reports/test_results.xml
```

This command will:
- Run all tests located in the `tests/` directory.
- Use the `tournament_project.settings` Django settings file.
- Generate a code coverage report in `reports/coverage.json` and print a summary to the console.
- Generate a JUnit XML test report in `reports/test_results.xml`.
- Enforce the `fail_under = 90` rule defined in `.coveragerc`.

## CI/CD

Tests are run automatically on every push and pull request to the `main` branch via GitHub Actions. The workflow is defined in `.github/workflows/test.yml`.
