PYTHON_VERSION := python2
CLIENT := $(PYTHON_VERSION)_client
OUTPUT := ./build
FOE := $(OUTPUT)/.foe
TEST := strategy_utils.py strategy.py

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
	tmp=$(OUTPUT)/.tmp_install;\
	mkdir $$tmp;\
	find ./strategy/ -type f -exec ./copy_source.sh '{}' "$$tmp" ';';\
	dst=$(realpath $(OUTPUT))/$(notdir $(PWD)).zip;\
	cd $$tmp && $(PYTHON_VERSION) -m compileall ./ \
		&& find . -type f -iname '*.py[co]' -exec rm -f '{}' ';' \
		&& zip -r $$dst .

run: clean foe;
	(python2 ./localrunner/world/run.py &) && sleep 1
	($(PYTHON_VERSION) $(FOE)/run.py &) && sleep 1
	$(PYTHON_VERSION) $(OUTPUT)/run.py

test: clean build;
	cd ./build/core;\
	for file in $(TEST); do\
		echo "TESTING $$file...";\
		python2 "$$file";\
		echo;\
	done