import peer

seller4 = peer.Peer(('127.0.0.1', 8004), 4, True, 0, 5, ('127.0.0.1', 8000), True)
# seller4 = peer.Peer(('127.0.0.1', 8004), 4, True, 0, 5, ('127.0.0.1', 8000))

seller4.process()