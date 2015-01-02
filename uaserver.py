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

metodos = ('INVITE', 'BYE', 'ACK')
dic_sdp = {}

class XMLHandlerUA(ContentHandler):
    """
    Handler de XML de los User Agent
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
		
		
class EchoHandler(SocketServer.DatagramRequestHandler):
    """
    SIP Server
    """

    def handle(self):
        print self.client_address
        while 1:
            # Leyendo línea a línea lo que nos envía el cliente
            line = self.rfile.read()

            # Si no hay más líneas salimos del bucle infinito
            if not line:
                break
            print "El cliente nos manda:\r\n" + line

            peticion = line.split()
            #Obtenemos el método del cliente
            metodo = peticion[0]

            #Esta en mis metodos?
            if metodo not in metodos:
                self.wfile.write('SIP/2.0 400 Method Not Allowed\r\n\r\n')
                print 'Enviamos: SIP/2.0 400 Method Not Allowed\r\n\r\n'
            else:
                sip = peticion[1][:4]
                version = peticion[2]
                user = peticion[1][4:]
                if sip == 'sip:' and '@' in user and version == 'SIP/2.0':
                    if metodo == 'INVITE':
                    
                        #Guardamos los datos del sdp
                        peticion = line.split('\r\n\r\n')
                        sdp = peticion[1].split('\r\n')
                        for parametro in sdp:
                            key = parametro.split('=')[0]
                            dic_sdp[key] = parametro.split('=')[1]
                        self.wfile.write('SIP/2.0 100 Trying\r\n\r\n'
                                         + 'SIP/2.0 180 Ringing\r\n\r\n'
                                         + 'SIP/2.0 200 OK\r\n\r\n')
                        print ('\r\nEnviamos: SIP/2.0 100 Trying\r\n\r\n'
                               + 'Enviamos: SIP/2.0 180 Ringing\r\n\r\n'
                               + 'Enviamos: SIP/2.0 200 OK\r\n\r\n')
                               
                    elif metodo == 'BYE':
                        self.wfile.write('SIP/2.0 200 OK\r\n\r\n')
                        print 'Enviamos: SIP/2.0 200 OK\r\n\r\n'
                    elif metodo == 'ACK':
                        ip_receptor = dic_sdp['o'].split()[1]
                        port_rtp = dic_sdp['m'].split()[1]
                        print 'IP_RTP + PORT_RTP :', ip_receptor, port_rtp
                        aEjecutar = './mp32rtp -i ' + ip_receptor + ' -p ' + str(port_rtp)
                        aEjecutar += ' < ' + path_audio
                        print 'Vamos a ejecutar', aEjecutar
                        os.system(aEjecutar)
                        print 'Ha terminado la cancion\r\n'
                else:
                    self.wfile.write('SIP/2.0 405 Bad Request\r\n\r\n')
                    print 'Enviamos: SIP/2.0 405 Bad Request\r\n\r\n'

if __name__ == "__main__":

    parser = make_parser()
    xHandler = XMLHandlerUA()
    parser.setContentHandler(xHandler)
    #Comprobamos que el fichero .xml es válido
    try:
	    parser.parse(open(CONFIG))
    except:
	    print 'Usage2: python uaserver.py config'
	    raise SystemExit
	
	#Obtenemos los datos de la configuracion
    for dicc in xHandler.lista_dic:
        if dicc['tag'] == 'account':
            username = dicc['username']
            passwd = dicc['passwd']
        elif dicc['tag'] == 'uaserver':
            ip_server = dicc['ip']
            if ip_server == "":
                ip_server = '127.0.0.1'
            port_server = int(dicc['puerto'])
        elif dicc['tag'] == 'rtpaudio':
            port_rtp = int(dicc['puerto'])
        elif dicc['tag'] == 'regproxy':
            ip_pr = dicc['ip']
            port_pr = int(dicc['puerto'])
        elif dicc['tag'] == 'log':
            path_log = dicc['path']
        elif dicc['tag'] == 'audio':
            path_audio = dicc['path']
	    
    # Creamos servidor de eco y escuchamos
    serv = SocketServer.UDPServer(("", port_server), EchoHandler)
    print 'Listening...'
    serv.serve_forever()
