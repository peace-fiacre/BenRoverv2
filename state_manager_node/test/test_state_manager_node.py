from state_manager_node.state_manager_node import (
    TopicHealth,
    _status_for_topic,
)
from diagnostic_msgs.msg import DiagnosticStatus


def test_topic_is_stale_before_first_message():
    topic = TopicHealth('/scan')

    level, message = _status_for_topic(topic, 1_000_000_000, 1.0)

    assert level == DiagnosticStatus.ERROR
    assert message == 'aucun message recu'


def test_topic_becomes_stale_after_timeout():
    topic = TopicHealth('/scan')
    topic.mark_received(1_000_000_000)

    level, message = _status_for_topic(topic, 2_100_000_000, 1.0)

    assert level == DiagnosticStatus.ERROR
    assert message == 'aucun message recent'


def test_topic_is_ok_when_message_is_recent():
    topic = TopicHealth('/scan')
    topic.mark_received(1_000_000_000)

    level, message = _status_for_topic(topic, 1_500_000_000, 1.0)

    assert level == DiagnosticStatus.OK
    assert message == 'messages recus normalement'


def test_invalid_topic_format_is_reported():
    topic = TopicHealth('/map')
    topic.mark_received(1_000_000_000, valid=False, error='format invalide')

    level, message = _status_for_topic(topic, 1_500_000_000, 1.0)

    assert level == DiagnosticStatus.ERROR
    assert message == 'format invalide'
