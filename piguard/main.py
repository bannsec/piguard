#!/usr/bin/env python3

import argparse
import subprocess
import random
import os
import sys
import json
from glob import glob

from termcolor import cprint
from rich import print, box
from rich.table import Table

from .install import install, SERVER_PRIVATE_KEY, SERVER_PUBLIC_KEY
from .wgconfig import WGConfig
from .wgpeer import WGPeer


def config_server(args):

    if os.path.isfile(args.config):
        config = WGConfig(args.config)

    else:
        config = WGConfig()

    #
    # Address
    #

    default_address = config.interface.get("Address", "10.10.10.1/24")

    print("Address is the internal IP address for your VPN server.")
    address = input(f"Address [{default_address}]: ").strip() or default_address
    config.interface["Address"] = address

    #
    # ListenPort
    #

    default_port = config.interface.get("ListenPort", random.randint(30000, 65535))

    print("ListenPort is the UDP port that the wireguard server will listen on.")
    port = input(f"ListenPort [{default_port}]: ").strip() or default_port
    config.interface["ListenPort"] = port

    #
    # PrivateKey
    #

    if "PrivateKey" not in config.interface:
        with open(SERVER_PRIVATE_KEY, "r") as f:
            config.interface["PrivateKey"] = f.read()

    # Routing stuff
    config.interface["PostUp"] = DEFAULT_POSTUP
    config.interface["PostDown"] = DEFAULT_POSTDOWN

    config.save(args.config)


def create_client(args):
    """Generates keys and structure for new peer."""
    os.makedirs(CLIENTS_DIR, exist_ok=True)

    name = input("Client name: ")

    client_json = os.path.join(CLIENTS_DIR, f"{name}.json")
    client_conf = os.path.join(CLIENTS_DIR, f"{name}.conf")

    if os.path.isfile(client_json):
        cprint("Client name already exists.", "yellow")
        if not input("Overwrite? [yN] ").lower().startswith("y"):
            return

    private = subprocess.check_output(["wg", "genkey"]).strip().decode()
    public = (
        subprocess.check_output(f"echo {private} | wg pubkey", shell=True)
        .strip()
        .decode()
    )

    with open(client_json, "w") as f:
        f.write(json.dumps({"public": public, "private": private}))

    config = WGConfig(client_conf)

    #
    # Address
    #

    print(
        "Internal address for your client. Be sure this doesn't overlap other clients."
    )
    default_address = config.interface.get("Address", "10.10.10.2/24")
    address = input(f"Address [{default_address}]: ").strip() or default_address
    config.interface["Address"] = address

    #
    # DNS
    #

    print("DNS for clients to use. Separated by spaces if needed.")
    default_dns = config.interface.get("DNS", "8.8.8.8")
    dns = input(f"DNS [{default_dns}]: ").strip() or default_dns
    config.interface["DNS"] = dns

    config.interface["PrivateKey"] = private
    config.save()

    cprint(f"Created client {name}", "green")


def link_client(args):
    """Link in a given client to the current server config."""

    client_name = input("client name: ")

    server_config = WGConfig(args.config)

    with open(os.path.join(CLIENTS_DIR, f"{client_name}.json"), "r") as f:
        client_json = json.loads(f.read())

    client_conf = WGConfig(os.path.join(CLIENTS_DIR, f"{client_name}.conf"))

    peer = server_config.find_peer(public=client_json["public"])
    if not peer:
        peer = WGPeer()
        server_config.peers.append(peer)

    #
    # Server side
    #

    print(
        "AllowedIPs tells wireguard what IPs this client can claim to have. Likely should match what you have assigned for it already."
    )
    default_address = client_conf.interface["Address"].split("/")[0]
    peer["AllowedIPs"] = input(f"AllowedIps: [{default_address}] ") or default_address
    peer["PublicKey"] = client_json["public"]

    #
    # Client side
    #

    with open(SERVER_PUBLIC_KEY, "r") as f:
        server_public = f.read().strip()

    peer = client_conf.find_peer(public=server_public)
    if not peer:
        peer = WGPeer()
        client_conf.peers.append(peer)

    peer["PublicKey"] = server_public
    print("What subnet would you like your client to forward through this channel?")
    peer["AllowedIPs"] = input("AllowedIPs: [0.0.0.0/0] ") or "0.0.0.0/0"
    print("Whats the IP endpoint and port of your server? I.e.: 1.2.3.4:80")
    peer["Endpoint"] = input("Endpoint: ")
    peer["PersistentKeepalive"] = "25"

    server_config.save()
    client_conf.save()

    cprint("Linked!", "green")


def parse_args():
    parser = argparse.ArgumentParser(description="Wireguard helper for Raspberry Pi")
    parser.add_argument(
        "--config",
        "-c",
        default=DEFAULT_WGCONF,
        help=f"WGConfig file to use (default: {DEFAULT_WGCONF})",
    )
    parser.add_argument(
        "action",
        choices=(
            "install",
            "config-server",
            "create-client",
            "link-client",
            "start",
            "stop",
            "restart",
            "enable",
            "disable",
            "print-client",
            "status"
        ),
        help="Which action?",
    )
    return parser.parse_args()


def sanity():
    # Make sure forwarding is enabled
    if (
        int(subprocess.check_output(["sysctl", "net.ipv4.ip_forward"]).split(b"=")[1])
        == 0
    ):
        cprint("net.ipv4.ip_forward is disabled. Enable? [Yn] ", "yellow")
        if not input().lower().startswith("n"):
            subprocess.call(["sudo", "sysctl", "net.ipv4.ip_forward=1"])
            subprocess.call(
                "echo net.ipv4.ip_forward=1 | sudo tee -a /etc/sysctl.conf", shell=True
            )

