# lndash

[![Build Status](https://travis-ci.org/djmelik/lndash.svg?branch=master)](https://travis-ci.org/djmelik/lndash)

lndash is a simple read-only web dashboard for [lnd](https://github.com/lightningnetwork/lnd) - Lightning Network Daemon

## Features

* Peer view
* Channel view
* Forwarding Events (routed payments) view
* Looking Glass Tool (route/path lookup)
* Lightning Network Graph

## Installation

*This guide was written on a Debian system.*

1. Clone lndash repository and enter the project directory:

```sh
git clone https://github.com/djmelik/lndash.git
cd lndash
```

2. Install required dependencies for virtualenv, set it up and activate:

```sh
sudo apt-get install python3-pip python3-virtualenv virtualenv
virtualenv -p python3 venv
source venv/bin/activate
```

Make sure you have installed Python 3 virtualenv, not Python 2 as this is not supported.

3. Install python libs & dependencies into running virtualenv:

```sh
pip install -r requirements.txt
```

7. Copy the tls certificate and **readonly** macaroon from lnd to lndash config directory:

```sh
cp ~/.lnd/tls.cert config/tls.cert
cp ~/.lnd/data/chain/bitcoin/mainnet/readonly.macaroon config/readonly.macaroon
```

8. (Optional) If lnd is installed on a remote host, define an environment variable pointing to that host:

```sh
export LNDASH_LND_SERVER="127.0.0.1:10009"
```

9. Run the application:

```sh
gunicorn main:app
```

If you want gunicorn to listen on all interfaces and/or change the port, run the application using the following:

```sh
gunicorn main:app -b 0.0.0.0:8080
```

## Docker

Four things need to be configured on the host to run the `lndash` docker container:

  1. The path to the TLS certificate (ex. `$HOME/.lnd/tls.cert`)
  1. The path to the readonly macaroon (ex. `$HOME/.lnd/data/chain/bitcoin/mainnet/readonly.macaroon`)
  1. The port on which the web app should listen (ex. `8000`)
  1. The LND server's RPC address (ex. `192.168.1.2:10009`)

### The easy way

Run the following command in your terminal (replace all local paths with your own):

```sh
docker run -d --rm \
  -v=$HOME/.lnd/tls.cert:/usr/src/app/config/tls.cert \
  -v=$HOME/.lnd/data/chain/bitcoin/mainnet/readonly.macaroon:/usr/src/app/config/readonly.macaroon \
  -p 8000:8000 \
  -e LNDASH_LND_SERVER="192.168.1.2:10009" \
  djmelik/lndash:latest
```

And open http://localhost:8000 in your browser.

> **Protip:** You can skip `-d` in the command above to get all the logs in your terminal.

### The manual way

#### Build the docker container

Run the following command in the `lndash` directory:

```sh
docker build -t lndash:latest .
```

This will build the docker container and give it the tag `lndash`.


#### Run the built container

Run the following command in your terminal:

```sh
docker run -d --restart \
  -v=$HOME/.lnd/tls.cert:/usr/src/app/config/tls.cert \
  -v=$HOME/.lnd/data/chain/bitcoin/mainnet/readonly.macaroon:/usr/src/app/config/readonly.macaroon \
  -p 8000:8000 \
  -e LNDASH_LND_SERVER="192.168.1.2:10009" \
  lndash:latest
```

The above command line assumes `tls.cert` and `readonly.macaroon` are stored at these locations and that the LND server is available on port 10009 at IP address 192.168.1.2. It makes the `lndash` server available on port 8000. Change these values as needed.

Now you can open http://localhost:8000 in your browser.

## Nginx reverse proxy

You can set up an nginx reverse proxy and publicly expose your lndash instance.

*Note: need to write these instructions.*
