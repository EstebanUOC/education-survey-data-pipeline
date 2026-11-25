.PHONY: data run run-r test all
data:
	python scripts/generate_synthetic_data.py --out data/raw
run:
	python -m pipeline --input data/raw --output outputs
run-r:
	Rscript R/analysis.R data/raw outputs
test:
	pytest -q
all: data run run-r test
