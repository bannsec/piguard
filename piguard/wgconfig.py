
import os

from .wgpeer import WGPeer

class WGConfig:
    def __init__(self, path=None):
        self.interface = {}
        self.peers = []
        self.path = path

        if self.path and os.path.isfile(self.path):
            self._load_from_file()

    def save(self, path=None):
        if not path:
            path = self.path

        with open(path, "w") as f:
            f.write(str(self))

    def find_peer(self, public=None):
        if public:
            try:
                next(peer for peer in self.peers if peer["PublicKey"] == public)
            except StopIteration:
                return None

    def _load_from_file(self, path=None):

        if not path:
            path = self.path

        with open(path, "r") as f:
            d = f.read().strip()

        sec = None

        for line in d.split("\n"):
            line = line.strip()

            if line == "[Interface]":
                sec = self.interface
                continue

            if line == "":
                sec = None
                continue

            if line == "[Peer]":
                self.peers.append(WGPeer())
                sec = self.peers[-1]
                continue

            # Save off the attribute
            key, value = line.split(" = ")
            sec[key] = value

    def __str__(self):
        s = "[Interface]\n"
        for key, val in self.interface.items():
            s += f"{key} = {val}\n"

        s += "".join(str(peer) for peer in self.peers)

        """
        for peer in self.peers:
            s += "\n[Peer]\n"
            for key, val in peer.items():
                s += f"{key} = {val}\n"
        """

        return s
