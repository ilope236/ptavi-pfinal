#!/usr/bin/python
# -*- coding: iso-8859-15 -*-
"""
Clase (y programa principal) para un servidor de eco en UDP simple
"""

import SocketServer
import sys
import os
from xml.sax import make_parser
from xml.sax.handler import ContentHandler

try:
    CONFIG = sys.argv[1]
except IndexError:
    print 'Usage1: python uaserver.py config'
    raise SystemExit
except ValueError:
    print 'Usage2: python server.py IP port audio_file'
    raise SystemExit

metodos = ('INVITE', 'BYE', 'ACK')
aEjecutar = './mp32rtp -i 127.0.0.1 -p 23032 < ' + 'cancion.mp3'


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
		
		
class EchoHandler(SocketServer.DatagramRequestHandler):
    """
    SIP Server
    """

    def handle(self):
        while 1:
            # Leyendo línea a línea lo que nos envía el cliente
            peticion = self.rfile.read()

            # Si no hay más líneas salimos del bucle infinito
            if not peticion:
                break
            print "El cliente nos manda: " + peticion

            #Obtenemos el método del cliente
            metodo = peticion.split()[0]

            #Esta en mis metodos?
            if metodo not in metodos:
                self.wfile.write('SIP/2.0 400 Method Not Allowed\r\n\r\n')
                print 'Enviamos: SIP/2.0 400 Method Not Allowed\r\n\r\n'
            else:
                #La petición sigue el estándar SIP?
                peticion = peticion.split()
                sip = peticion[1][:4]
                version = peticion[2]
                logip = peticion[1]
                if sip == 'sip:' and '@' in logip and version == 'SIP/2.0':
                    if metodo == 'INVITE':
                        self.wfile.write('SIP/2.0 100 Trying\r\n\r\n'
                                         + 'SIP/2.0 180 Ringing\r\n\r\n'
                                         + 'SIP/2.0 200 OK\r\n\r\n')
                        print ('Enviamos: SIP/2.0 100 Trying\r\n\r\n'
                               + 'Enviamos: SIP/2.0 180 Ringing\r\n\r\n'
                               + 'Enviamos: SIP/2.0 200 OK\r\n\r\n')
                    elif metodo == 'BYE':
                        self.wfile.write('SIP/2.0 200 OK\r\n\r\n')
                        print 'Enviamos: SIP/2.0 200 OK\r\n\r\n'
                    elif metodo == 'ACK':
                        print 'Vamos a ejecutar', aEjecutar
                        os.system(aEjecutar)
                        print 'Ha terminado la cancion\r\n'
                else:
                    self.wfile.write('SIP/2.0 405 Bad Request\r\n\r\n')
                    print 'Enviamos: SIP/2.0 405 Bad Request\r\n\r\n'

if __name__ == "__main__":

    parser = make_parser()
    xHandler = XMLHandler()
    parser.setContentHandler(xHandler)
    #Comprobamos que el fichero .xml es válido
    try:
	    parser.parse(open(CONFIG))
    except:
	    print 'Usage3: python uaserver.py config'
	    raise SystemExit
	
	#Obtenemos los datos de la configuracion
    for dicc in xHandler.lista_dic:
        if dicc['name'] == 'account':
            username = dicc['username']
            print 'username ' + username
            passwd = dicc['passwd']
            print 'password ' + passwd
        elif dicc['name'] == 'uaserver':
            ip_server = dicc['ip']
            print 'ip_server ' + ip_server
            port_server = dicc['puerto']
            print 'puerto_server ' + port_server
        elif dicc['name'] == 'rtpaudio':
            port_rtp = dicc['puerto']
            print 'puerto_rtp ' + port_rtp
        elif dicc['name'] == 'regproxy':
            ip_pr = dicc['ip']
            print 'ip_pr ' + ip_pr
            port_pr = dicc['puerto']
            print 'puerto_proxy ' + port_pr
        elif dicc['name'] == 'log':
            path_log = dicc['path']
            print 'log ' + path_log
        elif dicc['name'] == 'audio':
            path_audio = dicc['path']
            print 'audio ' + path_audio
	    
    # Creamos servidor de eco y escuchamos
    serv = SocketServer.UDPServer(("", 1111), EchoHandler)
    print 'Listening...'
    serv.serve_forever()
