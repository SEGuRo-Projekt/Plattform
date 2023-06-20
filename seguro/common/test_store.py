"""
SPDX-FileCopyrightText: 2023 Steffen Vogel, OPAL-RT Germany GmbH
SPDX-FileCopyrightText: 2023 Felix Wege, EONERC-ACS, RWTH Aachen University
SPDX-License-Identifier: Apache-2.0
"""

import os
import threading
import pytest

from seguro.common.store import Client, Event, EventType


@pytest.mark.store
def test_store():
    store = Client("pytest-client")

    # Create new file and fill with content
    if not os.path.isfile("myfile.txt"):
        f = open("myfile.txt", "w")

    f = open("myfile.txt", "w")
    f.write("Hello S3Storage!")
    f.close()

    # Put file into storage
    store.put_file("myStorageFile.txt", "myfile.txt")

    # Write new content to file
    store.put_file_contents("myStorageFile.txt", "!egarotS3S olleH")

    store.get_file("myLocalStorageFile.txt", "myStorageFile.txt")

    f = open("myLocalStorageFile.txt", "r")
    content = f.read()

    assert content == "!egarotS3S olleH"
    print(content)

    # Clean up files after test
    os.remove("myLocalStorageFile.txt")
    os.remove("myfile.txt")


@pytest.mark.store
def test_watch():
    store = Client("pytest-client")

    filename = "some/prefix/test"

    store.remove_file(filename)

    def create_obj():
        store.put_file_contents(filename, "this is a test2")
        store.remove_file(filename)

    t = threading.Timer(0.1, create_obj)
    t.start()

    events = store.watch("some/prefix/")

    event = next(events)
    assert event.type == EventType.CREATED
    assert event.filename == filename

    event = next(events)
    assert event.type == EventType.REMOVED
    assert event.filename == filename


@pytest.mark.store
def test_watch_async():
    store = Client("pytest-client")

    i = 0

    def callback(event: Event):
        nonlocal i

        if i == 0:
            assert event.type == EventType.CREATED
            assert event.filename == filename
        elif i == 1:
            assert event.type == EventType.REMOVED
            assert event.filename == filename

            # Raise a StopIteration exception to stop processing events
            raise StopIteration()

        i += 1

    filename = "some/prefix/test"

    store.remove_file(filename)
    watcher = store.watch_async("some/prefix/", callback)

    store.put_file_contents(filename, "this is a test2")
    store.remove_file(filename)

    watcher.join()
