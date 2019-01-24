import os, grpc, time, datetime, json
from flask import Blueprint, render_template, request, jsonify

import config
import libs.rpc_pb2 as ln
import libs.rpc_pb2_grpc as lnrpc
from cache import cache

blueprint = Blueprint("views", __name__, template_folder="templates")


def metadata_callback(context, callback):
    callback([("macaroon", macaroon)], None)


os.environ["GRPC_SSL_CIPHER_SUITES"] = "HIGH+ECDSA"
macaroon = open(config.macaroon_path, "rb").read().hex()
cert = open(config.cert_path, "rb").read()
cert_creds = grpc.ssl_channel_credentials(cert)
auth_creds = grpc.metadata_call_credentials(metadata_callback)
combined_creds = grpc.composite_channel_credentials(cert_creds, auth_creds)
grpc_options = [
    ("grpc.max_receive_message_length", config.grpc_max_length),
    ("grpc.max_send_message_length", config.grpc_max_length),
]
channel = grpc.secure_channel(
    config.lnd_grpc_server, combined_creds, options=grpc_options
)
stub = lnrpc.LightningStub(channel)


@blueprint.route("/query", methods=["GET", "POST"])
def query():
    nodes = stub.DescribeGraph(ln.ChannelGraphRequest()).nodes

    content = {"nodes": nodes, "node_count": len(nodes), "routes": []}

    if request.method == "POST":
        map_data = {"edges": [], "nodes": []}

        # Add Local Node to map data
        local_node = stub.GetInfo(ln.GetInfoRequest())
        local_node_info = stub.GetNodeInfo(
            ln.NodeInfoRequest(pub_key=local_node.identity_pubkey)
        )
        map_data["nodes"].append(
            {
                "id": local_node_info.node.pub_key,
                "label": local_node_info.node.alias,
                "color": local_node_info.node.color,
            }
        )

        routes_list = stub.QueryRoutes(
            ln.QueryRoutesRequest(
                pub_key=request.form["node-result"],
                amt=int(request.form["amount"]),
                num_routes=10,
            )
        ).routes

        for route in routes_list:
            hops = []

            for hop in route.hops:
                node_info = stub.GetNodeInfo(ln.NodeInfoRequest(pub_key=hop.pub_key))
                chan_info = stub.GetChanInfo(ln.ChanInfoRequest(chan_id=hop.chan_id))

                node = {
                    "id": node_info.node.pub_key,
                    "label": node_info.node.alias,
                    "color": node_info.node.color,
                }
                if hop.pub_key == chan_info.node1_pub:
                    edge = {
                        "from": chan_info.node2_pub,
                        "to": chan_info.node1_pub,
                        "label": chan_info.channel_id,
                        "arrows": "to",
                        "font": "{align: 'middle'}",
                    }
                else:
                    edge = {
                        "from": chan_info.node1_pub,
                        "to": chan_info.node2_pub,
                        "label": chan_info.channel_id,
                        "arrows": "to",
                        "font": "{align: 'middle'}",
                    }

                if node not in map_data["nodes"]:
                    map_data["nodes"].append(node)
                if edge not in map_data["edges"]:
                    map_data["edges"].append(edge)

                hops.append(
                    {
                        "chan_id": hop.chan_id,
                        "chan_capacity": hop.chan_capacity,
                        "amt_to_forward": hop.amt_to_forward_msat / 1000,
                        "fee": hop.fee_msat / 1000,
                        "pub_key": hop.pub_key,
                        "node_alias": node_info.node.alias,
                        "node_color": node_info.node.color,
                    }
                )

            content["routes"].append(
                {
                    "hops": hops,
                    "total_amt": route.total_amt_msat / 1000,
                    "total_fees": route.total_fees_msat / 1000,
                }
            )

        content.update({"map_data": json.dumps(map_data)})

        return render_template("query-success.html", **content)

    return render_template("query.html", **content)


@blueprint.route("/")
@cache.cached(timeout=60)
def home():
    node_info = stub.GetInfo(ln.GetInfoRequest())
    node_info_detail = stub.GetNodeInfo(
        ln.NodeInfoRequest(pub_key=node_info.identity_pubkey)
    )

    content = {
        "identity_pubkey": node_info.identity_pubkey,
        "uris": node_info.uris,
        "alias": node_info.alias,
        "chains": node_info.chains,
        "version": node_info.version,
        "block_height": node_info.block_height,
        "synced": str(node_info.synced_to_chain),
        "block_hash": node_info.block_hash,
        "num_active_channels": node_info.num_active_channels,
        "num_inactive_channels": node_info.num_inactive_channels,
        "num_pending_channels": node_info.num_pending_channels,
        "num_peers": node_info.num_peers,
        "total_capacity": node_info_detail.total_capacity,
    }

    return render_template("index.html", **content)


