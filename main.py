import time, datetime
import libs.rpc_pb2 as ln
import libs.rpc_pb2_grpc as lnrpc
import os, grpc, codecs

from flask import Flask, render_template, request
from flask_caching import Cache
from flask_qrcode import QRcode
from protobuf_to_dict import protobuf_to_dict
from collections import Counter

app = Flask(__name__)
app.debug = True
app.testing = False
qrcode = QRcode(app)
cache = Cache(config={'CACHE_TYPE': 'simple'})
cache.init_app(app)

# LND gRPC Variables
macaroon_path='config/readonly.macaroon'
cert_path='config/tls.cert'
lnd_grpc_server='10.1.0.100:10009'
os.environ["GRPC_SSL_CIPHER_SUITES"] = 'HIGH+ECDSA'
macaroon = codecs.encode(open(macaroon_path, 'rb').read(), 'hex')
cert = open(cert_path, 'rb').read()

# Set GRPC max receive length to 32 MiB
grpc_options = [
    ('grpc.max_receive_message_length', 33554432),
    ('grpc.max_send_message_length', 33554432),
]

def metadata_callback(context, callback):
    callback([('macaroon', macaroon)], None)

cert_creds = grpc.ssl_channel_credentials(cert)
auth_creds = grpc.metadata_call_credentials(metadata_callback)
combined_creds = grpc.composite_channel_credentials(cert_creds, auth_creds)
channel = grpc.secure_channel(lnd_grpc_server, combined_creds, options=grpc_options)
stub = lnrpc.LightningStub(channel)

@app.route('/qrcode', methods=['GET'])
@cache.cached(timeout=300)
def get_qrcode():
    data = request.args.get('data', '')

    return send_file(
    qrcode(data, mode='raw'),
    mimetype='image/png'
    )

@app.route("/query", methods=['GET', 'POST'])
#@cache.cached(timeout=60)
def query():
    nodes = stub.DescribeGraph(ln.ChannelGraphRequest()).nodes

    content = {
        'nodes': nodes,
        'node_count': len(nodes),
    }

    if request.method == 'POST':
        routes_list = stub.QueryRoutes(ln.QueryRoutesRequest(
            pub_key=request.form['node-result'],
            amt=long(request.form['amount']),
            num_routes=10,
        )).routes

        content.update({'routes': routes_list})

        return render_template('query-success.html', **content)

    return render_template('query.html', **content)

@app.route("/")
@cache.cached(timeout=60)
def home():
    node_info = protobuf_to_dict(stub.GetInfo(ln.GetInfoRequest()))
    node_info_detail = stub.GetNodeInfo(ln.NodeInfoRequest(pub_key=node_info['identity_pubkey']))

    content = node_info
    content.update({'total_capacity': node_info_detail.total_capacity})

    return render_template('index.html', **content)

