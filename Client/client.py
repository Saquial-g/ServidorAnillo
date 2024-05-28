import os
import zmq
import sys
import hashlib
import json
import time


def getHash(file):
  with open(file, "rb") as f: #tomado de https://stackoverflow.com/questions/3431825/generating-an-md5-checksum-of-a-file
      for chunk in iter(lambda: f.read(4096), b""):
        sha.update(chunk)
  ns = int(sha.hexdigest(), 16)
  return ns


def generateTorrent(name, torrent):
  with open(name + '.torrent', 'w') as f:
    for text in torrent:
        f.write(str(text) + "\n")


def orderDict(servers):
  servers = {key:value for key, value in sorted(servers.items(), key=lambda item: int(item[0]))} #Organiza los servidores, tomado de https://stackoverflow.com/questions/22264956/how-to-sort-dictionary-by-key-in-numerical-order-python
  servers = dict(reversed(list(servers.items()))) # invierte para que servidores sea de mayor a menor, tomado de  https://www.i2tutorials.com/how-to-reverse-order-of-keys-in-python-dict/
  return servers


def selectServer(servers, add, rk):
  key = 0
  for k, v in servers.items():
    if (int(k) >= rk):
      add = v
      key = k

  if (len(servers) != 0):
    if (int(key) < rk):
      ser = list(servers.values())
      add = ser[len(ser)-1]

  return [key, add]


def upload(add, servers):
  with open(name, "rb") as f:
    print("Trying on " + add)
    nex = True
    chunk = b''

    while True: 
      if nex:
        prevChunk = chunk
        chunk = f.read(chunksize) #Obtener el chunk y su hash
        if not chunk:
          return servers
          break
        m = hashlib.sha1()
        m.update(chunk)
        hg = m.hexdigest()
        hc = int(hg, 16)
        nex = False 

        r = selectServer(servers, add, hc)
        add = r[1]
        socket = context.socket(zmq.REQ)
        socket.connect("tcp://" + add)

      if (prevChunk != chunk): #revisa que no se estén enviando chunks vacios para agilizar la subida
        s = json.dumps({"action": "upload", "hash": hc})

        socket.send_multipart([s.encode("utf-8"), b''])
        poller = zmq.Poller()
        poller.register(socket, zmq.POLLIN)
        if poller.poll(10*1000): 
          m = socket.recv_multipart()    
          r = m[0]
            
          if (r == b'c'):
            socket.send_multipart([s.encode("utf-8"), chunk])
            m = socket.recv_multipart() 

            servers.update({m[1].decode("utf-8"): m[2].decode("utf-8")})
            servers = orderDict(servers)
            torrent.append(hc)
            print("Upload - " + str(hc)  + " - " +  m[2].decode("utf-8"))
            nex = True 

          elif (r == b'd'):
            servers.update({m[3].decode("utf-8"): m[4].decode("utf-8")})
            add = m[2].decode("utf-8")
            socket = context.socket(zmq.REQ)
            socket.connect("tcp://"+ add)
            servers = orderDict(servers)
            print("Inadequate server, attemting with predecesor " + m[2].decode("utf-8") + " (Server added to server list)")

          else:
            servers.update({m[1].decode("utf-8"): m[2].decode("utf-8")})
            servers = orderDict(servers)
            torrent.append(hc)
            print("Upload - " + str(hc) +  " - " + add + " - Shortcut taken")
            nex = True 

        else:
          try:
            print("Server " + add + " timed out, removing from server list")
            servers.pop(r[0]) 
          except:
            ...
          r = selectServer(servers, add, hc)
          add = r[1]
          socket = context.socket(zmq.REQ)
          socket.connect("tcp://" + add)
          print("Attempting to connect to " + add)  

      else: 
        torrent.append(hc) 
        print("Upload - " + str(hc) + " - Shortcut taken")
        nex = True 

         