@blueprint.route("/channels")
@cache.cached(timeout=60)
def channels():
    peers = []
    total_capacity = 0
    total_local_balance = 0
    total_remote_balance = 0
    total_sent = 0
    total_received = 0
    total_commit = 0
    bytes_sent = 0
    bytes_received = 0
    channel_count = 0
    scatterPlotCapacity = {
        "ids": [],
        "x": [],
        "y": [],
        "mode": "markers",
        "type": "scatter",
        "hovertext": [],
        "marker": {"size": 12, "color": []},
    }
    scatterPlotActivity = {
        "ids": [],
        "x": [],
        "y": [],
        "mode": "markers",
        "type": "scatter",
        "hovertext": [],
        "marker": {"size": 12, "color": []},
    }

    peers_response = stub.ListPeers(ln.ListPeersRequest())
    channels_response = stub.ListChannels(ln.ListChannelsRequest(active_only=True))

    for peer in peers_response.peers:
        try:
            node_info_response = stub.GetNodeInfo(
                ln.NodeInfoRequest(pub_key=peer.pub_key)
            )
            node_alias = node_info_response.node.alias
            node_color = node_info_response.node.color
        except grpc.RpcError:
            node_alias = ""
            node_color = ""

        peers.append(
            {
                "alias": node_alias,
                "color": node_color,
                "pub_key": peer.pub_key,
                "address": peer.address,
                "bytes_sent": peer.bytes_sent,
                "bytes_received": peer.bytes_recv,
                "sats_sent": peer.sat_sent,
                "sats_received": peer.sat_recv,
                "ping_time": peer.ping_time,
                "channels": [],
            }
        )

        bytes_sent += peer.bytes_sent
        bytes_received += peer.bytes_recv

    for channel in channels_response.channels:
        peer_filter = [x for x in peers if x["pub_key"] == channel.remote_pubkey]
        index = peers.index(peer_filter[0])

        scatterPlotCapacity["ids"].append(channel.chan_id)
        scatterPlotCapacity["y"].append(int(channel.capacity))
        scatterPlotCapacity["x"].append(
            round(100.0 * channel.local_balance / channel.capacity, 2)
        )
        scatterPlotCapacity["hovertext"].append(peers[index]["alias"])
        scatterPlotCapacity["marker"]["color"].append(str(peers[index]["color"]))

        scatterPlotActivity["ids"].append(channel.chan_id)
        scatterPlotActivity["y"].append(int(channel.capacity))
        scatterPlotActivity["x"].append(
            round(
                100.0
                * (channel.total_satoshis_sent + channel.total_satoshis_received)
                / channel.capacity,
                2,
            )
        )
        scatterPlotActivity["hovertext"].append(peers[index]["alias"])
        scatterPlotActivity["marker"]["color"].append(str(peers[index]["color"]))

        try:
            chan_info = stub.GetChanInfo(ln.ChanInfoRequest(chan_id=channel.chan_id))
        except grpc.RpcError as e:
            e.details()

        if chan_info.node1_pub == channel.remote_pubkey:
            remote_policy = {
                "min_htlc": chan_info.node1_policy.min_htlc,
                "fee_base_msat": chan_info.node1_policy.fee_base_msat,
                "fee_rate": chan_info.node1_policy.fee_rate_milli_msat,
                "time_lock_delta": chan_info.node1_policy.time_lock_delta,
            }
            local_policy = {
                "min_htlc": chan_info.node2_policy.min_htlc,
                "fee_base_msat": chan_info.node2_policy.fee_base_msat,
                "fee_rate": chan_info.node2_policy.fee_rate_milli_msat,
                "time_lock_delta": chan_info.node2_policy.time_lock_delta,
            }
        else:
            remote_policy = {
                "min_htlc": chan_info.node2_policy.min_htlc,
                "fee_base_msat": chan_info.node2_policy.fee_base_msat,
                "fee_rate": chan_info.node2_policy.fee_rate_milli_msat,
                "time_lock_delta": chan_info.node2_policy.time_lock_delta,
            }
            local_policy = {
                "min_htlc": chan_info.node1_policy.min_htlc,
                "fee_base_msat": chan_info.node1_policy.fee_base_msat,
                "fee_rate": chan_info.node1_policy.fee_rate_milli_msat,
                "time_lock_delta": chan_info.node1_policy.time_lock_delta,
            }

        peers[index]["channels"].append(
            {
                "active": channel.active,
                "chan_id": channel.chan_id,
                "capacity": channel.capacity,
                "commit_fee": channel.commit_fee,
                "local_balance": channel.local_balance,
                "remote_balance": channel.remote_balance,
                "sent": channel.total_satoshis_sent,
                "received": channel.total_satoshis_received,
                "local_policy": local_policy,
                "remote_policy": remote_policy,
            }
        )

        total_capacity += channel.capacity
        total_local_balance += channel.local_balance
        total_remote_balance += channel.remote_balance
        total_sent += channel.total_satoshis_sent
        total_received += channel.total_satoshis_received
        total_commit += channel.commit_fee

    content = {
        "peers": sorted(peers, key=lambda x: x["alias"].lower()),
        "stats": {
            "total_capacity": total_capacity,
            "total_local_balance": total_local_balance,
            "total_remote_balance": total_remote_balance,
            "total_sent": total_sent,
            "total_received": total_received,
            "total_commit": total_commit,
            "bytes_sent": bytes_sent,
            "bytes_received": bytes_received,
            "channel_count": len(channels_response.channels),
            "peer_count": len(peers_response.peers),
        },
        "scatterPlotCapacity": json.dumps(scatterPlotCapacity),
        "scatterPlotActivity": json.dumps(scatterPlotActivity),
    }

    return render_template("channels.html", **content)


