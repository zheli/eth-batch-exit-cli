.PHONY: test install lint clean

install:
	poetry install

test:
	poetry run pytest tests/

lint:
	poetry run pylint exit_validators.py

clean:
	rm -rf __pycache__
	rm -rf tests/__pycache__
	rm -rf .pytest_cache
