import socket
from threading import Thread
import select
import psycopg2
import psycopg2.extras
import struct
import redis
from redis.client import parse_client_list


class socket_server(Thread):

    def __init__(self, ip = "127.0.0.1", port = 4096 ):
        Thread.__init__(self)
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.ip = ip
        self.port = port
        try:
            self.socket.bind((self.ip, self.port))
        except Exception as e:
            print(str(e))
    
    def run(self):
        self.socket.listen()
        while True:
            client, _address = self.socket.accept()
            handler = connection_handler(client)
            handler.start()
        self.socket.close()

class connection_handler(Thread):

    def __init__(self, connection):
        Thread.__init__(self)
        self.connection = connection
        self.timeout = 60
        self.ESP_key = ""
        self.safe_start = True
        self.db_conn = psycopg2.connect(database="incubator", user='postgres', password='"|sJ7\\Be\\#f^#O1iy\'Po', host='127.0.0.1', port= '5432')
        self.users = object()
        self.node_id = 0
        self.node_name = "" 
        self.redis = redis.Redis(host='localhost', port=6379, db=0, password='zHRyp2n34Rgv6VTFgkrj')

    def start(self):
        cursor = self.db_conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        try:
            is_data_ready = select.select([self.connection], [], [], self.timeout)[0]
            if is_data_ready:
                self.ESP_key = self.connection.recv(64).decode('utf-8')
                sql = """
                SELECT u.userid, n.nodeid, n.name FROM users u
                INNER JOIN usernode un ON u.userid = un.userid
                INNER JOIN nodes n ON n.nodeid = un.nodeid
                WHERE n.nodekey = '{}'
                """.format(self.ESP_key)
                cursor.execute(sql)
                users = cursor.fetchall()
                if users is not None and len(users) > 0:
                    #send http post request
                    pass
                cursor.close()
            else:
                self.safe_start = False
                cursor.close()
                self.db_conn.close()
            
        except Exception as e:
            print(e)
        self.run()
    
    def run(self):
        try:
            while True:
                if not self.safe_start:
                    break
                is_data_ready = select.select([self.connection], [], [], self.timeout)[0]
                if is_data_ready:
                    data = self.connection.recv(64)
                    self.redis.mset({"Node-" + self.node_id: data})
                else:
                    #Timeout reached: Do stuff in here
                    pass


        except Exception as e:
            print(e)