@blueprint.route("/events")
@cache.cached(timeout=60)
def events():
    events = []
    max_events = 0
    min_events = 0
    avg_events = 0
    total_events = 0

    max_volume = 0
    min_volume = 0
    avg_volume = 0
    total_volume = 0

    max_fees = 0
    min_fees = 0
    avg_fees = 0
    total_fees = 0

    events_response = stub.ForwardingHistory(
        ln.ForwardingHistoryRequest(
            start_time=0,
            end_time=int(time.time()),
            index_offset=0,
            num_max_events=100000,
        )
    )

    for event in events_response.forwarding_events:
        tx_date = datetime.datetime.fromtimestamp(event.timestamp).strftime("%Y-%m-%d")
        tx_size = event.amt_out
        tx_fee = event.fee

        events_filter = [x for x in events if x["date"] == tx_date]
        if len(events_filter) > 0:
            index = events.index(events_filter[0])
            events[index]["events"] = events[index]["events"] + 1
            events[index]["volume"] = events[index]["volume"] + tx_size
            events[index]["fees"] = events[index]["fees"] + tx_fee
        else:
            events.append(
                {"date": tx_date, "events": 1, "volume": tx_size, "fees": tx_fee}
            )

    if len(events) > 0:
        max_events = max(events, key=lambda x: x["events"])
        min_events = min(events, key=lambda x: x["events"])
        events_list = [x["events"] for x in events]
        avg_events = round(sum(events_list) / (float(len(events_list))), 2)
        total_events = sum(events_list)

        max_volume = max(events, key=lambda x: x["volume"])
        min_volume = min(events, key=lambda x: x["volume"])
        volume_list = [x["volume"] for x in events]
        avg_volume = round(sum(volume_list) / (float(len(volume_list))), 2)
        total_volume = sum(volume_list)

        max_fees = max(events, key=lambda x: x["fees"])
        min_fees = min(events, key=lambda x: x["fees"])
        fees_list = [x["fees"] for x in events]
        avg_fees = round(sum(fees_list) / (float(len(fees_list))), 2)
        total_fees = sum(fees_list)

    content = {
        "forwarding_events": events,
        "events_stats": {
            "maximum": max_events,
            "minimum": min_events,
            "average": avg_events,
            "total": total_events,
        },
        "volume_stats": {
            "maximum": max_volume,
            "minimum": min_volume,
            "average": avg_volume,
            "total": total_volume,
        },
        "fees_stats": {
            "maximum": max_fees,
            "minimum": min_fees,
            "average": avg_fees,
            "total": total_fees,
        },
    }

    return render_template("events.html", **content)


@blueprint.route("/map")
@cache.cached(timeout=600)
def lightning_map():
    return render_template("map.html")


@blueprint.route("/map_data")
@cache.cached(timeout=1800)
def map_data():
    response = stub.DescribeGraph(ln.ChannelGraphRequest())
    nodes = [
        {"id": x.pub_key, "alias": x.alias, "color": x.color} for x in response.nodes
    ]
    links = [
        {
            "id": x.channel_id,
            "source": x.node1_pub,
            "target": x.node2_pub,
            "value": x.capacity,
        }
        for x in response.edges
    ]

    map_data = {"nodes": nodes, "links": links}

    return jsonify(map_data)
