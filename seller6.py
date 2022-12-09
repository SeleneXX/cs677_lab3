import peers

seller6 = peers.Peer(('127.0.0.1', 8006), 6, True, 0, 5, ('127.0.0.1', 8000))
seller6.istrader = True
seller6.trader_list.append(('127.0.0.1', 8002))
seller6.trader_list.append(('127.0.0.1', 8006))
seller6.process()