install:
	pip install --upgrade pip &&\
		pip install -r requirements.txt

format:
	black *.py

lint:
	pylint *.py

test:
	pytest -vv --cov=main

build:
	# build code

deploy:
	# deploy code

validate: format lint test

all: install format lint test build deploy

start:
	uvicorn main:app --reload