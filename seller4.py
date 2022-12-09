import peers

seller4 = peers.Peer(('127.0.0.1', 8004), 4, True, 0, 5, ('127.0.0.1', 8000))
seller4.trader_list.append(('127.0.0.1', 8002))
seller4.trader_list.append(('127.0.0.1', 8006))
seller4.process()