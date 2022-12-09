import peers

buyer3 = peers.Peer(('127.0.0.1', 8003), 3, False, 0, 5, ('127.0.0.1', 8000))
buyer3.trader_list.append(('127.0.0.1', 8002))
buyer3.trader_list.append(('127.0.0.1', 8006))
buyer3.process()
