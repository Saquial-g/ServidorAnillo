import os
import zmq
import json
import random
import string
import hashlib
import sys
import time

#python subserver.py [route to folder] [address of subserver] [address of known node] [name of subserver]

# Funciones generadoras de ID

def hashString(s):
    sha = hashlib.sha1()
    sha.update(s.encode())
    return sha.hexdigest()

def randomString(n):
    return ''.join(random.choices(string.ascii_lowercase + string.ascii_uppercase + string.digits, k = n))


# Funciones que administran conexiones

def search(add):
    print("Asking for predecesor: " + add)
    pred = context.socket(zmq.REQ)
    pred.connect("tcp://"+ add)
    s = json.dumps({"action": "new", 
                    "ID": ns,
                    "address": address, 
                    })
    pred.send_multipart([s.encode("utf-8"), b''])
    answ = pred.recv_multipart()

    if (answ[0] == b'c'): # Si el nodo le responde que su ID si está en su rango
        predIP = answ[2].decode("utf-8") # El predecesor del nodo al que se conectó ahora es su predecesor
        print("\n" + add + " gave predecessor " + predIP + " - Range obtained:")
        
        respRange = [int(answ[1].decode("utf-8")), ns]
        return [respRange, predIP]
    else: 
        return search(answ[1].decode("utf-8")) # Si no está en rango, recibe la dirección del predecesor del nodo contactado
        

def checkRange(ID): 
    if (respRange[0] > respRange[1]):
        if (ID >= respRange[0] or ID < respRange[1]):
            return True
        else:
            return False
    else:
        if (ID >= respRange[0] and ID < respRange[1]):
            return True
        else:
            return False


def get_files(path): # tomado de https://pynative.com/python-list-files-in-a-directory/
    files = []
    for file in os.listdir(path):
        if os.path.isfile(os.path.join(path, file)):
            files.append(file)
    return files


def transfer():
    print("\nChecking for inadequate files to transfer to " + predIP)
    trans = context.socket(zmq.REQ)
    trans.connect("tcp://" + predIP)
    if (checkTrans()):
        folderDir = sys.argv[1]
        files = get_files(folderDir)
        
        for f in files:
            if (not checkRange(int(f))):
                s = json.dumps({"action": "transfer", "hash": f, "add": address})
                with open(folderDir + "\\" + f, "rb") as f2:
                    trans.send_multipart([s.encode("utf-8"), f2.read()])
                    m = trans.recv()
                    print("Transfer - " + str(f), end="")
                if (m != b'd'):
                    print(" - Received")
                    os.remove(folderDir + "\\" + f)
                else:
                    print(" - Denied")

        print("Inadequate files sent to predecesor\n")
    else:
        print("Current files are adequate\n")
    
    s = json.dumps({"action": "finish", "add": address})
    trans.send_multipart([s.encode("utf-8"), b''])
    m = trans.recv()


def sendNewSuceIP():
    inf = context.socket(zmq.REQ)
    inf.connect("tcp://" + predIP)
    s = json.dumps({"action": "finish", "add": suceIP})
    inf.send_multipart([s.encode("utf-8"), b''])
    m = inf.recv()   


def closingTransfer():
    print("\nClosing command received, transfering files and range of responsability to " + suceIP)
    folderDir = sys.argv[1]
    files = get_files(folderDir)

    sendNewSuceIP()

    trans = context.socket(zmq.REQ)
    trans.connect("tcp://" + suceIP)

    for f in files:
        s = json.dumps({"action": "transfer", "hash": f, "add": address})
        with open(folderDir + "\\" + f, "rb") as f2:
            trans.send_multipart([s.encode("utf-8"), f2.read()])
            m = trans.recv()
            print("Transfer - " + str(f), end="")
        if (m != b'd'):
            print(" - Received")
            os.remove(folderDir + "\\" + f)
        else:
            print(" - Denied")

    s = json.dumps({"action": "finish", "predIP": predIP, "range": respRange[0]})
    trans.send_multipart([s.encode("utf-8"), b''])
    m = trans.recv()
    print("\nClosing server")


def checkTrans():
    folderDir = sys.argv[1]
    files = get_files(folderDir)
    for f in files:
        if (not checkRange(int(f))):
            return True
    return False





