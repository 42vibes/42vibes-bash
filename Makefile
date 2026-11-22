.PHONY: all build validate check sync-palette clean

all: build validate

build:
	python3 build.py

validate:
	python3 validate.py

check:
	python3 build.py --check
	python3 validate.py

sync-palette:
	cp ../42vibes-palette/palette.json vendor/palette.json
	@echo "vendor/palette.json aktualisiert"

clean:
	rm -rf __pycache__
