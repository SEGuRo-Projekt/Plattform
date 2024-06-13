#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2023-2024 Steffen Vogel, OPAL-RT Germany GmbH
# SPDX-License-Identifier: Apache-2.0

set -e

PKI_CLIENT_CERTS="mp1 mp2 admin"
PKI_SUBJECT="/C=DE/ST=NRW/L=Aachen/O=OPAL-RT Germany GmbH/OU=Research and Development"
PKI_KEY_BITS=4096
PKI_KEY_TYPE="rsa"
PKI_EXPIRY_DAYS=3650

if [ -n "${CI}" ]; then
  PKI_KEY_BITS=2048
fi

function create_ssh_keys() {
  echo "=== Creating new SSH host key..."
  ssh-keygen -N '' -t ${PKI_KEY_TYPE} -b ${PKI_KEY_BITS} -f /keys/ssh/ssh_host_rsa_key
  echo "Public host key: $(cat /keys/ssh/ssh_host_rsa_key.pub)"
  echo
}

function create_pki_ca() {
  echo "=== Creating new CA certificate"
  openssl req \
    -x509 \
    -new \
    -nodes \
    -sha256 \
    -days ${PKI_EXPIRY_DAYS} \
    -newkey "${PKI_KEY_TYPE}:${PKI_KEY_BITS}" \
    -keyout "/keys/ca/ca.key" \
    -out "/certs/ca.crt" \
    -subj "${PKI_SUBJECT}/CN=SEGuRo Certificate Authority" 2> /dev/null
}

function create_pki_server() {
  echo "=== Creating new server certificate"
  cat > server.v3.ext << EOF
authorityKeyIdentifier = keyid, issuer
basicConstraints = CA:FALSE
keyUsage = digitalSignature, nonRepudiation, keyEncipherment, dataEncipherment
extendedKeyUsage = serverAuth
subjectAltName = @alt_names
[alt_names]
DNS.1 = ${DOMAIN}
DNS.2 = ui.${DOMAIN}
DNS.3 = store.${DOMAIN}
DNS.4 = ui.store.${DOMAIN}
DNS.5 = registry.${DOMAIN}
DNS.6 = ui.registry.${DOMAIN}
DNS.7 = tsa.${DOMAIN}

# For testing against localhost
DNS.8 = localhost
DNS.9 = ui.localhost
DNS.10 = store.localhost
DNS.11 = ui.store.localhost
DNS.12 = registry.localhost
DNS.13 = ui.registry.localhost
DNS.14 = tsa.localhost

# For platform internal communication only
DNS.15 = minio
DNS.16 = mosquitto

IP.1 = 127.0.0.1
EOF

  openssl req \
    -new \
    -nodes \
    -out server.csr \
    -newkey "${PKI_KEY_TYPE}:${PKI_KEY_BITS}" \
    -keyout /keys/server/server.key \
    -subj "${PKI_SUBJECT}/CN=Server Certificate" 2> /dev/null

  openssl x509 \
    -req \
    -days ${PKI_EXPIRY_DAYS} \
    -sha256 \
    -extfile "server.v3.ext" \
    -CA "/certs/ca.crt" \
    -CAkey "/keys/ca/ca.key" \
    -CAcreateserial \
    -in "server.csr" \
    -out "/certs/server.crt" 2> /dev/null
}

function create_pki_tsa() {
  echo "=== Creating new TSA certificate"
  cat > server.v3.ext << EOF
authorityKeyIdentifier = keyid, issuer
basicConstraints = CA:FALSE
keyUsage = digitalSignature
extendedKeyUsage =  critical, timeStamping
subjectAltName = @alt_names
[alt_names]
DNS.1 = tsa.${DOMAIN}

# For testing against localhost
DNS.2 = tsa.localhost

# For platform internal communication only
DNS.3 = timestamp-server
EOF

  openssl req \
    -new \
    -nodes \
    -out tsa.csr \
    -newkey "${PKI_KEY_TYPE}:${PKI_KEY_BITS}" \
    -keyout /keys/tsa/tsa.key \
    -subj "${PKI_SUBJECT}/CN=SEGuRo Timestamping Authority" 2> /dev/null

  openssl x509 \
    -req \
    -days ${PKI_EXPIRY_DAYS} \
    -sha256 \
    -extfile "server.v3.ext" \
    -CA "/certs/ca.crt" \
    -CAkey "/keys/ca/ca.key" \
    -CAcreateserial \
    -in "tsa.csr" \
    -out "/certs/tsa.crt" 2> /dev/null

    # Create chain
    cat /certs/tsa.crt /certs/ca.crt > /certs/tsa_chain.crt
}

