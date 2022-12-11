import peer

seller6 = peer.Peer(('127.0.0.1', 8006), 6, True, 0, 5, ('127.0.0.1', 8000), True)
# seller6 = peer.Peer(('127.0.0.1', 8006), 6, True, 0, 5, ('127.0.0.1', 8000))


seller6.process()