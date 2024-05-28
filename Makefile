install:
	pip install --upgrade pip &&\
		pip install -r requirements.txt

format:
	black --line-length=120 **/*.py

lint:
	pylint --max-line-length=120 --max-args=6 orders_service/**/*.py

test-orders:
	pytest tests/orders -vv --cov-config=tests/orders/.coveragerc --cov=orders_service --cov-report=term-missing

test: test-orders

build:
	# build code

deploy:
	# deploy code

validate: format lint test

all: install format lint test build deploy

start:
	uvicorn main:app --reload

start-orders:
	uvicorn orders_service.app:app --port 8000 --reload