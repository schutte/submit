#!/usr/bin/make -f

ARTICLES = manual
MANPAGES_1 = submit

ARTICLES_HTML = $(patsubst %,%.html,$(ARTICLES))

MANPAGES_1_HTML = $(patsubst %,%.1.html,$(MANPAGES_1))
MANPAGES_1_GROFF = $(patsubst %,%.1,$(MANPAGES_1))

all: $(ARTICLES_HTML) $(MANPAGES_1_HTML) $(MANPAGES_1_GROFF)

$(ARTICLES_HTML): %.html: %.adc
	asciidoc -n -a toc $<

$(MANPAGES_1_HTML): %.html: %.adc
	asciidoc -d manpage $<

$(MANPAGES_1_GROFF): %: %.adc
	a2x --no-xmllint -f manpage $<

clean:
	rm -f *.html *.1 *.xml