def download(add, torr, servers, n):
  print("Trying on " + add)
  nex = True
  i = 1
  key = ""
  count = 0

  while True: 
    if nex:
      i += 1
      nex = False 

      if i < len(torr):
        r = selectServer(servers, add, int(torrent[i]))
        add = r[1]
        socket = context.socket(zmq.REQ)
        socket.connect("tcp://" + add)
      else:
        return servers

    s = json.dumps({"action": "download", "hash": torrent[i]})

    socket.send_multipart([s.encode("utf-8"), b''])
    poller = zmq.Poller()
    poller.register(socket, zmq.POLLIN)
    if poller.poll(10*1000): 
      m = socket.recv_multipart() 
      chunk = m[0]  

      if (chunk != b'd' and chunk != b'r'):
        servers.update({m[1].decode("utf-8"): m[2].decode("utf-8")})
        servers = orderDict(servers)
        with open(n, "ab+") as f2:
          f2.write(chunk)
          f2.close()
        print("download - " + str(torrent[i]) + " - " +  m[2].decode("utf-8"))
        nex = True 

      elif (chunk == b'r'):
        if (count <= 4):
          print("Server " + add + " is adequate but chunk couldn't be found, retrying...")
          time.sleep(5)
          count += 1
        else:
          print("Chunk couldn't be found, cancelling download")
          try:
            os.remove(n)
          except:
            ...
          count = 0
          return servers

      else:
        servers.update({m[3].decode("utf-8"): m[4].decode("utf-8")})
        servers = orderDict(servers)
        socket = context.socket(zmq.REQ)
        add = m[2].decode("utf-8")
        socket.connect("tcp://" + m[2].decode("utf-8"))
        print("Not found, checking " + m[2].decode("utf-8")  + " (Server added to server list)")

    else:   
      try:
        print("Server " + add + " timed out, removing from server list")
        servers.pop(r[0]) 
      except:
        ...
      r = selectServer(servers, add, int(torrent[i]))
      add = r[1]
      socket = context.socket(zmq.REQ)
      socket.connect("tcp://" + add)
      print("Attempting to connect to " + add)  


def uniqueName(torrent):
  dup = 0
  n = torrent[0]
  while os.path.exists(n): #Hace que genere un archivo nuevo si el archivo ya fue descargado
    if "." in n:
      if dup == 0:
        dup += 1
        n = n.replace(".", "(" + str(dup) + ").") #tomado de https://stackoverflow.com/questions/30232344/insert-a-string-before-a-substring-of-a-string
      else:
        n = n.replace("(" + str(dup) + ").", "(" + str(dup + 1) + ").")
        dup += 1
    else:
      if dup == 0:
        dup += 1
        n = n + "(" + str(dup) + ")" 
      else:
        n = n.replace("(" + str(dup) + ")", "(" + str(dup + 1) + ")")
        dup += 1
  return n



picture = b''
context = zmq.Context()
sha = hashlib.sha1()
servers = {}
torrent = []
chunksize = 5242880

add = sys.argv[1]

if (sys.argv[2] == "upload"):
  #try:
    name = sys.argv[3]
    h = getHash(name)
    torrent.append(name)
    torrent.append(h)
    servers = upload(add, servers)  
    generateTorrent(name.split(".")[0], torrent)
  #except:
    #print("Archivo especificado no encontrado")


elif (sys.argv[2] == "download"):
  #try:
    with open(sys.argv[3], "r") as f:
      torrent = f.read().splitlines() # tomado de https://stackoverflow.com/questions/12330522/how-to-read-a-file-without-newlines
      n = uniqueName(torrent)
      download(add, torrent, servers, n)      
  #except:
    #print("Archivo torrent no encontrado")


elif(sys.argv[2] == "close"):
  #try:
    print("Attempting to close server " + add)
    socket = context.socket(zmq.REQ)
    socket.connect("tcp://" + add) 
    s = json.dumps({"action": "close"})
    socket.send_multipart([s.encode("utf-8"), b''])
    print(socket.recv().decode("utf-8"))
  #except:
    #print("Node not found")

else:
   print("Solicitud invalida")

