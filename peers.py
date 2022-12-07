import collections
import multiprocessing
import random
import socket
import threading
from concurrent.futures import ThreadPoolExecutor
import time


# message category
# 0，1 election.
# 2 trader to warehouse, buy. Reply sell number.
# 3 trader to warehouse, update stock.
# 4 trader to warehouse, cache.
# 5 seller to trader, update stock.
# 6 buyer to trader, buy. Reply sell number.
# 7 trader to trader: check alive.
# 8 trader to peers: set trader.


lock = threading.RLock()
sem = threading.Semaphore(20)

class Warehouse(object):

    def __init__(self, address):
        # address = (IP, port)
        self.address = address
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.bind(address)
        self.server.listen(10000)
        self.item_list = collections.defaultdict(int)

    def process(self):
        print('Warehouse process start.')
        while True:
            with sem:
                time.sleep(0.5)
                conn, _ = self.server.accept()
                request = conn.recv(1024)
                data = request.decode('utf-8')
                fields = data.split('|')

                if fields[0] == '2':
                    # trader's buying message
                    # request_category|product_id|quantity

                    if self.item_list[fields[1]] == 0:
                        conn.send('0'.encode('utf-8'))
                        print(f'Product{fields[1]} not in stock')
                    else:
                        # print(self.buyNum, fields[2])
                        # print(fields)
                        if self.item_list[fields[1]] >= int(fields[2]):
                            self.item_list[fields[1]] -= int(fields[2])
                            print(f'Sucessfully buy {fields[2]} product{self.buyID}')
                            conn.send(fields[2].encode('utf-8'))
                        else:
                            print(f'Sucessfully buy {self.item_list[fields[1]]} product{self.buyID}')
                            conn.send(str(self.item_list[fields[1]]).encode('utf-8'))
                            self.item_list[fields[1]] = 0

                elif fields[0] == '3':
                    # update item in stock
                    # request_category|product_id|quantity
                    self.item_list[fields[1]] += int(fields[2])
                    print(f'Sucessfully update in stock info of Product{fields[1]}: {self.item_list[fields[1]]}')
                    conn.send('1'.encode('utf-8'))


                elif fields[0] == '4':
                    # trader request for stock info
                    # for cache
                    stock = []
                    for key, value in self.item_list.items():
                        pair = f'{key}:{value}'
                        stock.append(pair)
                    message = '|'.join(stock)
                    conn.send(message.encode('utf-8'))

                conn.close()



