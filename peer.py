import collections
import multiprocessing
import random
import socket
import threading
from concurrent.futures import ThreadPoolExecutor
import time, datetime

# message category
# 0,1 election.
# 2 trader to warehouse, buy. Reply sell number.
# 3 trader to warehouse, update stock.
# 4 trader to warehouse, cache.
# 5 seller to trader, update stock.
# 6 buyer to trader, buy. Reply sell number.
# 7 trader to trader: check alive.
# 8 trader to peers: set trader.
# 9 trader to warehouse: cache flush


Lock = threading.Lock()
sem = threading.Semaphore(20)


class Warehouse(object):

    def __init__(self, address):
        # address = (IP, port)
        self.address = address
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.bind(address)
        self.server.listen(10000)
        self.item_list = collections.defaultdict(int)
        self.over_selling_count = 0
        self.sell_num = 0

    def process(self):
        time.sleep(5)
        self.starttime = time.time()
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
                            print(f'Sucessfully buy {fields[2]} product{fields[1]}')
                            Lock.acquire()
                            Output = open(f'output/log.txt', mode='a')
                            now = datetime.datetime.now()
                            Output.write(
                                f'{now.strftime("%Y-%m-%d %H:%M:%S")}, ship out {fields[2]} product{fields[1]}!\n')
                            Output.close()
                            Lock.release()
                            conn.send(fields[2].encode('utf-8'))
                            Lock.acquire()
                            self.sell_num += int(fields[2])
                            Lock.release()
                        else:
                            print(f'Sucessfully buy {self.item_list[fields[1]]} product{fields[1]}')
                            Output = open(f'output/log.txt', mode='a')
                            now = datetime.datetime.now()
                            Output.write(
                                f'{now.strftime("%Y-%m-%d %H:%M:%S")}, ship out {self.item_list[fields[1]]} product{fields[1]}!\n')
                            Output.close()
                            Lock.release()
                            conn.send(str(self.item_list[fields[1]]).encode('utf-8'))
                            Lock.acquire()
                            self.sell_num += int(self.item_list[fields[1]])
                            self.item_list[fields[1]] = 0
                            Lock.release()

                elif fields[0] == '3':
                    # update item in stock
                    # request_category|product_id|quantity
                    Lock.acquire()
                    self.item_list[fields[1]] += int(fields[2])
                    Output = open(f'output/log.txt', mode='a')
                    now = datetime.datetime.now()
                    Output.write(
                        f'{now.strftime("%Y-%m-%d %H:%M:%S")}, in stock {fields[2]} product{fields[1]}!\n')
                    Output.close()
                    Lock.release()
                    print(f'Sucessfully update in stock info of Product{fields[1]}: {self.item_list[fields[1]]}')
                    conn.send('1'.encode('utf-8'))

                elif fields[0] == '4':
                    # trader request for stock info
                    # for cache
                    print('Send stock info.')
                    stock = []
                    for key, value in self.item_list.items():
                        pair = f'{key}:{value}'
                        stock.append(pair)
                    message = ','.join(stock)
                    conn.send(message.encode('utf-8'))

                # merge trader's cache
                elif fields[0] == '9':
                    print('Merging.')
                    request_list = fields[1].split(',')
                    request_list = list(map(lambda s: s.split(':'), request_list))
                    request_list.sort(key=lambda e: e[2])
                    for r in request_list:
                        product_id, num = r[0], int(r[1])
                        Lock.acquire()
                        self.item_list[product_id] += num
                        Output = open(f'output/log.txt', mode='a')
                        now = datetime.datetime.now()

                        if num <= 0:
                            Output.write(
                                f'{now.strftime("%Y-%m-%d %H:%M:%S")}, ship out {-num} product{product_id}!\n')
                            self.sell_num -= num
                        else:
                            Output.write(
                                f'{now.strftime("%Y-%m-%d %H:%M:%S")}, in stock {num} product{product_id}!\n')
                        if self.item_list[product_id] < 0:
                            Output.write(
                                f'{now.strftime("%Y-%m-%d %H:%M:%S")}, Oversell!\n')
                            self.sell_num += num
                            self.over_selling_count += 1
                            self.item_list[product_id] = 0
                        Output.close()
                        Lock.release()
                print(f'After {time.time() - self.starttime} seconds:')
                print(f'Oversell {self.over_selling_count} times!')
                print(f'Sell out {self.sell_num} items!')

                conn.close()


