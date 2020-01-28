.PHONY: prep build check analyze

build:
	echo TODO: build the package
	BuildSystem/common/license_scanner.py

prep:
	echo TODO: auto preparation

prereqs:
	BuildSystem/common/update_prereqs.py

check: build
	echo TODO: run tests

analyze:
	echo TODO: run analyze
