"""Kafka per-tenant topic partitioning tests."""

from datetime import datetime, timezone

import pytest

from telemetry.config import KafkaConfig, TenancyConfig
from telemetry.ingestion.kafka_producer import KafkaEventProducer
from telemetry.ingestion.kafka_topics import (
    consumer_topics,
    is_topic_per_tenant,
    parse_tenant_from_topic,
    stamp_event_tenant,
    topic_for_tenant,
)
from telemetry.models import SensorEvent
from telemetry.simulator.generator import SensorSimulator


def test_topic_for_tenant_from_template():
    kafka = KafkaConfig(topic_template="telemetry.events.{tenant_id}")
    assert topic_for_tenant("acme", kafka) == "telemetry.events.acme"


def test_topic_for_tenant_explicit_override():
    kafka = KafkaConfig(
        topic_template="telemetry.events.{tenant_id}",
        tenant_topics={"acme": "telemetry.acme.dedicated"},
    )
    assert topic_for_tenant("acme", kafka) == "telemetry.acme.dedicated"
    assert topic_for_tenant("globex", kafka) == "telemetry.events.globex"


def test_consumer_topics_single_when_disabled():
    kafka = KafkaConfig(topic="telemetry.events", topic_per_tenant=False)
    tenancy = TenancyConfig(enabled=True, tenant_api_keys={"acme": "k1"})
    assert consumer_topics(kafka, tenancy) == ["telemetry.events"]


def test_consumer_topics_per_tenant():
    kafka = KafkaConfig(topic_per_tenant=True, topic_template="telemetry.events.{tenant_id}")
    tenancy = TenancyConfig(
        enabled=True,
        default_tenant="default",
        tenant_api_keys={"acme": "k1", "globex": "k2"},
    )
    topics = consumer_topics(kafka, tenancy)
    assert topics == ["telemetry.events.acme", "telemetry.events.default", "telemetry.events.globex"]


def test_parse_tenant_from_topic_roundtrip():
    kafka = KafkaConfig(topic_template="telemetry.events.{tenant_id}")
    assert parse_tenant_from_topic("telemetry.events.acme", kafka) == "acme"
    assert parse_tenant_from_topic("telemetry.events", kafka) is None


def test_stamp_event_tenant_from_topic():
    kafka = KafkaConfig(topic_per_tenant=True, topic_template="telemetry.events.{tenant_id}")
    event = SensorEvent(
        device_id="industrial-device-001",
        sensor_type="industrial",
        timestamp=datetime.now(timezone.utc),
        metrics={"temperature": 65.0},
    )
    stamped = stamp_event_tenant(event, "telemetry.events.acme", kafka)
    assert stamped.tenant_id == "acme"
    assert stamped.tags["tenant_id"] == "acme"


def test_producer_resolve_topic(pipeline_config, sensors_config):
    pipeline_config.tenancy.enabled = True
    pipeline_config.tenancy.tenant_api_keys = {"acme": "key"}
    pipeline_config.ingestion.kafka.topic_per_tenant = True

    producer = KafkaEventProducer(pipeline_config.ingestion.kafka, pipeline_config.tenancy)
    event = SensorEvent(
        device_id="industrial-device-001",
        sensor_type="industrial",
        timestamp=datetime.now(timezone.utc),
        metrics={"temperature": 65.0},
        tenant_id="acme",
    )
    assert producer.resolve_topic(event) == "telemetry.events.acme"


def test_simulator_assigns_tenant_to_events(pipeline_config, sensors_config):
    pipeline_config.tenancy.enabled = True
    pipeline_config.tenancy.tenant_api_keys = {"acme": "k1", "globex": "k2"}
    pipeline_config.ingestion.kafka.topic_per_tenant = True

    sim = SensorSimulator(pipeline_config, sensors_config, seed=1)
    tenants = {sim.generate_event("industrial-device-000").tenant_id for _ in range(20)}
    assert "acme" in tenants or "globex" in tenants or "default" in tenants


def test_topic_per_tenant_requires_tenancy_enabled():
    kafka = KafkaConfig(topic_per_tenant=True)
    tenancy = TenancyConfig(enabled=False)
    assert not is_topic_per_tenant(kafka, tenancy)