{{- define "open-webui.selectorLabels" -}}
app.kubernetes.io/name: frontend-open-webui
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end -}}
{{- define "open-webui.labels" -}}
{{ include "open-webui.selectorLabels" . }}
app.kubernetes.io/part-of: frontend-open-webui
app.kubernetes.io/component: app
app.kubernetes.io/managed-by: {{ .Release.Service }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
helm.sh/chart: {{ printf "%s-%s" .Chart.Name .Chart.Version }}
{{- end -}}