# Código principal

rs = randomString(1000)
hg = hashString(rs)
ns = int(hg, 16) # ID del nodo actual
print("\nServer ID: ", end="")
print(ns)
print()

respRange = [ns+1, ns]
transRecv = False

context = zmq.Context()
socket = context.socket(zmq.REP) # Recibe mensajes tanto de clientes como de nodos sucesores
address = sys.argv[2]
socket.bind("tcp://"+ address)

predIP = address
suceIP = address
turnedON = True

if (sys.argv[3] != "default"):
    PrevPredIP = sys.argv[3]
    results = search(PrevPredIP)
    respRange = results[0]
    predIP = results[1]
    print(respRange)
    print()

print("\n------------------------------------| Node initialized |------------------------------------\n")

while turnedON:
    #time.sleep(0.5) #Ping artificial
    m = socket.recv_multipart()
    data = json.loads(m[0].decode("utf-8"))
    chunk = m[1]

    if (data["action"] == 'finish'):
        socket.send(b'ok')
        if "add" in data:
            suceIP = data["add"]
            print("Successor ID defined as " + suceIP)
            if transRecv:
                print("Transfer received from successor")
            transRecv = False
        else:
            predIP = data["predIP"]
            respRange[0] = int(data["range"])
            print("Transfer received from closing node, predecesor updated: " + predIP)
            print("Range updated:")
            print(respRange)
            print()   
            transRecv = False   

        if checkTrans():
            transfer()


    elif (data["action"] == 'close'):
        closingTransfer()
        socket.send(b'Server ' + address.encode("utf-8") + b' closed')
        turnedON = False


    elif (data["action"] == 'new'): # Recibe solicitud de integración de un nuevo nodo
        if (checkRange(int(data["ID"]))): # Revisa si los archivos con la ID del nuevo nodo son su responsabilidad
            socket.send_multipart([b'c', str(respRange[0]).encode("utf-8"), predIP.encode("utf-8")])
            predIP = data["address"]
            respRange = [int(data["ID"])+1, ns]
            print("\nNode " + predIP + " added to network as predecesor, range updated:")
            print(respRange)
            print()
            transfer()
        else:
            socket.send_multipart([b'd', predIP.encode("utf-8")])


    elif (data["action"] == 'transfer'):
        if not transRecv:
            print("\nReceiving files from " + data["add"])
        try:
            with open(sys.argv[1] + "\\" + str(data["hash"]), "wb+") as f2:
                f2.write(chunk)
                f2.close() 
            print("Receive - " + str(data["hash"]))  
            socket.send(b'c')  
            transRecv = True
        except: 
            socket.send(b'd')


    elif (data["action"] == 'upload'):
        i = data["hash"]
        if (chunk == b''):
            if (checkRange(int(i))):
                if (os.path.exists(sys.argv[1] + "\\" + str(i))):
                    print("Upload - " + str(i)  + " - Shortcut taken") 
                    socket.send_multipart([b'f', str(ns).encode("utf-8"), address.encode("utf-8")])
                else:
                    socket.send_multipart([b'c'])
            else: 
                socket.send_multipart([b'd', str(respRange[0]-1).encode("utf-8"), predIP.encode("utf-8"), str(ns).encode("utf-8"), address.encode("utf-8")])

        else:
            with open(sys.argv[1] + "\\" + str(i), "wb+") as f2:
                f2.write(chunk)
                f2.close() 
            print("Upload - " + str(i))  
            socket.send_multipart([b'c', str(ns).encode("utf-8"), address.encode("utf-8")])



    elif(data["action"] == 'download'):
        filename = data["hash"]
        if (checkRange(int(filename))):
            try:
                with open(sys.argv[1] + "\\" + filename, "rb") as f: 
                    print("Download - " + str(filename))  
                    socket.send_multipart([f.read(), str(ns).encode("utf-8"), address.encode("utf-8")])        
            except:
                socket.send_multipart([b'r']) # Pertenece a su rango, pero no lo tiene por ahora, le pide al cliente que reintente en un momento                       
        else:
            socket.send_multipart([b'd', str(respRange[0]-1).encode("utf-8"), predIP.encode("utf-8"), str(ns).encode("utf-8"), address.encode("utf-8")])
            

