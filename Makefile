PYTHON_VERSION := python2
CLIENT := $(PYTHON_VERSION)_client
OUTPUT := ./build
FOE := $(OUTPUT)/.foe

.PHONY: clean run

build:
	if ! [ -d $(OUTPUT) ]; then mkdir $(OUTPUT); fi;\
	cp -r ./clients/$(CLIENT)/client/* $(OUTPUT);\
	cp -r ./strategy/* $(OUTPUT)/core

clean:
	rm -rf ./build

foe: build;
	if ! [ -d $(FOE) ]; then mkdir $(FOE); fi;\
	cp -r ./clients/$(CLIENT)/client/* $(FOE);\
	cp -r ./baseline/$(CLIENT)/* $(FOE)/core

install: clean build;
	dst=$(realpath $(OUTPUT))/$(notdir $(PWD)).zip;\
	cd ./strategy && zip -r $$dst .;\

run: clean foe;
	(python2 ./localrunner/world/run.py &) && sleep 1
	($(PYTHON_VERSION) $(FOE)/run.py &) && sleep 1
	$(PYTHON_VERSION) $(OUTPUT)/run.py