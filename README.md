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

10. (Optional) You can set up an nginx reverse proxy and publicly expose your lndash instance. *Note: need to write these instructions.*
