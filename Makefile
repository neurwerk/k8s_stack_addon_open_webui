SHELL := /bin/bash
.SHELLFLAGS := -eu -o pipefail -c
ADDON_TOOLING ?= $(WORKSPACE_ROOT)/tooling
CHART_DIRS := $(sort $(shell find charts -name Chart.yaml -printf '%h\n'))
PACKAGES := namespaces/open-webui open-webui/secret-sync open-webui/database open-webui/access open-webui/oidc open-webui/certificate-approval open-webui/app

.PHONY: check
check:
	uv run --frozen --project "$(ADDON_TOOLING)" addon-check "$(CURDIR)"
	@for chart in $(CHART_DIRS); do \
		helm lint --strict "$$chart" --values validation/helm-values.yaml; \
		helm template test "$$chart" --values validation/helm-values.yaml | kubeconform -strict -summary -ignore-missing-schemas; \
	done
	@for package in $(PACKAGES); do \
		kustomize build --load-restrictor LoadRestrictionsNone "releases/$$package" | kubeconform -strict -summary -ignore-missing-schemas; \
	done
