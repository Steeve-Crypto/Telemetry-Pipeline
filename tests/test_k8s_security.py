"""Helm chart Pod Security Standards and NetworkPolicy coverage."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHART = ROOT / "helm" / "telemetry-pipeline"
TEMPLATES = CHART / "templates"


def test_dockerfiles_run_as_non_root():
    for name in ("docker/Dockerfile", "docker/Dockerfile.simulator"):
        text = (ROOT / name).read_text()
        assert "USER 1000:1000" in text
        assert "useradd" in text


def test_values_define_pod_security_and_network_policy():
    values = (CHART / "values.yaml").read_text()
    assert "podSecurity:" in values
    assert "networkPolicy:" in values
    assert "enforce: baseline" in values
    assert "defaultDeny: true" in values


def test_helm_templates_include_security_resources():
    namespace = (TEMPLATES / "namespace.yaml").read_text()
    assert "telemetry-pipeline.podSecurityLabels" in namespace

    netpol = (TEMPLATES / "networkpolicy.yaml").read_text()
    assert "kind: NetworkPolicy" in netpol
    assert "default-deny" in netpol
    assert "dns-egress" in netpol

    security = (TEMPLATES / "_security.tpl").read_text()
    assert "runAsNonRoot: true" in security
    assert "readOnlyRootFilesystem" in security


def test_pipeline_deployment_has_tmp_volume_and_security_context():
    deploy = (TEMPLATES / "pipeline-deployment.yaml").read_text()
    assert "pythonPodSecurityContext" in deploy
    assert "pythonContainerSecurityContext" in deploy
    assert 'mountPath: /tmp' in deploy
    assert "emptyDir: {}" in deploy


def test_k8s_namespace_has_pss_labels():
    ns = (ROOT / "k8s" / "namespace.yaml").read_text()
    assert "pod-security.kubernetes.io/enforce: baseline" in ns