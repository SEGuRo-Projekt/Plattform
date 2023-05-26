"""
SPDX-FileCopyrightText: 2023 Felix Wege, EONERC-ACS, RWTH Aachen University
SPDX-License-Identifier: Apache-2.0
"""

import os
import time

from seguro.common.store import StoreClient


def test_store():
    storage = StoreClient()

    # Create new file and fill with content
    if not os.path.isfile("myfile.txt"):
        f = open("myfile.txt", "w")

    f = open("myfile.txt", "w")
    f.write("Hello S3Storage!")
    f.close()

    # Put file into storage
    storage.put_file("myStorageFile.txt", "myfile.txt")

    # Check if file has changed...
    # Note: As the storage client cannot know if the file changed on
    #       the first call file_changed() will always return True on first call
    assert storage.file_changed("myStorageFile.txt") is True
    assert storage.file_changed("myStorageFile.txt") is False

    # Write new content to file
    # FIXME: last_modified attribute of S3Storage only retruns
    #        second resolution...
    time.sleep(1)
    storage.write_to_file("myStorageFile.txt", "!egarotS3S olleH")

    # If file has changed (which it should at this point), download it...
    if storage.file_changed("myStorageFile.txt"):
        print("Info: myStorageFile.txt has changed - downloading it again...")
        storage.get_file("myLocalStorageFile.txt", "myStorageFile.txt")

    f = open("myLocalStorageFile.txt", "r")
    content = f.read()

    assert content == "!egarotS3S olleH"
    print(content)
