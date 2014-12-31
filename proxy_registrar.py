#!/usr/bin/python
# -*- coding: iso-8859-15 -*-
"""
Clase (y programa principal) para un servidor de SIP
en UDP simple
"""

import SocketServer
import sys
import time
import os
from xml.sax import make_parser
from xml.sax.handler import ContentHandler

CONFIG = sys.argv[1]
dic_clients = {}


class XMLHandler(ContentHandler):
    """
    Handler de XML
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
            dic_attrs['name'] = name
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
    SIP server register class
    """
    def handle(self):
        # Escribe dirección y puerto del cliente (de tupla client_address)
        print self.client_address
        while 1:
            # Leyendo línea a línea lo que nos envía el cliente
            line = self.rfile.read()
            if not line:
                break
            print "El cliente nos manda: " + line
            #Cogemos los datos del cliente
            user = line.split()[1][4:]
            ip = self.client_address[0]
            metodo = line.split('\r\n')[0][:8]
            exp = int(line.split('\r\n')[1][8:])
            if metodo == 'REGISTER':
                self.buscar_clientes()
                if exp == 0:
                    #Borramos al cliente del diccionario
                    if user in dic_clients:
                        del dic_clients[user]
                        print "Borramos a :" + user
                else:
                    hora_exp = time.time() + exp
                    formato = '%Y-%m-%d %H:%M:%S'
                    expires = time.strftime(formato, time.gmtime(hora_exp))
                    print "Guardamos user: " + user + " y la IP: " + ip + '\n'
                    dic_clients[user] = [ip, expires]
                self.register2file()
                self.wfile.write("SIP/2.0 200 OK\r\n\r\n")
            else:
                self.wfile.write("SIP/2.0 400 Bad Request\r\n\r\n")
            print "DICCIONARIO CLIENTES:", dic_clients
            print

    def register2file(self):
        """
        Registramos a los clientes en un fichero:
        """
        fich = open('registered', 'w')
        fich.write('User' + '\t' + 'IP' + '\t' + 'Expires' + '\n')
        for key in dic_clients.keys():
            ip = dic_clients[key][0]
            expire = str(dic_clients[key][1])
            fich.write(key + '\t' + ip + '\t' + expire + '\n')
        fich.close()

    def buscar_clientes(self):
        """
        Buscamos si han caducado los clientes y borrarlos
        """
        for key in dic_clients.keys():
            expires = dic_clients[key][1]
            hora = time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(time.time()))
            if expires <= hora:
                del dic_clients[key]
                print "Borramos a :" + key


if __name__ == "__main__":
    parser = make_parser()
    xHandler = XMLHandler()
    parser.setContentHandler(xHandler)
    #Comprobamos que el fichero .xml es válido
    try:
        parser.parse(open(CONFIG))
    except:
        print 'Usage: python proxy_registrar.py config'
        raise SystemExit
	    
    # Creamos servidor register y escuchamos
    serv = SocketServer.UDPServer(("", 2222), SIPRegisterHandler)
    print "Server Proxy-Registrar listening at port 2222...\n"
    serv.serve_forever()
