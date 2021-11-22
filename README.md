Decided to be random and make a python wrapper around setting up/managing
wireguard. It's still early in development so YMMV.

# Usage

```bash
# Install wireguard and dependencies
piguard install

# Configure your server (probably only once)
piguard config-server

# Create a client to talk to your server
piguard create-client

# Link in your client to this config
piguard link-client

# Start up wireguard
piguard start

# Enable it (so it auto starts on reboot)
piguard enable

# Print out your client conf and QR to scan on your phone
piguard print-client

# Done
```
