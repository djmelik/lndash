# lndash

lndash is a simple read-only web dashboard for lnd.

## Features
* Peer view
* Channel view
* Events (routed payments) view
* Looking Glass Tool (route/path lookup)
* Lightning Network Graph

## Installation
*Please note that the following installation instructions are still a work in progress. This guide was written on a Debian system*

1. Install dependencies.

```
apt-get install python-pip python-virtualenv
```

1. Clone lndash repository.

```
git clone https://github.com/djmelik/lndash.git
```

2. Enter lndash project directory.

```
cd lndash
```

3. Set up python virtualenv.

```
virtualenv venv
```

4. Activate virtual environment.

```
source venv/bin/activate
```

5. Install python libs & dependencies.

```
pip install -r requirements.txt
```

6. Copy the tls certificate and **readonly** macaroon from lnd to config directory.

```
cp ~/.lnd/tls.cert config/tls.cert
cp ~/.lnd/readonly.macaroon config/readonly.macaroon
```

7. (Optional) If lnd is installed on a remote host, edit `main.py` and update lnd's server IP.

```python
lnd_grpc_server = 127.0.0.1:10009
```

8. Run the application.

```
gunicorn main:app
```

9. (Optional) You can set up an nginx reverse proxy and publicly expose your lndash instance. *Note: need to write these instructions.*