class Peer(object):

    def __init__(self, address, peer_id, state, product_ID, product_num, warehouse_addr, use_cache=False):
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
        self.is_electing = False
        self.isBuyer = not state
        self.isSeller = state
        self.cache = collections.defaultdict(int)
        self.warehouse = warehouse_addr
        self.alive_peers = []

        self.use_cache = use_cache
        self.request_list = []

    def seller_update_stock(self):
        # seller produce their product every 5 second
        print('Seller update stock coroutine start.')
        while True:
            trader_addr, trader_port = random.choice(self.trader_list)
            self.clock += 1
            data = f'{5}|{self.productID}|{self.productNum}|{self.clock}'
            client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            try:
                client.connect((trader_addr, int(trader_port)))
                client.send(data.encode('utf-8'))
                print('Send selling item to trader.')
            except:
                print('Fail to send selling item to trader, try again.')
            client.close()
            time.sleep(5)

    def trader_listening(self):
        # trader receive buy and update stock request
        print('Trader listening start.')
        while True:
            with sem:
                time.sleep(0.5)
                if self.use_cache and (not self.cache):
                    self.lookup()
                conn, _ = self.server.accept()
                request = conn.recv(1024)
                data = request.decode('utf-8')
                fields = data.split('|')
                if fields[0] == '6':
                    # receive buy request from buyer
                    # request_category|product_id|quantity
                    print('Receive buy request...')
                    if not self.use_cache:
                        self.forward(2, fields[1], fields[2], conn)
                    else:
                        if self.cache:
                            product_id = fields[1]
                            num_buy = int(fields[2])
                            num_stock = self.cache[product_id]
                            if num_stock:
                                num_get = min(num_buy, num_stock)
                                Lock.acquire()
                                self.cache[product_id] -= num_get
                                Lock.release()
                                conn.send(str(num_get).encode('utf-8'))
                            else:
                                conn.send('0'.encode('utf-8'))
                            Lock.acquire()
                            self.clock = max(self.clock, int(fields[3])) + 1
                            self.request_list.append(f'{product_id}:{-num_get}:{self.clock}')
                            Lock.release()
                            self.cache_flush()
                        else:
                            self.forward(2, fields[1], fields[2], conn)

                elif fields[0] == '5':
                    # receive update stock request from seller
                    # request_category|product_id|quantity
                    print('Receive update stock request...')
                    if not self.use_cache:
                        self.forward(3, fields[1], fields[2])
                    else:
                        if self.cache:
                            product_id = fields[1]
                            num_sell = int(fields[2])
                            Lock.acquire()
                            self.cache[product_id] += num_sell
                            self.clock = max(self.clock, int(fields[3])) + 1
                            self.request_list.append(f'{product_id}:{num_sell}:{self.clock}')
                            Lock.release()
                            self.cache_flush()
                        else:
                            self.forward(3, fields[1], fields[2])
                elif fields[0] == '7':
                    # receive update stock request from seller
                    # request_category
                    print('Alive.')
                conn.close()

    def forward(self, request_category, product_id, num, conn=None):
        # Forward Peers' requests to warehouse.
        print('Forward.')
        message = f'{request_category}|{product_id}|{num}'
        warehouse_addr, warehouse_port = self.warehouse
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.connect((warehouse_addr, int(warehouse_port)))
        client.send(message.encode('utf-8'))
        if request_category == 2:
            # Buy request.
            reply = client.recv(1024)
            conn.send(reply)
        else:
            # Sell request.
            print('Successfully update.')
        client.close()

    def cache_flush(self):
        # Send merge request to warehouse.
        print('Cache flush.')
        if len(self.request_list) == 5:
            # delete cache
            Lock.acquire()
            self.cache = collections.defaultdict(int)
            Lock.release()
            # merge info
            warehouse_addr, warehouse_port = self.warehouse
            client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client.connect((warehouse_addr, int(warehouse_port)))
            message = ','.join(self.request_list)
            client.send(f'9|{message}'.encode('utf-8'))
            # init request_list
            Lock.acquire()
            self.request_list = []
            Lock.release()

    def lookup(self):
        # request for updating cache.
        print('Look up for cache.')
        message = f'{4}'
        warehouse_addr, warehouse_port = self.warehouse
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.connect((warehouse_addr, int(warehouse_port)))
        client.send(message.encode('utf-8'))
        reply = client.recv(1024)
        client.close()
        stock_info = reply.decode('utf-8')
        if stock_info:
            stock_info = stock_info.split('|')
            for pair in stock_info:
                ID, num = pair.split(':')
                Lock.acquire()
                self.cache[ID] = int(num)
                Lock.release()

    def trader_process(self):
        # heart beat
        print('Trader process start.')
        while True:
            time.sleep(2)
            for addr, port in self.trader_list:
                if int(port) != int(self.address[1]):
                    try:
                        # check the status of the other trader
                        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        client.connect((addr, int(port)))
                        client.send(f'{7}'.encode('utf-8'))
                        print('The other trader alive.')
                    except:
                        # if dead, send message to all peers.
                        print(f'After {time.time() - self.starttime} seconds:')
                        print('The other trader dead. Sending message to all peer.')
                        with open('./configuration_file/trader.txt', 'w') as f:
                            f.write(f'{self.address[0]}:{self.address[1]}\n')
                            f.close()
                        for addr, port in self.alive_peers:
                            print(addr,port)
                            client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                            client.connect((addr, int(port)))
                            client.send(f'{8}'.encode('utf-8'))
                        self.trader_list = []
                        with open('./configuration_file/trader.txt') as f:
                            for line in f:
                                if not line:
                                    continue
                                fields = line.split(':')
                                self.trader_list.append((fields[0], int(fields[1])))
                            f.close()
                    client.close()

    def buyer_process(self):
        # buyer request
        print('Buyer process start.')
        while True:
            time.sleep(0.5)
            if self.productNum == 0:
                print('Complete.')
                self.productNum = random.randint(1, 5)
            trader_addr, trader_port = random.choice(self.trader_list)
            self.clock += 1
            data = f'{6}|{self.productID}|{self.productNum}|{self.clock}'
            client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            try:
                client.connect((trader_addr, int(trader_port)))
                client.send(data.encode('utf-8'))
                print('Send buy request to trader.')
                reply = client.recv(1024)
                buy_num = reply.decode('utf-8')
                buy_num = int(buy_num)
                if buy_num == 0:
                    print(f'Fail to buy product{self.productID}.')
                else:
                    print(f'Successfully buy {buy_num} product{self.productID}.')
                self.productNum -= buy_num
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
                # election done
                conn.send('1'.encode('utf-8'))
                print('Stop election.')
                self.is_electing = False
                break
            elif fields[0] == '1':
                # for election
                if not self.is_electing:
                    self.election()
                    self.is_electing = True
            conn.close()

    def election(self):
        self.is_electing = True
        # election process
        print(f'Peer {self.peer_id} starting election.')
        alive_peer = []
        larger_peer = []
        with open('./configuration_file/config.txt') as f:
            for line in f:
                if not line:
                    continue
                fields = line.split(':')
                if int(fields[0]) > self.peer_id:
                    larger_peer.append((fields[1], int(fields[2])))
                if int(fields[0]) != self.peer_id:
                    alive_peer.append(line)
            f.close()

        if not larger_peer:
            # find the trader
            self.istrader = True
            with open('./configuration_file/config.txt', 'w') as f:
                f.writelines(alive_peer)
                f.close()

            with open('./configuration_file/trader.txt', 'a') as f:
                f.write(f'{self.address[0]}:{self.address[1]}\n')
                f.close()
            for peer in alive_peer:
                fields = peer.split(':')
                client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                client.connect((fields[1], int(fields[2])))
                client.send(f'{0}'.encode('utf-8'))
                client.recv(1024)
                client.close()

            self.is_electing = False
        else:
            # continue to send message
            for address in larger_peer:
                client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                client.connect(address)
                client.send(f'{1}'.encode('utf-8'))
                client.close()

    def peer_listening(self):
        # receive message for resetting trader
        print('Peer listening start')
        while True:
            time.sleep(0.5)
            conn, _ = self.server.accept()
            request = conn.recv(1024)
            data = request.decode('utf-8')
            fields = data.split('|')

            if fields[0] == '8':
                # 1 trader dead, reset trader_list
                # request_category|trader_address
                print(f'After {time.time() - self.starttime} seconds:')
                print('1 trader dead. Reset trader list.')
                self.trader_list = []
                with open('./configuration_file/trader.txt') as f:
                    for line in f:
                        if not line:
                            continue
                        fields = line.split(':')
                        self.trader_list.append((fields[0], int(fields[1])))
                    f.close()

    def process(self):
        # send all requests
        time.sleep(5)
        # request_category|product_id|seller_address(for reply message)
        for _ in range(2):
            if not self.istrader:
                self.election()
                if not self.istrader:
                    self.election_listening()
        time.sleep(5)

        with open('./configuration_file/trader.txt') as f:
            for line in f:
                if not line:
                    continue
                fields = line.split(':')
                self.trader_list.append((fields[0], int(fields[1])))
            f.close()

        with open('./configuration_file/config.txt') as f:
            for line in f:
                if not line:
                    continue
                fields = line.split(':')
                self.alive_peers.append((fields[1], int(fields[2])))
            f.close()
        print(self.trader_list)

        self.starttime=time.time()

        with ThreadPoolExecutor(2) as executor:

            if self.istrader:
                task1 = executor.submit(self.trader_listening)
                task2 = executor.submit(self.trader_process)
                # task1 = multiprocessing.Process(target=self.trader_listening)
                # task2 = multiprocessing.Process(target=self.trader_process)
                # task1.start()
                # task2.start()
            else:
                if self.isSeller:
                    task3 = executor.submit(self.seller_update_stock)
                    # task3 = multiprocessing.Process(target=self.seller_update_stock)
                    # task3.start()
                elif self.isBuyer:
                    task4 = executor.submit(self.buyer_process)
                    # task4 = multiprocessing.Process(target=self.buyer_process)
                    # task4.start()
                task5 = executor.submit(self.peer_listening)
                # task5 = multiprocessing.Process(target=self.peer_listening)
                # task5.start()
