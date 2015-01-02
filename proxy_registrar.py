#!/usr/bin/python
# -*- coding: iso-8859-15 -*-
"""
Clase (y programa principal) para un servidor de SIP
en UDP simple
"""

import SocketServer
import sys
import time
import socket
import os
from xml.sax import make_parser
from xml.sax.handler import ContentHandler

#Comprobamos errores en los datos

try:
	CONFIG = sys.argv[1]
except IndexError:
	print 'Usage1: python proxy_registrar.py config'
	raise SystemExit

metodos = ('REGISTER', 'INVITE', 'BYE', 'ACK')
dic_clients = {}

class XMLHandlerPR(ContentHandler):
    """
    Handler de XML de Servidor Registar-Proxy
    """
    def __init__(self):
        """
        Constructor, creamos las variables
        """
        self.lista_dic = []
        self.tags = ['server', 'database', 'log']
        self.attrs = {
            'server': ['name', 'ip', 'puerto'],
            'database': ['path', 'passwdpath'],
            'log': ['path']
        }

    def startElement(self, name, attrs):
        """
        Función que se llama al abrir una etiqueta
        """
        dic_attrs = {}
        if name in self.tags:
            dic_attrs['tag'] = name
            for atributo in self.attrs[name]:
                dic_attrs[atributo] = attrs.get(atributo, "")
                #Guardamos en una lista los diccionarios de atributos
            self.lista_dic.append(dic_attrs)

    def get_tags(self):
        """
        Función con la que se obtiene la lista de diccionarios de atributos
        """
        return self.lista_dic


