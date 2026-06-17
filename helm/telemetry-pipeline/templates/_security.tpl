{{/*
Pod Security Standard labels for the release namespace.
*/}}
{{- define "telemetry-pipeline.podSecurityLabels" -}}
{{- if .Values.podSecurity.enabled }}
pod-security.kubernetes.io/enforce: {{ .Values.podSecurity.enforce | quote }}
pod-security.kubernetes.io/warn: {{ .Values.podSecurity.warn | quote }}
pod-security.kubernetes.io/audit: {{ .Values.podSecurity.audit | quote }}
{{- end }}
{{- end }}

{{/*
Restricted-style pod security context for Python workloads.
*/}}
{{- define "telemetry-pipeline.pythonPodSecurityContext" -}}
{{- $cfg := .Values.podSecurity.pipeline }}
{{- if .Values.podSecurity.enabled }}
runAsNonRoot: true
runAsUser: {{ $cfg.runAsUser }}
runAsGroup: {{ $cfg.runAsGroup }}
fsGroup: {{ $cfg.fsGroup }}
seccompProfile:
  type: RuntimeDefault
{{- end }}
{{- end }}

{{- define "telemetry-pipeline.pythonContainerSecurityContext" -}}
{{- $cfg := .Values.podSecurity.pipeline }}
{{- if .Values.podSecurity.enabled }}
allowPrivilegeEscalation: false
readOnlyRootFilesystem: {{ $cfg.readOnlyRootFilesystem }}
capabilities:
  drop:
    - ALL
{{- end }}
{{- end }}

{{- define "telemetry-pipeline.timescalePodSecurityContext" -}}
{{- $cfg := .Values.podSecurity.timescaledb }}
{{- if .Values.podSecurity.enabled }}
runAsNonRoot: true
runAsUser: {{ $cfg.runAsUser }}
fsGroup: {{ $cfg.fsGroup }}
seccompProfile:
  type: RuntimeDefault
{{- end }}
{{- end }}

{{- define "telemetry-pipeline.timescaleContainerSecurityContext" -}}
{{- if .Values.podSecurity.enabled }}
allowPrivilegeEscalation: false
capabilities:
  drop:
    - ALL
{{- end }}
{{- end }}

{{- define "telemetry-pipeline.victoriametricsPodSecurityContext" -}}
{{- $cfg := .Values.podSecurity.victoriametrics }}
{{- if .Values.podSecurity.enabled }}
runAsNonRoot: true
runAsUser: {{ $cfg.runAsUser }}
runAsGroup: {{ $cfg.runAsGroup }}
fsGroup: {{ $cfg.fsGroup }}
seccompProfile:
  type: RuntimeDefault
{{- end }}
{{- end }}

{{- define "telemetry-pipeline.victoriametricsContainerSecurityContext" -}}
{{- if .Values.podSecurity.enabled }}
allowPrivilegeEscalation: false
capabilities:
  drop:
    - ALL
{{- end }}
{{- end }}

{{- define "telemetry-pipeline.redpandaContainerSecurityContext" -}}
{{- if .Values.podSecurity.enabled }}
allowPrivilegeEscalation: false
capabilities:
  drop:
    - ALL
{{- end }}
{{- end }}

{{- define "telemetry-pipeline.kafkaInitContainerSecurityContext" -}}
{{- if .Values.podSecurity.enabled }}
allowPrivilegeEscalation: false
capabilities:
  drop:
    - ALL
{{- end }}
{{- end }}