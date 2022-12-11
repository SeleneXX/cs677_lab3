import peer

seller5 = peer.Peer(('127.0.0.1', 8005), 5, True, 0, 5, ('127.0.0.1', 8000), True)
# seller5 = peer.Peer(('127.0.0.1', 8005), 5, True, 0, 5, ('127.0.0.1', 8000))

seller5.process()