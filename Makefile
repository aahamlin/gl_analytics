
MODULE=gl_analytics


all:
	@echo "Available Targets:"
	@echo "  init\t\tsetup pipenv"
	@echo "  test\t\trun pytests"
	@echo "  test_e2e\texecute canned query against gitlab.com"
	@echo ""
	@echo "Run command line: pipenv run python -m gl_analitics --help"

init:
	pipenv install --dev

test_e2e:
	pipenv run python -m $(MODULE) --help
	pipenv run python -m $(MODULE)

test:
	PIPENV_DONT_LOAD_ENV=1 pipenv run coverage run --source=$(MODULE) -m pytest
	pipenv run coverage report -m

.PHONY: all init test test_e2e
