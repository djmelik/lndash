import config
import os, grpc
import filters

from flask import Flask
from flask_caching import Cache

app = Flask(__name__)
app.register_blueprint(filters.blueprint)

app.debug = False
app.testing = False
cache = Cache(config={"CACHE_TYPE": "simple"})
cache.init_app(app)

os.environ["GRPC_SSL_CIPHER_SUITES"] = "HIGH+ECDSA"
macaroon = open(config.macaroon_path, "rb").read().hex()
cert = open(config.cert_path, "rb").read()

grpc_options = [
    ("grpc.max_receive_message_length", config.grpc_max_length),
    ("grpc.max_send_message_length", config.grpc_max_length),
]


def metadata_callback(context, callback):
    callback([("macaroon", macaroon)], None)


cert_creds = grpc.ssl_channel_credentials(cert)
auth_creds = grpc.metadata_call_credentials(metadata_callback)
combined_creds = grpc.composite_channel_credentials(cert_creds, auth_creds)
channel = grpc.secure_channel(
    config.lnd_grpc_server, combined_creds, options=grpc_options
)

import views

if __name__ == "__main__":
    app.run()
