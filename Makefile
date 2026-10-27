SHELL := /bin/bash
.SHELLFLAGS := -eu -o pipefail -c
.DEFAULT_GOAL := check
TOOLING := uv run --locked --project tooling
TOOLING_IMAGE := ghcr.io/neurwerk/k8s-stack-addon-open-webui-tooling
CHART_DIRS := $(sort $(shell find charts -name Chart.yaml -printf '%h\n'))

.PHONY: check tooling-check tooling-build tooling-candidate-check
tooling-candidate-check:
	python3 validation/candidate_check.py --tooling-wheel "$(TOOLING_WHEEL)" --tooling-sha256 "$(TOOLING_SHA256)" --setup-wheel "$(SETUP_WHEEL)" --setup-sha256 "$(SETUP_SHA256)" --base "$(BASE_REPO)"

tooling-check:
	$(TOOLING) ruff check --config tooling/pyproject.toml tooling validation/candidate_check.py
	$(TOOLING) ruff format --check --config tooling/pyproject.toml tooling validation/candidate_check.py
	$(TOOLING) ty check --project tooling
	BASE_REPO="$(BASE_REPO)" $(TOOLING) pytest tooling/tests

tooling-build:
	@test -n "$(VERSION)" -a -n "$(REVISION)" || { echo 'Set VERSION and REVISION for image metadata'; exit 1; }
	docker build --build-arg VERSION="$(VERSION)" --build-arg REVISION="$(REVISION)" -t "$(TOOLING_IMAGE):$(VERSION)" tooling

check: tooling-check
	@test -n "$(BASE_REPO)" || { echo 'Set BASE_REPO to the exact selected Base checkout'; exit 1; }
	$(TOOLING) open-webui-validate "$(CURDIR)"
	$(TOOLING) addon-check "$(CURDIR)" --base "$(BASE_REPO)"
	@for chart in $(CHART_DIRS); do \
		helm lint --strict "$$chart" --values validation/helm-values.yaml; \
		helm template test "$$chart" --values validation/helm-values.yaml | kubeconform -strict -summary -ignore-missing-schemas; \
	done
	@packages="$$($(TOOLING) open-webui-validate "$(CURDIR)" --list-packages)"; \
	for package in $$packages; do \
		kustomize build --load-restrictor LoadRestrictionsNone "$$package" | kubeconform -strict -summary -ignore-missing-schemas; \
	done
