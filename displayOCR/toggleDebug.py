import time
from multiprocessing.connection import Client

address = ('localhost', 6000)
conn = Client(address, authkey=b'Super secret key')

print('Sending debug toggle')
conn.send('toggleDebug')

conn.close()