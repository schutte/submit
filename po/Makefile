#!/usr/bin/make -f

LANGUAGES = de
MOFILES = $(patsubst %,%.mo,$(LANGUAGES))

all: LINGUAS $(MOFILES)

%.mo: %.po
	msgfmt -o $@ $<

LINGUAS:
	echo "# Please edit Makefile instead of this file" >LINGUAS
	echo $(LANGUAGES) >>LINGUAS

clean:
	rm -f $(MOFILES)