class SIPRegisterHandler(SocketServer.DatagramRequestHandler):
    """
    SIP server register and proxy class
    """
    def handle(self):
        # Escribe dirección y puerto del cliente (de tupla client_address)
        print self.client_address
        while 1:
            # Leyendo línea a línea lo que nos envía el cliente
            line = self.rfile.read()
            if not line:
                break
            print "El cliente nos manda:\r\n" + line
            
            peticion = line.split()
            metodo = peticion[0]
            encontrado = False
            #Es un metodo válido?
            if metodo not in metodos:
            
                self.wfile.write('SIP/2.0 400 Method Not Allowed\r\n\r\n')
                print 'Enviamos: SIP/2.0 400 Method Not Allowed\r\n\r\n'
                
            else:
                #La peticion sigue el estandar SIP?
                sip = peticion[1][:4]
                version = peticion[2]
                user = peticion[1][4:]
                if sip == 'sip:' and '@' in user and version == 'SIP/2.0':

                    ip = self.client_address[0]
                    self.buscar_clientes()
                    
                    if metodo == 'REGISTER':
                    
                        port = user.split(':')[1]
                        user = user.split(':')[0]
                        exp = int(peticion[4])

                        if exp == 0:
                            #Borramos al cliente del diccionario
                            if user in dic_clients:
                                del dic_clients[user]
                                print "Borramos a :" + user
                        else:
                            formato = '%Y-%m-%d %H:%M:%S'
                            date = time.strftime(formato, time.gmtime(time.time()))
                            hora_exp = time.time() + exp
                            expires = time.strftime(formato, time.gmtime(hora_exp))
                            print "Guardamos user:" + user + " IP:" + ip + ' Port:' + str(port) + \
                                  ' Date:' + str(date) + ' Exp:' + str(expires) + '\n'
                            dic_clients[user] = [ip, port, date, expires]
                            
                        self.register2file()
                        self.wfile.write('SIP/2.0 200 OK\r\n\r\n')
                        print '\r\nEnviamos:\r\nSIP/2.0 200 OK\r\n\r\n'
                        
                    elif metodo == 'INVITE':
                        
                        #Guardamos los datos del sdp
                        peticion = line.split('\r\n\r\n')
                        sdp = peticion[1].split('\r\n')
                        dic_sdp = {}
                        for parametro in sdp:
                            key = parametro.split('=')[0]
                            dic_sdp[key] = parametro.split('=')[1]
                          
                        #Buscamos si el destinatario esta registrado
                        for client in dic_clients.keys():
                        
                            if client == user:
                            
                                encontrado = True
                                #Reenviamos el mensaje a receptor
                                ip_receptor = dic_clients[client][0]
                                port_receptor = int(dic_clients[client][1])
                                my_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                                my_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                                my_socket.connect((ip_receptor, port_receptor))
                                print '\r\nReenviamos:\r\n' + line
                                my_socket.send(line)
                                
                                #Esperamos la respuesta
                                try:
                                    data = my_socket.recv(1024)
                                except socket.error:
                                    print 'Error: No server listening at ' + ip_receptor + ' port ' + str(port_receptor)
                                    raise SystemExit
                                    
                                print '\r\nRecibimos:\r\n' + data
                                
                                #Reenviamos el asentimiento al emisor
                                self.wfile.write(data)
                                print '\r\nReenviamos:\r\n' + data

                        if encontrado == False:
                            self.wfile.write('SIP/2.0 404 User Not Found\r\n\r\n')
                            print 'Enviamos: SIP/2.0 404 User Not Found\r\n\r\n'
                            
                    elif metodo == 'ACK':
                    
                        #Buscamos si el destinatario esta registrado
                        for client in dic_clients.keys():
                        
                            if client == user:
                                encontrado = True
                                ip_receptor = dic_clients[client][0]
                                port_receptor = int(dic_clients[client][1])
                                #Reenviamos el ACK al receptor
                                my_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                                my_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                                my_socket.connect((ip_receptor, port_receptor))
                                print '\r\nReenviamos:\r\n' + line
                                my_socket.send(line)

                        if encontrado == False:
                            self.wfile.write('SIP/2.0 404 User Not Found\r\n\r\n')
                            print '\r\nEnviamos: SIP/2.0 404 User Not Found\r\n\r\n'   
                        
                else:
                    self.wfile.write('SIP/2.0 400 Bad Request\r\n\r\n')
                    print '\r\nEnviamos: SIP/2.0 400 Bad Request\r\n\r\n'
                   
            print "DICCIONARIO CLIENTES:", dic_clients
            print

    def register2file(self):
        """
        Registramos a los clientes en un fichero:
        """
        fich = open('registered.txt', 'w')
        fich.write('User\tIP\tPuerto\tResgistro\tExpires\n')
        for key in dic_clients.keys():
            ip = dic_clients[key][0]
            port = str(dic_clients[key][1])
            date = dic_clients[key][2]
            expire = str(dic_clients[key][3])
            fich.write(key + '\t' + ip + '\t' + port + '\t' + date + '\t' + expire + '\n')
        fich.close()

    def buscar_clientes(self):
        """
        Buscamos si han caducado los clientes y borrarlos
        """
        for key in dic_clients.keys():
            expires = dic_clients[key][3]
            hora = time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(time.time()))
            if expires <= hora:
                del dic_clients[key]
                print "Borramos a :" + key


if __name__ == "__main__":
    parser = make_parser()
    xHandler = XMLHandlerPR()
    parser.setContentHandler(xHandler)
    #Comprobamos que el fichero .xml es válido
    try:
        parser.parse(open(CONFIG))
    except:
        print 'Usage: python proxy_registrar.py config'
        raise SystemExit
        
	#Obtenemos los datos de la configuracion
    for dicc in xHandler.lista_dic:
        if dicc['tag'] == 'server':
            name = dicc['name']
            ip_pr = dicc['ip']
            if ip_pr == "":
                ip_pr = "127.0.0.1"
            port_pr = int(dicc['puerto'])
        elif dicc['tag'] == 'database':
            data_path = dicc['path']
            passwdpath = dicc['passwdpath']
        elif dicc['tag'] == 'log':
            path_log = dicc['path']
              
    # Creamos servidor register y escuchamos
    serv = SocketServer.UDPServer(("", port_pr), SIPRegisterHandler)
    print 'Server ' + name + ' listening at port ' + str(port_pr) + '...\n'
    serv.serve_forever()
