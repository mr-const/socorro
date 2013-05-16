# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import datetime
import threading
import json
import pika

from socorro.external.crashstorage_base import (
    CrashStorageBase,
    CrashIDNotFound
)
from configman import Namespace
from socorro.database.transaction_executor import (
    TransactionExecutor
)
from socorro.external.rabbitmq.connection_context import ConnectionContext
from socorro.lib.datetimeutil import uuid_to_date

from socorro.database.transaction_executor import \
    TransactionExecutorWithInfiniteBackoff


class RabbitMQCrashStorage(CrashStorageBase):

    required_config = Namespace()

    required_config.add_option('rabbitmq_class',
                               default=ConnectionContext,
                               doc='the class responsible for connecting to'
                               'RabbitMQ')

    required_config.add_option('transaction_executor_class',
                              default=TransactionExecutorWithInfiniteBackoff,
                              doc='Transaction wrapper class')

    def __init__(self, config, quit_check_callback=None):
        super(RabbitMQCrashStorage, self).__init__(
            config,
            quit_check_callback=quit_check_callback
        )

        # Note: this may continue to grow if we aren't acking certain UUIDs.
        # We should find a way to time out UUIDs after a certain time.
        self.internal_cache = {}

        self.rabbitmq = config.rabbitmq_class(config)
        self.transaction = config.transaction_executor_class(
            config,
            self.rabbitmq,
            quit_check_callback=quit_check_callback
        )

    def save_raw_crash(self, raw_crash, dumps, crash_id):
        try:
            if raw_crash.legacy_processing == 0:
                self.transaction(self._save_raw_crash_transaction, crash_id)
            else:
                self.config.logger.debug(
                    'not saving crash %s, legacy processing '
                    'flag is %d', crash_id, raw_crash_json.legacy_processing
                )
        except KeyError:  # TODO: overbroad "try" block
            self.config.logger.debug(
                'legacy_processing key absent in crash %s', 
                crash_id
            )

    def _save_raw_crash_transaction(self, connection, crash_id):
        connection.channel.basic_publish(
            exchange='',
            routing_key='socorro.normal',
            body=crash_id,
            properties=pika.BasicProperties(
                delivery_mode = 2, # make message persistent
            ))

    def new_crashes(self):
        connection = self.rabbitmq.connection()
        data = connection.channel.basic_get(queue="socorro.priority")
        # RabbitMQ gives us: (channel information, meta information, payload)
        if data == (None, None, None):
            data = connection.channel.basic_get(queue="socorro.normal")

        while data != (None, None, None):
            self.internal_cache[data[2]] = data[0]
            yield data[2]
            data = connection.channel.basic_get(queue="socorro.priority")
            if data == (None, None, None):
                data = connection.channel.basic_get(queue="socorro.normal")

    def ack_crash(self, crash_id):
        if crash_id in self.internal_cache:
            to_ack = self.internal_cache[crash_id]
            self.transaction(self._transaction_ack_crash, to_ack)
            del self.internal_cache[crash_id]
        else:
            self.config.logger.error('Crash ID %s was not found in the internal cache', crash_id)

    def _transaction_ack_crash(self, connection, to_ack):
        connection.channel.basic_ack(delivery_tag=to_ack.delivery_tag)