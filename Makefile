PYTHON   := /usr/bin/python3
ARTIFACT := Bambu-Recent.alfredworkflow
SOURCES  := info.plist bambu_recent.py $(wildcard icon.png)

.PHONY: build test clean

build: $(ARTIFACT)

$(ARTIFACT): $(SOURCES)
	rm -f $@
	zip -X -q $@ $(SOURCES)

test:
	$(PYTHON) -m unittest discover -s tests -t . -v

clean:
	rm -f $(ARTIFACT)
	find . -name __pycache__ -type d -prune -exec rm -rf {} +
