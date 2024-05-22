# SPDX-FileCopyrightText: 2023 Steffen Vogel, OPAL-RT Germany GmbH
# SPDX-License-Identifier: Apache-2.0

"""
https://github.com/tpm2-software/tpm2-openssl/blob/master/docs/keys.md

Sign with TPM
   echo -n "hello world" | openssl pkeyutl \
        -provider base \
        -provider tpm2 \
        -inkey testkey.priv \
        -sign \
        -digest sha256 \
        -rawin | xxd -p
"""

import sys
import os
import subprocess
import argparse
from pathlib import Path
from typing import Optional
from contextlib import contextmanager
from tempfile import NamedTemporaryFile

from cryptography.hazmat.backends.openssl.backend import backend
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import rsa, ec, padding, types


def load_openssl_module(name: str, path: Optional[Path]):
    lib = backend._lib
    ffi = backend._ffi

    if not lib.CRYPTOGRAPHY_OPENSSL_300_OR_GREATER:
        raise Exception("Incompatible OpenSSL version")

    if path is not None:
        os.environ["OPENSSL_MODULES"] = path.as_posix()

    p = lib.OSSL_PROVIDER_load(ffi.NULL, name.encode("ascii"))
    if p == ffi.NULL:
        errs = backend._consume_errors()
        raise Exception(
            "Failed to initialize module: "
            + errs[0].reason_text.decode("utf-8")
        )


@contextmanager
def openssl_provider_config(
    name: str = "tpm2",
    module: str = "/usr/lib/ossl-modules/tpm2.so",
):
    # The default provider requires no further configuration
    if name == "default":
        yield {}
        return

    with NamedTemporaryFile("w+t") as tf:
        tf.write(
            f"""
config_diagnostics = 1
openssl_conf = openssl_init

[openssl_init]
providers = providers

[providers]
{name} = {name}_provider

[{name}_provider]
module = {module}
identity = {name}
activate = 1
"""
        )

    yield {"OPENSSL_CONF": tf.name}


def load_privkey(filename) -> types.PrivateKeyTypes:
    with open(filename, "rb") as f:
        return serialization.load_pem_private_key(
            f.read(), unsafe_skip_rsa_key_validation=True, password=None
        )


def generate_privkey(
    provider_name: str = "default",
    provider_module: str | None = None,
    algorithm: str = "RSA",
    rsa_bits: int = 1024,
    ec_group: str = "P-256",
) -> types.PrivateKeyTypes:
    opts = []
    if algorithm == "RSA":
        opts += ["-pkeyopt", f"bits:{rsa_bits}"]
    elif algorithm == "EC":
        opts += ["-pkeyopt", f"group:{ec_group}"]
    else:
        raise RuntimeError("Unsupported algorithm")

    with openssl_provider_config() as env:
        result = subprocess.run(
            [
                "openssl",
                "genpkey",
                "-quiet",
                "-provider",
                provider_name,
                "-outform",
                "DER",
                "-algorithm",
                algorithm,
            ]
            + opts,
            capture_output=True,
            env=env,
        )

    return serialization.load_der_private_key(result.stdout, None)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-p", "--provider", type=str, default="tpm2")
    parser.add_argument("-k", "--key", type=str, default="testkey.priv")
    parser.add_argument(
        "-P",
        "--provider-path",
        type=Path,
    )

    args = parser.parse_args()

    load_openssl_module(args.provider, args.provider_path)

    # key = generate_privkey()
    key = load_privkey(args.key)

    print(key)

    data = b"hello world"

    if isinstance(key, rsa.RSAPrivateKey):
        signature = key.sign(data, padding.PKCS1v15(), hashes.SHA256())
    elif isinstance(key, ec.EllipticCurvePrivateKey):
        signature = key.sign(data, ec.ECDSA(hashes.SHA256()))

    print(signature.hex())


if __name__ == "__main__":
    sys.exit(main())
