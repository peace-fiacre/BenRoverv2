# Run from the workspace root:
# colcon test --packages-select benrover_manager \
#   --python-testing pytest --event-handlers console_direct+

from benrover_manager.state_manager_node import (
    LEVEL_ERROR,
    LEVEL_OK,
    TopicHealth,
    _status_for_topic,
)


def test_topic_is_stale_before_first_message():
    topic = TopicHealth('/scan')

    level, message = _status_for_topic(topic, 1_000_000_000, 1.0)

    assert level == LEVEL_ERROR
    assert message == 'aucun message recu'


def test_topic_becomes_stale_after_timeout():
    topic = TopicHealth('/scan')
    topic.mark_received(1_000_000_000)

    level, message = _status_for_topic(topic, 2_100_000_000, 1.0)

    assert level == LEVEL_ERROR
    assert message == 'aucun message recent'


def test_topic_is_ok_when_message_is_recent():
    topic = TopicHealth('/scan')
    topic.mark_received(1_000_000_000)

    level, message = _status_for_topic(topic, 1_500_000_000, 1.0)

    assert level == LEVEL_OK
    assert message == 'messages recus normalement'


def test_invalid_topic_format_is_reported():
    topic = TopicHealth('/map')
    topic.mark_received(1_000_000_000, valid=False, error='format invalide')

    level, message = _status_for_topic(topic, 1_500_000_000, 1.0)

    assert level == LEVEL_ERROR
    assert message == 'format invalide'
