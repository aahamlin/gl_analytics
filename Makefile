
MODULE=gl_analytics


all:
	@echo "Makefile options:"
	@echo "  init - setup pipenv"
	@echo "  run  - run Flask app"
	@echo "  test - run pytests"

init:
	pipenv install --dev

run:
	pipenv run python -m $(MODULE)

test:
	pipenv run coverage run --source=$(MODULE) -m pytest tests
	pipenv run coverage report -m

.PHONY: all init test
