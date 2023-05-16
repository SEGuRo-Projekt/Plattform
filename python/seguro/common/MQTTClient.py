"""
SPDX-FileCopyrightText: 2023 Felix Wege, EONERC-ACS, RWTH Aachen University
SPDX-License-Identifier: Apache-2.0
"""

import paho.mqtt.client as mqtt
from queue import Queue


class MQTTClient:
    """Helper class for MQTT interaction with the SEGuRo platform.

        This class provides an abstraction layer for MQTT based communication
        between the SEGuRo platform and the MQTT broker.
    """

    def __init__(self):
        """MQTTClient Constructor

            Create a paho.mqtt.client object and initialize the message queue.
        """
        self.client = self.__mqtt_create_client()
        self.messageQueue = Queue()

    def __on_connect(self, client, userdata, flags, rc):
        print(f"Connected with result code {rc}")

    def __on_message(self, client, userdata, msg):
        print(msg.topic+" "+str(msg.payload))
        self.messageQueue.put(msg)

    def __mqtt_create_client(self):
        client = mqtt.Client()
        client.on_connect = self.__on_connect
        client.on_message = self.__on_message
        return client

    def connect(self, broker, port, username=None, passwd=None, keepalive=60):
        """Connect MQTT client to broker.

        Arguments:
            broker  -- Hostname of IP address of the MQTT broker
            port    -- Network port of the MQTT broker

        Keyword arguments:
            username    -- Username for broker authentication (default None)
            passwd      -- Password for broker authentication (default None)
            keepalive   -- Set keepalive interval of connection in s (default 60)
        """
        if username is not None or passwd is not None:
            self.client.username_pw_set(username, passwd)

        self.client.connect(broker, port, keepalive)

    def subscribe(self, topic):
        """Subscribe client to given topic."""
        self.client.subscribe(topic)

    def start_listening(self):
        """Start async listening on subscribed topics."""
        self.client.loop_start()

    def stop_listening(self):
        """Stop async listening on subscribed topics."""
        self.client.loop_stop()

    def publish(self, topic, message):
        """Publish message to given topic."""
        self.client.publish(topic, message)