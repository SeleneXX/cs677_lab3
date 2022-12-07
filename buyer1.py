import peers

buyer1 = peers.Peer(('127.0.0.1', 8001), 1, False, 0, 5, ('127.0.0.1', 8000))
buyer1.trader_list.append(('127.0.0.1', 8002))
buyer1.process()
