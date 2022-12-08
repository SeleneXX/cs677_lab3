import peers, multiprocessing
from concurrent.futures import ThreadPoolExecutor

# buyer1 = peers.Peer(('127.0.0.1', 8001), 1, False, 0, 5, ('127.0.0.1', 8000))
# buyer1.trader_list.append(('127.0.0.1', 8002))
# buyer1.process()
buyer2 = peers.Peer(('127.0.0.1', 8002), 2, False, 0, 5, ('127.0.0.1', 8000))
buyer2.istrader = True
# buyer2.process()

if __name__ == '__main__':
    # p1 = multiprocessing.Process(target=buyer1.process)
    # p2 = multiprocessing.Process(target=buyer2.process)
    # p1.start()
    # p2.start()
    with ThreadPoolExecutor(2) as executor:
        # executor.submit(buyer1.process)
        executor.submit(buyer2.process)