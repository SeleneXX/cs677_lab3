import peer, multiprocessing
from initialize import initialize as ini

def peer1():
    buyer1 = peer.Peer(('127.0.0.1', 8001), 1, False, 0, 5, ('127.0.0.1', 8000), True)
    buyer1.process()

def peer2():
    buyer2 = peer.Peer(('127.0.0.1', 8002), 2, False, 0, 5, ('127.0.0.1', 8000), True)
    buyer2.process()

def peer3():
    buyer3 = peer.Peer(('127.0.0.1', 8003), 3, True, 0, 5, ('127.0.0.1', 8000), True)
    buyer3.process()

def peer4():
    seller4 = peer.Peer(('127.0.0.1', 8004), 4, True, 0, 5, ('127.0.0.1', 8000), True)
    seller4.process()

def peer5():
    seller5 = peer.Peer(('127.0.0.1', 8005), 5, True, 0, 5, ('127.0.0.1', 8000), True)
    seller5.process()

def peer6():
    seller6 = peer.Peer(('127.0.0.1', 8006), 6, True, 0, 5, ('127.0.0.1', 8000), True)
    seller6.process()

def warehouse():
    warehouse = peer.Warehouse(('127.0.0.1', 8000))
    warehouse.process()

if __name__ == '__main__':
    ini()
    p0 = multiprocessing.Process(target=warehouse)
    p1 = multiprocessing.Process(target=peer1)
    p2 = multiprocessing.Process(target=peer2)
    p3 = multiprocessing.Process(target=peer3)
    p4 = multiprocessing.Process(target=peer4)
    p5 = multiprocessing.Process(target=peer5)
    p6 = multiprocessing.Process(target=peer6)

    p0.start()
    p1.start()
    p2.start()
    p3.start()
    p4.start()
    p5.start()
    p6.start()