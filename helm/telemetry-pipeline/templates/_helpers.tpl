{{/*
Expand the name of the chart.
*/}}
{{- define "telemetry-pipeline.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
*/}}
{{- define "telemetry-pipeline.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{- define "telemetry-pipeline.namespace" -}}
{{- .Values.namespace.name }}
{{- end }}

{{- define "telemetry-pipeline.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" }}
{{- end }}

{{- define "telemetry-pipeline.labels" -}}
helm.sh/chart: {{ include "telemetry-pipeline.chart" . }}
{{ include "telemetry-pipeline.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
app.kubernetes.io/part-of: telemetry-pipeline
{{- end }}

{{- define "telemetry-pipeline.selectorLabels" -}}
app.kubernetes.io/name: {{ include "telemetry-pipeline.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{- define "telemetry-pipeline.pipelineLabels" -}}
{{ include "telemetry-pipeline.labels" . }}
app: telemetry-pipeline
{{- end }}

{{- define "telemetry-pipeline.configMapName" -}}
{{- printf "%s-config" (include "telemetry-pipeline.fullname" .) }}
{{- end }}

{{- define "telemetry-pipeline.secretName" -}}
{{- if .Values.secrets.existingSecretName }}
{{- .Values.secrets.existingSecretName }}
{{- else }}
{{- printf "%s-secrets" (include "telemetry-pipeline.fullname" .) }}
{{- end }}
{{- end }}

{{- define "telemetry-pipeline.pipelineServiceName" -}}
{{- include "telemetry-pipeline.fullname" . }}
{{- end }}