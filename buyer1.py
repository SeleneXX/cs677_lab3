import peer

buyer1 = peer.Peer(('127.0.0.1', 8001), 1, False, 0, 5, ('127.0.0.1', 8000), True)
# buyer1 = peer.Peer(('127.0.0.1', 8001), 1, False, 0, 5, ('127.0.0.1', 8000))

buyer1.process()
