#!/usr/bin/python
# -*- coding: iso-8859-15 -*-
"""
Programa cliente que abre un socket a un servidor
"""

import socket
import sys
import os

from xml.sax import make_parser
from xml.sax.handler import ContentHandler

# Cliente UDP simple.

#Comprobamos errores en los datos
metodos = ('INVITE', 'BYE', 'REGISTER')

try:
    CONFIG = sys.argv[1]
    METODO = sys.argv[2]
    if METODO not in metodos:
        print 'Usage: python uaclient.py config method option'
        raise SystemExit
    elif METODO == 'REGISTER':
        OPCION = int(sys.argv[3])
    else:
        OPCION = sys.argv[3]
        if OPCION[-4:] != '.com' or '@' not in OPCION:
            print 'Usage1: python uaclient.py config method option'
            raise SystemExit
except IndexError:
	print 'Usage2: python uaclient.py config method option'
	raise SystemExit
except ValueError:
	print 'Usage3: python uaclient.py config method option'
	raise SystemExit

class XMLHandler(ContentHandler):
    """
    Handler de XML
    """

    def __init__(self):
        """
        Constructor, creamos las variables
        """
        self.lista_dic = []
        self.tags = ['account', 'uaserver', 'rtpaudio', 'regproxy', 'log', 'audio']
        self.attrs = {
            'account': ['username', 'passwd'],
            'uaserver': ['ip', 'puerto'],
            'rtpaudio': ['puerto'],
            'regproxy': ['ip', 'puerto'],
            'log': ['path'],
            'audio': ['path']
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


if __name__ == "__main__":

    parser = make_parser()
    xHandler = XMLHandler()
    parser.setContentHandler(xHandler)
    #Comprobamos que el fichero .xml es válido
    try:
        parser.parse(open(CONFIG))
    except:
        print 'Usage4: python uaclient.py config method option'
        raise SystemExit

    #Obtenemos los datos de la configuracion
    for dicc in xHandler.lista_dic:
        if dicc['tag'] == 'account':
            username = dicc['username']
            print 'username => ' + username
            passwd = dicc['passwd']
            print 'password => ' + passwd
        elif dicc['tag'] == 'uaserver':
            ip_server = dicc['ip']
            print 'ip_server => ' + ip_server
            port_server = int(dicc['puerto'])
            print 'puerto_server => ' + str(port_server)
        elif dicc['tag'] == 'rtpaudio':
            port_rtp = int(dicc['puerto'])
            print 'puerto_rtp => ' + str(port_rtp)
        elif dicc['tag'] == 'regproxy':
            ip_pr = dicc['ip']
            print 'ip_pr => ' + ip_pr
            port_pr = int(dicc['puerto'])
            print 'puerto_proxy => ' + str(port_pr)
        elif dicc['tag'] == 'log':
            path_log = dicc['path']
            print 'log => ' + path_log
        elif dicc['tag'] == 'audio':
            path_audio = dicc['path']
            print 'audio => ' + path_audio

    # Creamos el socket, lo configuramos y lo atamos a un servidor/puerto
    my_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    my_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    my_socket.connect((ip_pr, port_pr))

    #Comprobamos el metodo para crear la peticion
    if METODO == 'REGISTER':

        #Creamos la peticion REGISTER
        peticion = METODO + ' sip:' + username + ':' + str(port_pr) + ' SIP/2.0\r\n'
        cabecera = 'Expires: ' + str(OPCION) + '\r\n\r\n'
        peticion = peticion + cabecera
    '''	
    elif METODO == INVITE:

    elif METODO == BYE
    '''
    #def enviar_peticion(metodo):
        #"""
        #Función que crea las peticiones y las envía
        #"""
        #peticion = metodo + ' sip:' + USER + '@' + IP + ' SIP/2.0\r\n\r\n'
        #print "Enviando: " + peticion
        #my_socket.send(peticion)

    # Enviamos la peticion
    #enviar_peticion(METODO)
    print "Enviando: " + peticion
    my_socket.send(peticion)

    #Comprobamos que se escucha en el servidor
    try:
        data = my_socket.recv(1024)
    except socket.error:
        print 'Error: No server listening at ' + ip_pr + ' port ' + str(port_pr)
        raise SystemExit

    print 'Recibido -- ', data

    data = data.split('\r\n\r\n')

    #Comprobamos que han llegado todos los mensajes
    if data[0] == 'SIP/2.0 100 Trying':
        if data[1] == 'SIP/2.0 180 Ringing':
	        if data[2] == 'SIP/2.0 200 OK':
		        #Enviamos ACK
		        enviar_peticion('ACK')

    # Cerramos todo

    my_socket.close()
    print "Fin."
