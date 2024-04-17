#!/bin/bash
# SPDX-FileCopyrightText: 2023 Steffen Vogel, OPAL-RT Germany GmbH
# SPDX-License-Identifier: Apache-2.0

set -e

rm -f /mosquitto/config/dynsec.json

mosquitto_ctrl dynsec init /mosquitto/config/dynsec.json "${ADMIN_USERNAME}" "${ADMIN_PASSWORD}"