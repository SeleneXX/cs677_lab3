import peer, multiprocessing

# def B1():
#     buyer1 = peers.Peer(('127.0.0.1', 8001), 1, False, 0, 5, ('127.0.0.1', 8000))
#     buyer1.trader_list.append(('127.0.0.1', 8002))
#     buyer1.process()


# def B2():
buyer2 = peer.Peer(('127.0.0.1', 8002), 2, False, 0, 5, ('127.0.0.1', 8000), True)
# buyer2 = peer.Peer(('127.0.0.1', 8002), 2, False, 0, 5, ('127.0.0.1', 8000))

buyer2.process()

# if __name__ == '__main__':
#     # p1 = multiprocessing.Process(target=B1)
#     p2 = multiprocessing.Process(target=B2)
#     # p1.start()
#     p2.start()