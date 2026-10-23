{{/* Adapt LibreChat's catalog projection: only route IDs and display names leave the catalog. */}}
{{- define "open-webui.mcpConnections" -}}
{{- $connections := list -}}
{{- if .Values.frontendOpenWebui.mcp.enabled -}}
{{- if hasKey .Values "mcp" }}{{ fail "root mcp has been removed; use mcp-servers" }}{{ end -}}
{{- $mcp := index .Values "mcp-servers" -}}
{{- if not $mcp.enabled }}{{ fail "Open WebUI MCP requires mcp-servers.enabled" }}{{ end -}}
{{- if hasKey $mcp "servers" }}{{ fail "mcp-servers.servers has been removed; configure mcp-servers.catalog" }}{{ end -}}
{{- $catalog := $mcp.catalog | default dict -}}
{{- $routes := $mcp.contextforgeRoutesEnabled | default list -}}
{{- $known := dict -}}
{{- range $id, $selection := $catalog.presets | default dict -}}
{{- if $selection.enabled -}}
{{/* Base's presets are ContextForge-backed and require explicit route publication. */}}
{{- $_ := set $known $id (dict "name" ($selection.displayName | default $id) "routed" (has $id $routes)) -}}
{{- end -}}
{{- end -}}
{{- range $entry := $catalog.custom | default list -}}
{{- if $entry.enabled -}}
{{- if hasKey $known $entry.name }}{{ fail "duplicate enabled MCP catalog ID" }}{{ end -}}
{{- $_ := set $known $entry.name (dict "name" ($entry.displayName | default $entry.name) "routed" (or (not $entry.contextforge) (has $entry.name $routes))) -}}
{{- end -}}
{{- end -}}
{{- range $id := .Values.frontendOpenWebui.mcp.servers -}}
{{- if not (hasKey $known $id) }}{{ fail (printf "Open WebUI MCP server %s must be an enabled catalog selection" $id) }}{{ end -}}
{{- $entry := get $known $id -}}
{{- if not $entry.routed }}{{ fail (printf "Open WebUI MCP server %s requires contextforgeRoutesEnabled" $id) }}{{ end -}}
{{- $connection := dict
  "type" "mcp"
  "url" (printf "%s/mcp/%s" $.Values.frontendOpenWebui.agentGateway.origin $id)
  "path" ""
  "auth_type" "system_oauth"
  "key" ""
  "forward_cookies" false
  "headers" (dict "X-Session-ID" "{{CHAT_ID}}")
  "config" (dict "enable" true "access_grants" (list (dict "principal_type" "user" "principal_id" "*" "permission" "read")))
  "info" (dict "id" $id "name" $entry.name) -}}
{{- $connections = append $connections $connection -}}
{{- end -}}
{{- end -}}
{{- $connections | toJson -}}
{{- end -}}
