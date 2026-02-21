.PHONY: prepare-toilets build prepare-all

prepare-toilets:
	python3 -m scripts.prepare.prepare_friendly_toilets

build:
	python3 build_places.py

prepare-all: prepare-toilets

PYTHON := python3
PIP := $(PYTHON) -m pip
VENV := .venv
REQ := requirements.txt

.PHONY: help venv install upgrade freeze clean

help:
	@echo "Available commands:"
	@echo "  make venv      Create virtual environment"
	@echo "  make install   Install requirements"
	@echo "  make upgrade   Upgrade pip + install requirements"
	@echo "  make freeze    Freeze installed packages into requirements.txt"
	@echo "  make clean     Remove virtual environment"

venv:
	$(PYTHON) -m venv $(VENV)

install: venv
	$(VENV)/bin/python -m pip install --upgrade pip
	$(VENV)/bin/pip install -r $(REQ)

upgrade: venv
	$(VENV)/bin/pip install --upgrade pip setuptools wheel
	$(VENV)/bin/pip install --upgrade -r $(REQ)

freeze:
	$(VENV)/bin/pip freeze > $(REQ)

clean:
	rm -rf $(VENV)

