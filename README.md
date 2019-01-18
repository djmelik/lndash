# lndash

lndash is a simple read-only web dashboard for lnd.

## Features
* Peer view
* Channel view
* Forwarding Events (routed payments) view
* Looking Glass Tool (route/path lookup)
* Lightning Network Graph

## Installation
*Please note that the following installation instructions are still a work in progress. This guide was written on a Debian system.*

1. Install dependencies.

```
apt-get install python3-pip python3-virtualenv virtualenv
```

2. Clone lndash repository.

```
git clone https://github.com/djmelik/lndash.git
```

3. Enter lndash project directory.

```
cd lndash
```

4. Set up python virtualenv.

```
virtualenv -p python3 venv
```

5. Activate virtual environment.

```
source venv/bin/activate
```

6. Install python libs & dependencies.

```
pip install -r requirements.txt
```

7. Copy the tls certificate and **readonly** macaroon from lnd to config directory.

```
cp ~/.lnd/tls.cert config/tls.cert
cp ~/.lnd/data/chain/bitcoin/mainnet/readonly.macaroon config/readonly.macaroon
```

8. (Optional) If lnd is installed on a remote host, edit `config/__init__.py` and update lnd's server IP.

```python
lnd_grpc_server = "127.0.0.1:10009"
```

9. Run the application.

```
gunicorn main:app
```

If you want gunicorn to listen on all interfaces and/or change the port, run the application using the following:

```
gunicorn main:app -b 0.0.0.0:8080
```

10. (Optional) You can set up an nginx reverse proxy and publicly expose your lndash instance. *Note: need to write these instructions.*

## Docker
### Building the docker container
`cd` into the `lndash` directory and run the following command:

```
docker build -t lndash:latest .
```
This will build the docker container and give it the tag `lndash`.

### Running the docker container
Three things need to be configured to run the `lndash` docker container.

1. The path to the TLS certificate and readonly macaroon.
2. The port on which the web app should listen.
3. The LND server's RPC address

These can all be configured via the docker command line, as follows:
```
docker run -d --restart -v=/home/ubuntu/lndashcredentials:/usr/src/app/configuration -p 80:8000 -e LNDASH_LND_SERVER='192.168.1.2:10009' lndash:latest
```
The above command line assumes tls.cert and readonly.macaroon have been copied to the directory `/home/ubuntu/lndashcredentials`, and that the LND server is available on port 10009 at IP address 192.168.1.2. It makes the `lndash` server available on port 80.