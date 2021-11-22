#!/usr/bin/env python3

from termcolor import cprint
import subprocess
import os

os.environ["debian_frontend"] = "noninteractive"

def install():
    cprint("Updating packages ... ", "yellow")
    subprocess.call(["sudo", "apt", "update"])
    subprocess.call(["sudo", "apt", "dist-upgrade", "-y"])

    cprint("Installing wireguard packages ... ", "yellow")
    subprocess.call(["sudo", "apt", "install", "-y", "qrencode", "iptables", "wireguard", "wireguard-tools", "openresolv"])

    cprint("Creating server keys ... ", "yellow")
    subprocess.call("wg genkey | sudo tee /etc/wireguard/server_private.key | wg pubkey | sudo tee /etc/wireguard/server_public.key", shell=True)

SERVER_PRIVATE_KEY = "/etc/wireguard/server_private.key"
SERVER_PUBLIC_KEY = "/etc/wireguard/server_public.key"

if __name__ == "__main__":
    install()
