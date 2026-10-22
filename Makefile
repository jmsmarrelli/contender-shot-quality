# Pipeline stages share generated inputs and must run in order.
.NOTPARALLEL:
PY ?= python3

.PHONY: all build model teams figures clean site

all: verify-data build model teams

build:
	$(PY) src/run_01_build.py

model:
	$(PY) src/run_02_model.py

teams:
	$(PY) src/run_03_teams.py

# Re-cut every chart from the tables already in output/, fitting nothing.
figures:
	$(PY) src/run_03_teams.py --figures

# Regenerate the GitHub Pages page from README.md. Needs `pip install -r requirements.txt`.
site:
	$(PY) tools/site.py

clean:
	rm -f figures/*.png output/*.csv data/processed/*

.PHONY: fetch-data verify-data
fetch-data:
	$(PY) tools/fetch_data.py

verify-data:
	$(PY) tools/fetch_data.py --check

.PHONY: report
report:
	$(PY) tools/report.py
