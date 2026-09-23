PY := python3

.PHONY: all build model teams figures clean site

all: build model teams

build:
	$(PY) src/run_01_build.py

model:
	$(PY) src/run_02_model.py

teams:
	$(PY) src/run_03_teams.py

# Re-cut every chart from the tables already in output/, fitting nothing.
figures:
	$(PY) src/run_03_teams.py --figures

# Regenerate the GitHub Pages page from README.md. Needs `pip install markdown`.
site:
	$(PY) tools/site.py

clean:
	rm -f figures/*.png output/*.csv data/processed/*
