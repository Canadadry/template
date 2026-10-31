.PHONY: help test check

help:
	@echo "make test    the fast loop: unit tests, on the host, in seconds"
	@echo "make check   the net: everything that must be green before a push"

# The fast loop. Keep it a few seconds, with no network and no external service.
test:
	python3 -m unittest discover -v tests

# The net. Add the slow checks here (lint, type check, integration, e2e...).
# A change that keeps it green is correct; one that breaks it is a bug.
check: test
