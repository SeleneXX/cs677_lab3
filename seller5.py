import peers

seller5 = peers.Peer(('127.0.0.1', 8005), 5, True, 0, 5, ('127.0.0.1', 8000))
seller5.trader_list.append(('127.0.0.1', 8002))
seller5.trader_list.append(('127.0.0.1', 8006))
seller5.process()