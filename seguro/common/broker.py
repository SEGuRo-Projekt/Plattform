"""
SPDX-FileCopyrightText: 2023 Felix Wege, EONERC-ACS, RWTH Aachen University
SPDX-FileCopyrightText: 2023 Steffen Vogel, OPAL-RT Germany GmbH
SPDX-License-Identifier: Apache-2.0
"""

from queue import Queue
import os
import uuid

import paho.mqtt.client as mqtt

import seguro.common.logger
from seguro.common.config import (
    MQTT_HOST,
    MQTT_PASSWORD,
    MQTT_PORT,
    MQTT_USERNAME,
    LOG_LEVEL,
    MAX_BYTES,
    BACKUP_COUNT,
)


class BrokerClient:
    """Helper class for MQTT interaction with the SEGuRo platform.

    This class provides an abstraction layer for MQTT based communication
    between the SEGuRo platform and the MQTT broker.
    """

    def __init__(
        self,
        uid="",
        host=MQTT_HOST,
        port=MQTT_PORT,
        username=MQTT_USERNAME,
        password=MQTT_PASSWORD,
        keepalive=60,
        log_level=LOG_LEVEL,
        log_max_bytes=MAX_BYTES,
        log_backup_count=BACKUP_COUNT,
    ):
        """Broker Constructor

        Create a paho.mqtt.client object and initialize the message queue.

        Arguments:
            uid -- Unique id/name of the client
        """
        if not uid:
            # Create uid based onMAC address and time component
            self.uid = str(uuid.uuid1())
        else:
            self.uid = uid

        self.client = client = mqtt.Client(client_id=self.uid)

        client.on_connect = self.__on_connect
        client.on_message = self.__on_message

        if username is not None or password is not None:
            self.client.username_pw_set(username, password)

        self.client.connect(host, port, keepalive)

        self.message_queue = Queue()

        try:
            self.logger = seguro.common.logger.store_logger(
                log_level, f"{self.uid}.log"
            )
        except Exception as exc:
            self.logger = seguro.common.logger.file_logger(
                log_level,
                os.path.join(
                    os.path.dirname(__file__),
                    f"../../log/brokerclient/{self.uid}.log",
                ),
                max_bytes=log_max_bytes,
                backup_count=log_backup_count,
            )
            self.logger.warning(
                "Exception %s raised when creating store_logger, \
                    falling back to file_logger...",
                exc,
            )

        self.start_listening()

    def __del__(self):
        self.stop_listening()

    def __on_connect(self, client, userdata, flags, rc):
        self.logger.info("Connected with result code %i", rc)

    def __on_message(self, client, userdata, msg):
        self.logger.debug("Receive msg: %s - %s", msg.topic, str(msg.payload))
        self.message_queue.put(msg)

    def subscribe(self, topic, callback=None):
        """Subscribe client to given topic and registering callback (optional).

        Arguments:
            topic -- topic that is subscribed

        Optional:
            callback -- callback func that is called on message reception.
                        If no callback set, the default __on_message is called
        """
        self.client.subscribe(topic)

        if callback:
            self.client.message_callback_add(topic, callback)
            self.logger.info(
                "Subscribed to %s with callback-func %s", topic, callback
            )

    def start_listening(self):
        """Start async listening on subscribed topics."""
        self.client.loop_start()

    def stop_listening(self):
        """Stop async listening on subscribed topics."""
        self.client.loop_stop()

    def publish(self, topic, message):
        """Publish message to given topic."""
        self.logger.debug("Send msg: %s - %s", topic, message)
        self.client.publish(topic, message)
