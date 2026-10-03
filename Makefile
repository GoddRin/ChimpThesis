# Aparri pipeline. `make setup && make test` must pass on a clean checkout.
PY := .venv/bin/python
.PHONY: setup test audit audit-gee clean-lines raster-lines compare transects risk tables maps sensitivity survey web annex all

setup:
	uv venv .venv -q || python3 -m venv .venv
	uv pip install -q -p $(PY) -e . || $(PY) -m pip install -q -e .

test:
	$(PY) -m pytest

audit:            ## Phase 2  : forensic audit of legacy lines + risk polygons
	$(PY) -m aparri.audit
audit-gee:        ## Phase 2B : forensic audit of the Earth Engine pipeline
	$(PY) -m aparri.audit_gee
clean-lines:      ## Phase 3A : clean the vector shorelines
	$(PY) -m aparri.clean
raster-lines:     ## Phase 3B : lines traced from the Earth Engine rasters + comparison
	$(PY) -m aparri.raster_shore
transects:        ## Phase 4  : transects and change metrics for the configured shoreline_set
	$(PY) -m aparri.transects
risk:             ## Phase 5  : classification and risk layers
	$(PY) -m aparri.risk
tables:           ## Phase 5  : Table 4.2 etc.
	$(PY) -m aparri.tables
maps:             ## Phase 5  : thesis figures
	$(PY) -m aparri.maps
sensitivity:      ## Phase 6
	$(PY) -m aparri.sensitivity
survey:           ## Phase 7  : survey template + validator (needs real data for outputs)
	$(PY) -m aparri.stats_survey
web:              ## Phase 8  : static interactive map
	$(PY) -m aparri.web
annex:            ## Phase 10E: technical annex
	$(PY) -m aparri.annex
all: audit audit-gee clean-lines raster-lines transects risk tables maps sensitivity web
landsat:          ## Phase 3C : sub-pixel shorelines from index rasters exported by scripts/gee_v2.js
	$(PY) -m aparri.landsat
priority:         ## Phase 10C : barangay ranking for field inspection (weights in config)
	$(PY) -m aparri.priority
qgis:             ## Phase 10D : QGIS project
	$(PY) -m aparri.qgis_project
drafts:           ## Phase 9   : generated draft documents
	$(PY) -m aparri.drafts
annex-docs: annex drafts priority qgis deck   ## Phase 9/10 documents
deck:             ## Phase 10F : defense slides (PPTX)
	$(PY) -m aparri.deck
