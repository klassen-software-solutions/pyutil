.PHONY: all analyze build check install

all: build

build:
	python3 setup.py sdist bdist_wheel

check:
	python3 -m unittest discover --start-directory Tests

analyze:
	pylint kss/util

install:
	python3 -m pip install --user .
