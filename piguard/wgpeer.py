

class WGPeer:
    def __init__(self):
        self._vars = {}

    def __setitem__(self, key, val):
        self._vars[key] = val

    def __getitem__(self, key):
        return self._vars[key]

    def __str__(self):
        s = "\n[Peer]\n"

        for key, val in self._vars.items():
            s += f"{key} = {val}\n"

        return s
