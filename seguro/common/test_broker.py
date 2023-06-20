"""
SPDX-FileCopyrightText: 2023 Felix Wege, EONERC-ACS, RWTH Aachen University
SPDX-FileCopyrightText: 2023 Steffen Vogel, OPAL-RT Germany GmbH
SPDX-License-Identifier: Apache-2.0
"""

import time
import pytest

from seguro.common.broker import BrokerClient

# Used to store callback messages
messages = []


def callback(client, userdata, msg):
    messages.append((msg.topic, msg.payload))


@pytest.mark.broker
def test_broker():
    broker = BrokerClient("pytest-broker")

    # Subscribe to topic "mytopic" and start listening in another thread
    broker.subscribe("mytopic")
    broker.subscribe("myCustomTopic", callback)
    # broker.start_listening()

    # Publish messages to topic "mytopic"
    broker.publish("mytopic", "Hello MQTT!")
    broker.publish("myCustomTopic", "Aaaand another one...")

    #  Make sure messages are completely sent...
    time.sleep(1)

    # Read messages on "mytopic" are stored in a messageQueue of the client
    assert broker.message_queue.empty() is False
    assert messages[0] == ("myCustomTopic", b"Aaaand another one...")

    # Read messages directly from client message queue
    while not broker.message_queue.empty():
        msg = broker.message_queue.get()
        print(f"{msg.topic} : {msg.payload}")

    # Note that queue.get() removes messages from queue
    assert broker.message_queue.empty() is True

    # Note that messsages send after listening has stopped,
    # are not put into message queue
    broker.publish("mytopic", "Hello again!")
    assert broker.message_queue.empty() is True
