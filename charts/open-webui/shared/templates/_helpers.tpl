{{- define "open-webui.modelConnections" -}}
{{- $known := dict -}}
{{- $upstreams := dict -}}
{{- $catalogNames := dict -}}
{{- $excluded := .Values.openrouterCatalog.excludedModels | default list -}}
{{- if ne (len $excluded) (len ($excluded | uniq)) }}{{ fail "duplicate excluded catalog model" }}{{ end -}}
{{- range $model := .Values.openrouterCatalog.models -}}
{{- if or (hasKey $upstreams $model.upstreamModel) (hasKey $catalogNames $model.name) }}{{ fail "duplicate canonical catalog model" }}{{ end -}}
{{- $_ := set $upstreams $model.upstreamModel true -}}
{{- $_ := set $catalogNames $model.name true -}}
{{- if and $.Values.openrouterCatalog.enabled (not (has $model.upstreamModel $excluded)) }}{{ $_ := set $known $model.name true }}{{ end -}}
{{- end -}}
{{- range $excluded }}{{ if not (hasKey $upstreams .) }}{{ fail "unknown excluded catalog model" }}{{ end }}{{ end -}}
{{- $custom := dict -}}
{{- range $model := .Values.guardrails.llmPolicyEngine.models -}}
{{- if hasKey $custom $model.name }}{{ fail "duplicate client model" }}{{ end -}}
{{- $_ := set $custom $model.name true -}}
{{- $_ := set $known $model.name true -}}
{{- end -}}
{{- $urls := list -}}{{- $keys := list -}}{{- $configs := dict -}}{{- $routed := dict -}}{{- $bindingIds := dict -}}
{{- range $group := list "self-hosted-api-providers" "external-api-providers" -}}
{{- range $binding := index $.Values $group -}}
{{- if hasKey $bindingIds $binding.id }}{{ fail "duplicate API binding id" }}{{ end -}}
{{- $_ := set $bindingIds $binding.id true -}}
{{- $api := ($binding.routes | default dict).api | default dict -}}
{{- $sources := $binding.credentialSources | default list -}}
{{- range $source := $sources -}}
{{- if not (has $source (list "global" "override" "none")) }}{{ fail "binding credentialSources accepts only global, override or none" }}{{ end -}}
{{- end -}}
{{- $global := has "global" $sources -}}
{{- $local := and (eq $group "self-hosted-api-providers") (eq (toJson $sources) `["none"]`) -}}
{{- if and $binding.enabled (eq (toJson $api.enabled) "true") (has "openai-chat-completions-v1" ($binding.profiles | default list)) (or $global $local) -}}
{{- $selected := $binding.catalogModels | default list -}}
{{- range $model := $binding.models | default list -}}
{{- $selected = append $selected $model.name -}}
{{- $_ := set $known $model.name true -}}
{{- end -}}
{{- if $selected -}}
{{- range $name := $selected -}}
{{- if not (hasKey $known $name) }}{{ fail (printf "unknown binding catalog model %s" $name) }}{{ end -}}
{{- if hasKey $routed $name }}{{ fail (printf "ambiguous API binding for model %s" $name) }}{{ end -}}
{{- $_ := set $routed $name true -}}
{{- end -}}
{{- $path := $api.path | default (printf "/bindings/%s" $binding.id) -}}
{{- if not (regexMatch `^/[a-zA-Z0-9/_-]+$` $path) }}{{ fail "invalid AgentGateway API path" }}{{ end -}}
{{- $url := printf "%s%s/v1" (trimSuffix "/" $.Values.frontendOpenWebui.agentGateway.origin) (trimSuffix "/" $path) -}}
{{- $_ := set $configs (len $urls | toString) (dict "enable" true "auth_type" "system_oauth" "model_ids" $selected) -}}
{{- $urls = append $urls $url -}}{{- $keys = append $keys "" -}}
{{- end -}}
{{- end -}}
{{- end -}}
{{- end -}}
{{- if not $urls }}{{ fail "Open WebUI requires at least one explicit AgentGateway model binding" }}{{ end -}}
{{- if gt (len $routed) 256 }}{{ fail "Open WebUI supports at most 256 model destinations" }}{{ end -}}
{{/* The shared catalog can also contain override-only, Responses-only or unselected models. */}}
{{- $default := .Values.frontendOpenWebui.agentGateway.defaultModel -}}
{{- if and $default (not (hasKey $routed $default)) }}{{ fail "default model must belong to an explicit API binding" }}{{ end -}}
{{- dict "urls" (join ";" $urls) "keys" (join ";" $keys) "configs" $configs | toYaml -}}
{{- end -}}