function create_pki_client() {
  mkdir -p /{keys,certs}/clients
  CN=$1

  echo "=== Creating new client certificate for ${CN}"
  cat > client.v3.ext << EOF
authorityKeyIdentifier = keyid, issuer
basicConstraints = CA:FALSE
keyUsage = digitalSignature, nonRepudiation, keyEncipherment, dataEncipherment
extendedKeyUsage = clientAuth
EOF

  openssl req \
    -new \
    -nodes \
    -out "/certs/clients/${CN}.csr" \
    -newkey "${PKI_KEY_TYPE}:${PKI_KEY_BITS}" \
    -keyout "/keys/clients/${CN}.key" \
    -subj "${PKI_SUBJECT}/CN=${CN}" 2> /dev/null

  openssl x509 \
    -req \
    -days ${PKI_EXPIRY_DAYS} \
    -sha256 \
    -extfile "client.v3.ext" \
    -CA "/certs/ca.crt" \
    -CAkey "/keys/ca/ca.key" \
    -CAcreateserial \
    -in "/certs/clients/${CN}.csr" \
    -out "/certs/clients/${CN}.crt" 2> /dev/null
}

if [ "${SECRET}" == "PLEASE-CHANGE-ME" ]; then
  echo "Please change the value of the envvar SECRET in your .env file."
  exit 1
fi

echo "== Checking SSH host keys..."
if ! [ -f /keys/ssh/ssh_host_rsa_key ]; then
  create_ssh_keys
fi

echo "== Checking PKI certificates..."
{ [ -f "/certs/ca.crt" ] && [ -f "/keys/ca/ca.key" ]; } || \
create_pki_ca

{ [ -f "/certs/server.crt" ] && [ -f "/keys/server/server.key" ]; } || \
create_pki_server

{ [ -f "/certs/tsa.crt" ] && [ -f "/keys/tsa/tsa.key" ]; } || \
create_pki_tsa

for CN in ${PKI_CLIENT_CERTS}; do
  { [ -f "/certs/clients/${CN}.crt" ] && [ -f "/keys/clients/${CN}.key" ]; } || \
  create_pki_client "${CN}"
done

# Copy clients certs to user accessible mount
mkdir -p /keys/out/clients
cp /certs/clients/*.crt /keys/out/clients
cp /keys/clients/*.key /keys/out/clients
cp /certs/{tsa,tsa_chain,ca}.crt /keys/ca/ca.key /keys/out/
chmod -R 777 /keys/{ca,server,clients,tsa,out}/* /certs/*

# Prepare Minio keys
# See: https://min.io/docs/minio/linux/operations/network-encryption.html
mkdir -p /keys/minio/CAs
cp /certs/ca.crt /keys/minio/CAs
cp /certs/server.crt /keys/minio/public.crt
cp /keys/server/server.key /keys/minio/private.key
cp /keys/ssh/ssh_host_rsa_key{.pub,} /keys/minio/

echo "== Checking DH parameters file..."
if ! [ -f /keys/server/dhparam.pem ]; then
  #openssl dhparam -out /keys/server/dhparam.pem ${PKI_KEY_BITS}
  curl -s "https://2ton.com.au/dhparam/${PKI_KEY_BITS}" > /keys/server/dhparam.pem
  chmod 700 /keys/server/dhparam.pem
  chown 1883:1883 /keys/server/dhparam.pem
fi

echo "== Checking htpasswd for registry..."
if [ -f /keys/server/registry_htpasswd ]; then
  if htpasswd -iv /keys/server/registry_htpasswd "${ADMIN_USERNAME}" <<< "${ADMIN_PASSWORD}" 2> /dev/null; then
    echo "Admin password unchanged"
  else
    htpasswd -iB /keys/server/registry_htpasswd "${ADMIN_USERNAME}" <<< "${ADMIN_PASSWORD}"
  fi
else
  htpasswd -iBc /keys/server/registry_htpasswd "${ADMIN_USERNAME}" <<< "${ADMIN_PASSWORD}"
fi