@app.route("/channels")
@cache.cached(timeout=60)
def channels():
    peers = []
    total_capacity = 0
    total_local_balance = 0
    total_remote_balance = 0
    total_sent = 0
    total_received = 0
    bytes_sent = 0
    bytes_received = 0
    channel_count = 0

    peers_response = stub.ListPeers(ln.ListPeersRequest())
    channels_response = stub.ListChannels(ln.ListChannelsRequest(active_only=True))

    for peer in peers_response.peers:
        try:
            node_info_response = stub.GetNodeInfo(ln.NodeInfoRequest(pub_key=peer.pub_key))
            node_alias = node_info_response.node.alias
            node_color = node_info_response.node.color
        except grpc.RpcError:
            node_alias = ''
            node_color = ''

        peers.append({
            'alias': node_alias,
            'color': node_color,
            'pub_key': peer.pub_key,
            'address': peer.address,
            'bytes_sent': peer.bytes_sent,
            'bytes_received': peer.bytes_recv,
            'sats_sent': peer.sat_sent,
            'sats_received': peer.sat_recv,
            'ping_time': peer.ping_time,
            'channels': [],
        })

        bytes_sent += peer.bytes_sent
        bytes_received += peer.bytes_recv

    for channel in channels_response.channels:
        peer_filter = filter(lambda x: x['pub_key'] == channel.remote_pubkey, peers)
        index = peers.index(peer_filter[0])

        chan_info = stub.GetChanInfo(ln.ChanInfoRequest(chan_id=channel.chan_id))

        if chan_info.node1_pub == channel.remote_pubkey:
            remote_policy = {
                'min_htlc': chan_info.node1_policy.min_htlc,
                'fee_base_msat': chan_info.node1_policy.fee_base_msat,
                'fee_rate': chan_info.node1_policy.fee_rate_milli_msat,
                'time_lock_delta': chan_info.node1_policy.time_lock_delta,
            }
            local_policy = {
                'min_htlc': chan_info.node2_policy.min_htlc,
                'fee_base_msat': chan_info.node2_policy.fee_base_msat,
                'fee_rate': chan_info.node2_policy.fee_rate_milli_msat,
                'time_lock_delta': chan_info.node2_policy.time_lock_delta,
            }
        else:
            remote_policy = {
                'min_htlc': chan_info.node2_policy.min_htlc,
                'fee_base_msat': chan_info.node2_policy.fee_base_msat,
                'fee_rate': chan_info.node2_policy.fee_rate_milli_msat,
                'time_lock_delta': chan_info.node2_policy.time_lock_delta,
            }
            local_policy = {
                'min_htlc': chan_info.node1_policy.min_htlc,
                'fee_base_msat': chan_info.node1_policy.fee_base_msat,
                'fee_rate': chan_info.node1_policy.fee_rate_milli_msat,
                'time_lock_delta': chan_info.node1_policy.time_lock_delta,
            }

        peers[index]['channels'].append({
            'active': channel.active,
            'chan_id': channel.chan_id,
            'capacity': channel.capacity,
            'local_balance': channel.local_balance,
            'remote_balance': channel.remote_balance,
            'sent': channel.total_satoshis_sent,
            'received': channel.total_satoshis_received,
            'local_policy': local_policy,
            'remote_policy': remote_policy,
        })

        total_capacity +=  channel.capacity
        total_local_balance +=  channel.local_balance
        total_remote_balance += channel.remote_balance
        total_sent += channel.total_satoshis_sent
        total_received += channel.total_satoshis_received

    content = {
        'peers': sorted(peers, key=lambda x: x['alias'].lower()),
        'stats': {
            'total_capacity': total_capacity,
            'total_local_balance': total_local_balance,
            'total_remote_balance': total_remote_balance,
            'total_sent': total_sent,
            'total_received': total_received,
            'bytes_sent': bytes_sent,
            'bytes_received': bytes_received,
            'channel_count': len(channels_response.channels),
            'peer_count': len(peers_response.peers),
        },
    }

    return render_template('channels.html', **content)

@app.route('/events')
@cache.cached(timeout=60)
def events():
    request = ln.ForwardingHistoryRequest(
        start_time = 0,
        end_time = int(time.time()),
        index_offset = 0,
        num_max_events = 100000,
    )
    response = stub.ForwardingHistory(request)

    events = []
    for i in response.forwarding_events:
        tx_date = datetime.datetime.fromtimestamp(i.timestamp).strftime('%y-%m-%d')
        tx_size = i.amt_out
        tx_fee = i.fee

        events_filter = filter(lambda x: x['date'] == tx_date, events)
        if len(events_filter) > 0:
            index = events.index(events_filter[0])
            events[index]['events'] = events[index]['events'] + 1
            events[index]['volume'] = events[index]['volume'] + tx_size
            events[index]['fees'] = events[index]['fees'] + tx_fee
        else:
            events.append({ 'date': tx_date, 'events': 1, 'volume': tx_size, 'fees': tx_fee})

    max_events = max(events, key=lambda x: x['events'])
    min_events = min(events, key=lambda x: x['events'])
    events_list = map(lambda x: x['events'], events)
    avg_events = round(sum(events_list) / (float(len(events_list))), 2)
    total_events = sum(events_list)

    max_volume = max(events, key=lambda x: x['volume'])
    min_volume = min(events, key=lambda x: x['volume'])
    volume_list = map(lambda x: x['volume'], events)
    avg_volume = round(sum(volume_list) / (float(len(volume_list))), 2)
    total_volume = sum(volume_list)

    max_fees = max(events, key=lambda x: x['fees'])
    min_fees = min(events, key=lambda x: x['fees'])
    fees_list = map(lambda x: x['fees'], events)
    avg_fees = round(sum(fees_list) / (float(len(fees_list))), 2)
    total_fees = sum(fees_list)

    content = {
        'forwarding_events': events,
        'events_stats': {
            'maximum': max_events,
            'minimum': min_events,
            'average': avg_events,
            'total': total_events,
            },
        'volume_stats': {
            'maximum': max_volume,
            'minimum': min_volume,
            'average': avg_volume,
            'total': total_volume,
            },
        'fees_stats': {
            'maximum': max_fees,
            'minimum': min_fees,
            'average': avg_fees,
            'total': total_fees,
            },
    }

    return render_template('events.html', **content)

if __name__ == '__main__':
    app.run()