class Peer(object):

    def __init__(self, address, peer_id, state, product_ID, product_num, warehouse_addr):
        # address = (IP, port)
        self.address = address
        self.peer_id = peer_id
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.bind(address)
        self.server.listen(10000)
        self.productID = product_ID
        self.productNum = product_num
        self.trader_list = []
        self.istrader = False
        self.clock = 0
        self.is_electing = True
        self.isBuyer = not state
        self.isSeller = state
        self.cache = collections.defaultdict[int]
        self.warehouse = warehouse_addr
        self.update_cache = False
        self.alive_peers = []

    def seller_update_stock(self):
        # seller produce their product every 5 second
        print('Seller update stock coroutine start.')
        while True:
            trader_addr, trader_port = random.choice(self.trader_list)
            data = f'{5}|{self.productID}|{self.productNum}'
            client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            try:
                client.connect((trader_addr, int(trader_port)))
                client.send(data.encode('utf-8'))
                print('Send selling item to trader.')
            except:
                print('Fail to send selling item to trader, try again.')
            client.close()
            time.sleep(5)

    def trader_listening_no_cache(self):
        # trader receive buy and update stock request
        print('Trader listening start.')
        while True:
            with sem:
                time.sleep(0.5)
                conn, _ = self.server.accept()
                request = conn.recv(1024)
                data = request.decode('utf-8')
                fields = data.split('|')

                if fields[0] == '6':
                    # receive buy request from buyer
                    # request_category|product_id|quantity
                    print('Receive buy request...')
                    message = f'{2}|{fields[1]}|{fields[2]}'
                    warehouse_addr, warehouse_port = self.warehouse
                    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    client.connect((warehouse_addr, int(warehouse_port)))
                    client.send(message.encode('utf-8'))
                    reply = client.recv(1024)
                    conn.send(reply)
                    client.close()
                elif fields[0] == '5':
                    # receive update stock request from seller
                    # request_category|product_id|quantity
                    print('Receive update stock request...')
                    message = f'{3}|{fields[1]}|{fields[2]}'
                    warehouse_addr, warehouse_port = self.warehouse
                    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    client.connect((warehouse_addr, int(warehouse_port)))
                    client.send(message.encode('utf-8'))
                    conn.send(reply)
                    conn.recv(1024)
                    print('Successfully update.')
                    client.close()
                elif fields[0] == '7':
                    # receive update stock request from seller
                    # request_category
                    print('Alive.')
                conn.close()

    def trader_process(self):
        # trader request for cache and check the status of the other trader
        print('Trader process start.')
        while True:
            time.sleep(0.5)
            if self.update_cache:
                # request for updating cache.
                message = f'{4}'
                warehouse_addr, warehouse_port = self.warehouse
                client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                client.connect((warehouse_addr, int(warehouse_port)))
                client.send(message.encode('utf-8'))
                reply = client.recv(1024)
                client.close()
                stock_info = reply.decode('utf-8')
                stock_info = stock_info.split('|')
                for pair in stock_info:
                    ID, num = pair.split(':')
                    self.cache[ID] = int(num)
                self.update_cache = False

            for addr, port in self.trader_list:
                if addr != self.address[0]:
                    try:
                        # check the status of the other trader
                        client.connect((addr, int(port)))
                        client.send(f'{7}'.encode('utf-8'))
                        print('The other trader alive.')
                    except:
                        # if dead, send message to all peers.
                        print('The other trader dead. Sending message to all peer.')
                        for peer in self.alive_peers:
                            addr, port = peer.split(':')
                            client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                            client.connect((addr, int(port)))
                            client.send(f'{8}|{self.address[0]}-{self.address[1]}'.encode('utf-8'))
                            client.recv(1024)
                            client.close()

    def buyer_process(self):
        # buyer request
        print('Buyer process start.')
        while True:
            time.sleep(0.5)
            if self.productNum == 0:
                print('Complete.')
                self.productNum = random.randint(1, 10)
            trader_addr, trader_port = random.choice(self.trader_list)
            data = f'{6}|{self.productID}|{self.productNum}'
            client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            try:
                client.connect((trader_addr, int(trader_port)))
                client.send(data.encode('utf-8'))
                print('Send selling item to trader.')
                reply = client.recv(1024)
                buy_num = reply.decode('utf-8')
                buy_num = int(buy_num)
                if buy_num == 0:
                    print(f'Fail to buy product{self.productID}.')
                else:
                    print(f'Successfully buy {buy_num} product{self.productID}.')
            except:
                print('Fail to send selling item to trader, try again.')
            client.close()

    def election_listening(self):
        # receive message during election, end when find a trader
        while True:
            conn, _ = self.server.accept()
            request = conn.recv(1024)
            data = request.decode('utf-8')
            fields = data.split('|')

            if fields[0] == '0':
                # after election trader send his address to all peers
                # request_category|trader_address
                trader_address, trader_port = fields[1].split('-')
                self.trader_list.append = (trader_address, trader_port)
                break
                conn.send('1'.encode('utf-8'))
                print("Set new trader.")
                time.sleep(2)
            elif fields[0] == '1':
                # for election
                if self.election():
                    break
            conn.close()

    def election(self):
        # election process
        print(f'Peer {self.peer_id} starting election.')
        alive_peer = []
        larger_peer = []
        with open('./config') as f:
            for line in f:
                fields = line.split(':')
                if int(fields[0]) > self.peer_id:
                    larger_peer.append((fields[1], int(fields[2])))
                if int(fields[0]) != self.peer_id:
                    alive_peer.append(line)
            f.close()

        if not larger_peer:
            # find the trader
            self.istrader = True
            for peer in alive_peer:
                fields = peer.split(':')
                client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                client.connect((fields[1], int(fields[2])))
                client.send(f'{0}|{self.address[0]}-{self.address[1]}'.encode('utf-8'))
                client.recv(1024)
                client.close()
            with open('./config', 'w') as f:
                f.writelines(alive_peer)
                f.close()
            return True
        else:
            # continue to send message
            for address in larger_peer:
                client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                client.connect(address)
                client.send(f'{1}'.encode('utf-8'))
                client.close()
            return False

    def peer_listening(self):
        # receive message for resetting trader
        while True:
            time.sleep(3)
            conn, _ = self.server.accept()
            request = conn.recv(1024)
            data = request.decode('utf-8')
            fields = data.split('|')

            if fields[0] == '8':
                # 1 trader dead, reset trader_list
                # request_category|trader_address
                self.trader_list = []
                trader_address, trader_port = fields[1].split('-')
                self.trader_list.append = (trader_address, trader_port)


    def process(self):
        # send all requests
        time.sleep(5)
        # request_category|product_id|seller_address(for reply message)
        # for _ in range(2):
        #     if not self.istrader:
        #         self.election()
        #         self.election_listening()

        with ThreadPoolExecutor(5) as executor:
            if self.istrader:
                task1 = executor.submit(self.trader_listening_no_cache)
                task2 = executor.submit(self.trader_process)
                # task1 = threading.Thread(target=self.trader_listening_no_cache, args=())
                # task2 = threading.Thread(target=self.trader_process, args=())
                # task1.start()
                # task2.start()
            else:
                if self.isSeller:
                    task3 = executor.submit(self.seller_update_stock)
                    # task3 = multiprocessing.Process(self.seller_update_stock())
                    # task3.start()
                elif self.isBuyer:
                    task4 = executor.submit(self.buyer_process)
                    # task4 = multiprocessing.Process(self.buyer_process())
                    # task4.start()
                task5 = executor.submit(self.peer_listening)
                # task5 = multiprocessing.Process(self.peer_listening())
                # task5.start()



