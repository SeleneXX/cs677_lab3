import peer

buyer3 = peer.Peer(('127.0.0.1', 8003), 3, True, 0, 5, ('127.0.0.1', 8000), True)
# buyer3 = peer.Peer(('127.0.0.1', 8003), 3, True, 0, 5, ('127.0.0.1', 8000))

buyer3.process()
