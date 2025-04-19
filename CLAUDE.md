# CLAUDE.md - Django Project Guidelines

## Commands
- Setup: `pip install -r requirements.txt && python manage.py migrate`
- Run server: `python manage.py runserver`
- Run all tests: `python manage.py test`
- Run single test: `python manage.py test conversation.tests.TestClass.test_method`
- Process emails: `python manage.py check_emails`
- Setup Gmail: `python manage.py setup_gmail`
- Celery worker: `celery -A casy worker -l info`
- Celery scheduler: `celery -A casy beat -l info`

## Code Style
- Imports: stdlib → Django → third-party → local (alphabetized within groups)
- Formatting: 4-space indentation, ~88 char line length, double quotes
- Types: Use typing annotations (Optional, List, Dict), Pydantic for validation
- Naming: snake_case (vars/funcs), PascalCase (classes), UPPERCASE (constants)
- Error handling: Specific exceptions, try/except with fallbacks, proper logging
- Documentation: Docstrings for classes/methods, inline comments for complex logic
- Testing: Django TestCase, mocks for external deps, specific test scenarios