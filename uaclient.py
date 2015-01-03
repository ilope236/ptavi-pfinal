#!/usr/bin/python
# -*- coding: iso-8859-15 -*-
"""
Programa cliente que abre un socket a un servidor
"""

import socket
import sys
import os
import time

from xml.sax import make_parser
from xml.sax.handler import ContentHandler

# Cliente UDP simple.


class Log:
    """
    Clase para escribir los mensajes en el fichero log
    """
    
    def __init__(self, path_log):
    
        self.log = open(path_log, 'a')
    
    def sent_to(self, ip, port, mensaje):
    
        hora = str(time.time())
        mensaje = mensaje.replace('\r\n', ' ')
        evento = 'Sent to ' + ip + ':' + str(port) + ': ' + mensaje + '\r\n'
        string = hora + ' ' + str(evento)
        self.log.write(string)
        print 'Añadimos a log: ' + string

    def recv_from(self, ip, port, mensaje):
    
        hora = str(time.time())
        mensaje = mensaje.replace('\r\n', ' ')
        evento = 'Received form ' + ip + ':' + str(port) + ': ' + mensaje + '\r\n'
        string = hora + ' ' + str(evento)
        self.log.write(string)
        print 'Añadimos a log: ' + string

    def error(self, mensaje):
        
        hora = str(time.time())
        string = hora + ' ' + str(mensaje) + '\r\n'
        print 'Añadimos a log: ' + string
        
    def eventos(self, mensaje):
        
        hora = str(time.time())
        string = hora + ' ' + str(mensaje) + '\r\n'
        self.log.write(string)
        print 'Añadimos a log: ' + string

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


if __name__ == "__main__":

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
                print 'Usage: python uaclient.py config method option'
                raise SystemExit
    except IndexError:
	    print 'Usage: python uaclient.py config method option'
	    raise SystemExit
    except ValueError:
	    print 'Usage: python uaclient.py config method option'
	    raise SystemExit

    parser = make_parser()
    xHandler = XMLHandlerUA()
    parser.setContentHandler(xHandler)
    #Comprobamos que el fichero .xml es válido
    try:
        parser.parse(open(CONFIG))
    except:
        print 'Usage: python uaclient.py config method option'
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
    
    log_ua = Log(path_log)
    
    # Creamos el socket, lo configuramos y lo atamos a un servidor/puerto
    my_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    my_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    my_socket.connect((ip_pr, port_pr))

    #Comprobamos el metodo para crear la peticion
    if METODO == 'REGISTER':

        #Creamos la peticion REGISTER
        peticion = METODO + ' sip:' + username + ':' + str(port_server) + ' SIP/2.0\r\n'
        cabecera = 'Expires: ' + str(OPCION) + '\r\n\r\n'
        peticion = peticion + cabecera
    
    elif METODO == 'INVITE':
        
        #Creamos la peticion INVITE
        peticion = METODO + ' sip:' + OPCION + ' SIP/2.0\r\n'
        CABECERA = 'Content-Type: application/sdp\r\n\r\n'
        sdp = 'v=0\r\n' + 'o=' + username + ' ' + ip_server + '\r\n' \
               + 's=MiSesion\r\n' + 't=0\r\n' + 'm=audio ' + str(port_rtp) + ' RTP' 
        peticion = peticion + CABECERA + sdp

    elif METODO == 'BYE':
    
        #Creamos la petición BYE
        peticion = METODO + ' sip:' + OPCION + ' SIP/2.0\r\n'

    my_socket.send(peticion)
    log_ua.sent_to(ip_pr, port_pr, peticion)

    #Comprobamos que se escucha en el servidor
    try:
        data = my_socket.recv(1024)
    except socket.error:
        error = 'Error: No server listening at ' + ip_pr + ' port ' + str(port_pr)
        log_ua.error(error)
        raise SystemExit

    log_ua.recv_from(ip_pr, port_pr, data)

    data = data.split('\r\n\r\n')
    dic_sdp = {}
    #Comprobamos que han llegado todos los mensajes
    if data[0] == 'SIP/2.0 100 Trying':
        if data[1] == 'SIP/2.0 180 Ringing':
            if data[2].split('\r\n')[0] == 'SIP/2.0 200 OK':
                #Enviamos ACK
                ack = 'ACK sip:' + OPCION + ' SIP/2.0\r\n'
                my_socket.send(ack)
                log_ua.sent_to(ip_pr, port_pr, ack)

                #Guardamos los datos de sdp del 200 OK
                sdp = data[3].split('\r\n')
                for parametro in sdp:
                    key = parametro.split('=')[0]
                    dic_sdp[key] = parametro.split('=')[1]

                ip_UA = dic_sdp['o'].split()[1]
                port_UA = int(dic_sdp['m'].split()[1])
                #Enviamos RTP
                os.system("chmod +x mp32rtp")
                aEjecutar = './mp32rtp -i ' + ip_UA + ' -p ' + str(port_UA) + ' < ' + path_audio 
                print 'Vamos a ejecutar', aEjecutar
                os.system(aEjecutar)
                print 'Ha terminado la cancion\r\n'
                
    # Cerramos todo
    log_ua.log.close()
    my_socket.close()
    print "Fin."