def get_clients_json(args):
    clients = {}

    for client in glob(f"{CLIENTS_DIR}/*.json"):
        with open(client, "r") as f:
            client_name = os.path.basename(client).split(".")[0]
            clients[client_name] = json.loads(f.read())
    
    return clients

def print_client(args):
    target = input("Print config for which client: ")
    config_path = os.path.join(CLIENTS_DIR, target + ".conf")
    subprocess.call(["cat", config_path])
    subprocess.call(["qrencode", "-t", "utf8", "-r", config_path])

def print_status_rich(args):

    def _print_status():
        # Determine union of thing keys
        keys = set()
        for item in info:
            keys.update(item.keys())
        
        # Order keys
        keys = sorted(keys)

        if "name" in keys:
            keys.remove("name")
            keys.insert(0, "name")
        
        if "private key" in keys:
            keys.remove("private key")

        # Add keys to table
        for key in keys:
            table.add_column(key, justify="left")#, style=RICH_TABLE_COLORS_ORDER[keys.index(key) % len(RICH_TABLE_COLORS_ORDER)])

        # Add rows to table
        for item in info:
            table.add_row(*[item.get(key, "") for key in keys])

        print(table)


    server_config = WGConfig(args.config)
    clients = get_clients_json(args)

    interface = args.config.split("/")[-1].split(".")[0]
    out = subprocess.check_output(["wg", "show", interface]).decode()

    is_interface = False
    info = []
    thing = {}

    for line in out.splitlines():
        if line.startswith("interface: "):
            is_interface = True
            table = Table(title="Interface: " + line.split(": ")[1], box=box.SIMPLE_HEAD)
            continue
        
        if line.startswith("peer: "):
            if is_interface:
                info.append(thing)
                thing = {}
                _print_status()
                is_interface = False

            if thing:
                info.append(thing)
                thing = {}
            
            else:
                table = Table(title="Peer list", box=box.SIMPLE_HEAD, row_styles=["", "dim"])

            public_key = line.split(": ")[1].strip()
            peer_name = next(name for name, client in clients.items() if client["public"] == public_key)
            thing["name"] = peer_name
            thing["public key"] = public_key
        
        if line.startswith("\t") or line.startswith(" "):
            key, value = line.split(": ")
            thing[key.strip()] = value.strip()

    if thing:
        info.append(thing)
        _print_status()



def print_status(args):
    server_config = WGConfig(args.config)
    clients = get_clients_json(args)

    interface = args.config.split("/")[-1].split(".")[0]
    out = subprocess.check_output(["wg", "show", interface]).decode()

    # Loop through each line, for the lines that start with "peer: ", lookup the peer name
    for line in out.splitlines():
        if line.startswith("peer: "):
            peer_key = line.split(" ")[1].strip()
            for client_name, client_json in clients.items():
                if client_json["public"] == peer_key:
                    print(f"peer: {peer_key} ({client_name})")
                    break
            else:
                raise Exception(f"Could not find client for peer {peer_key}")
        else:
            print(line)

def main():

    # Need to run as root
    if not os.geteuid() == 0:
        return subprocess.call(["sudo", "-E"] + sys.argv)

    args = parse_args()
    sanity()

    if args.action == "install":
        install()

    elif args.action == "config-server":
        config_server(args)

    elif args.action == "create-client":
        create_client(args)

    elif args.action == "link-client":
        link_client(args)

    elif args.action == "start":
        subprocess.call(
            [
                "systemctl",
                "start",
                f"wg-quick@{os.path.basename(args.config).split('.')[0]}",
            ]
        )

    elif args.action == "stop":
        subprocess.call(
            [
                "systemctl",
                "stop",
                f"wg-quick@{os.path.basename(args.config).split('.')[0]}",
            ]
        )

    elif args.action == "restart":
        subprocess.call(
            [
                "systemctl",
                "restart",
                f"wg-quick@{os.path.basename(args.config).split('.')[0]}",
            ]
        )

    elif args.action == "enable":
        subprocess.call(
            [
                "systemctl",
                "enable",
                f"wg-quick@{os.path.basename(args.config).split('.')[0]}",
            ]
        )

    elif args.action == "disable":
        subprocess.call(
            [
                "systemctl",
                "disable",
                f"wg-quick@{os.path.basename(args.config).split('.')[0]}",
            ]
        )

    elif args.action == "print-client":
        print_client(args)
    
    elif args.action == "status":
        print_status_rich(args)


# TODO: Don't assume eth0
CLIENTS_DIR = "/etc/wireguard/clients"
DEFAULT_WGCONF = "/etc/wireguard/wg0.conf"
DEFAULT_POSTUP = "iptables -A FORWARD -i %i -j ACCEPT; iptables -A FORWARD -o %i -j ACCEPT; iptables -t nat -A POSTROUTING -o eth0 -j MASQUERADE"
DEFAULT_POSTDOWN = "iptables -D FORWARD -i %i -j ACCEPT; iptables -D FORWARD -o %i -j ACCEPT; iptables -t nat -D POSTROUTING -o eth0 -j MASQUERADE"

RICH_TABLE_COLORS_ORDER = ['cyan', 'magenta', 'turquoise2', 'blue']

if __name__ == "__main__":
    main()
