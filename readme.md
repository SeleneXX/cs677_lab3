## Instructions
Modify peers in Run.py as you want. If ``state=True`` then this peer is a seller, else this peer is a buyer.
````python3
peer = Peer(address, peer_id, state, product_ID, product_num, warehouse_addr, use_cache=False)
````
Just run this script. Then all the peers and warehouse will be run concurrently.