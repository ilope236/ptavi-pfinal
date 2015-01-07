#!/usr/bin/python
# -*- coding: iso-8859-15 -*-
"""
Programa y clases de un cliente de un User Agent en SIP
"""

import socket
import sys
import os
import time
from xml.sax import make_parser
from xml.sax.handler import ContentHandler


class Log:
    """
    Clase para escribir los mensajes en el fichero log
    """

    def __init__(self, path_log):
        '''
        Constructor, creamos las variables
        '''
        self.path_log = str(path_log)

    def sent_to(self, ip, port, mensaje):
        '''
        Función que escribe en el log cuando se envia un mensaje
        '''
        log = open(self.path_log, 'a')
        hora = str(time.time())
        mensaje = mensaje.replace('\r\n', ' ')
        evento = 'Sent to ' + ip + ':' + str(port) + ': ' + mensaje + '\r\n'
        string = hora + ' ' + str(evento)
        log.write(string)
        print 'Añadimos a ' + self.path_log + ': ' + string
        log.close()

    def recv_from(self, ip, port, mensaje):
        '''
        Función que escribe en el log cuando se recibe un mensaje
        '''
        log = open(self.path_log, 'a')
        hora = str(time.time())
        mensaje = mensaje.replace('\r\n', ' ')
        evento = 'Received form ' + ip + ':' + str(port) \
            + ': ' + mensaje + '\r\n'
        string = hora + ' ' + str(evento)
        log.write(string)
        print 'Añadimos a ' + self.path_log + ': ' + string
        log.close()

    def error(self, mensaje):
        '''
        Función que escribe en el log cuando se produce un error
        '''
        log = open(self.path_log, 'a')
        hora = str(time.time())
        string = hora + ' ' + str(mensaje) + '\r\n'
        log.write(string)
        print 'Añadimos a ' + self.path_log + ': ' + string
        log.close()

    def eventos(self, mensaje):
        '''
        Función que escribe en el log cuando empieza o termina la sesión
        '''
        log = open(self.path_log, 'a')
        hora = str(time.time())
        string = hora + ' ' + str(mensaje) + '\r\n'
        log.write(string)
        print 'Añadimos a ' + self.path_log + ': ' + string
        log.close()


class XMLHandlerUA(ContentHandler):
    """
    Handler de XML de los User Agent
    """

    def __init__(self):
        """
        Constructor, creamos las variables
        """
        self.lista_dic = []
        self.tags = [
            'account', 'uaserver', 'rtpaudio', 'regproxy', 'log', 'audio']
        self.attrs = {
            'account': ['username', 'passwd'],
            'uaserver': ['ip', 'puerto'],
            'rtpaudio': ['puerto'],
            'regproxy': ['ip', 'puerto'],
            'log': ['path'],
            'audio': ['path']}

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


def check_ip(ip):
    """
    Función que comprueba que una IP sea de un rango correcto
    """
    campo_ip = ip.split('.')
    check = False
    if campo_ip[0] >= '0' and campo_ip[0] <= '255':
        if campo_ip[1] >= '0' and campo_ip[1] <= '255':
            if campo_ip[2] >= '0' and campo_ip[2] <= '255':
                if campo_ip[3] >= '0' and campo_ip[3] <= '255':
                    check = True
    return check


def check_port(port):
    """
    Función que comprueba que un puerto sea un número positivo y un entero
    """
    check = False
    if port >= '0':
        check = True
        try:
            port = int(port)
        except ValueError:
            check = False
    return check


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
            if '@' not in OPCION:
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
            c_ip_serv = check_ip(ip_server)
            port_server = dicc['puerto']
            c_port_serv = check_port(port_server)
        elif dicc['tag'] == 'rtpaudio':
            port_rtp = dicc['puerto']
            c_port_rtp = check_port(port_rtp)
        elif dicc['tag'] == 'regproxy':
            ip_pr = dicc['ip']
            c_ip_pr = check_ip(ip_pr)
            port_pr = dicc['puerto']
            c_port_pr = check_port(port_pr)
        elif dicc['tag'] == 'log':
            path_log = dicc['path']
        elif dicc['tag'] == 'audio':
            path_audio = dicc['path']

    #Si hay alguna IP o puerto incorrecto imprimimos error
    print c_ip_serv
    print c_port_serv
    print c_port_rtp
    print c_ip_pr
    print c_port_pr
    if c_ip_serv is False or c_port_serv is False or c_port_rtp is False \
        or c_ip_pr is False or c_port_pr is False:
        print 'Usage11: python uaclient.py config method option'
        raise SystemExit
    

    log_ua = Log(path_log)

    # Creamos el socket, lo configuramos y lo atamos a un servidor/puerto
    my_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    my_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    my_socket.connect((ip_pr, int(port_pr)))

    #Comprobamos el metodo para crear la peticion
    if METODO == 'REGISTER':

        #Creamos la petición REGISTER
        peticion = METODO + ' sip:' + username + ':' \
            + port_server + ' SIP/2.0\r\n'
        cabecera = 'Expires: ' + str(OPCION) + '\r\n\r\n'
        peticion = peticion + cabecera

    elif METODO == 'INVITE':

        #Creamos la petición INVITE
        peticion = METODO + ' sip:' + OPCION + ' SIP/2.0\r\n'
        CABECERA = 'Content-Type: application/sdp\r\n\r\n'
        sdp = 'v=0\r\n' + 'o=' + username + ' ' + ip_server + '\r\n' \
            + 's=MiSesion\r\n' + 't=0\r\n' + 'm=audio ' + port_rtp \
            + ' RTP'
        peticion = peticion + CABECERA + sdp

    elif METODO == 'BYE':

        #Creamos la petición BYE
        peticion = METODO + ' sip:' + OPCION + ' SIP/2.0\r\n\r\n'

    my_socket.send(peticion)
    log_ua.sent_to(ip_pr, int(port_pr), peticion)

    #Comprobamos que se escucha en el servidor
    try:
        data = my_socket.recv(1024)
    except socket.error:
        error = 'Error: No server listening at ' + ip_pr \
            + ' port ' + port_pr
        log_ua.error(error)
        raise SystemExit

    data = data.split('\r\n\r\n')
    dic_sdp = {}
    log_ua.recv_from(ip_pr, port_pr, data[0])

    #Comprobamos que han llegado todos los mensajes de confirmación del INVITE
    if data[0] == 'SIP/2.0 100 Trying':
        if data[1] == 'SIP/2.0 180 Ringing':
            log_ua.recv_from(ip_pr, port_pr, data[1])
            if data[2].split('\r\n')[0] == 'SIP/2.0 200 OK':

                log_ua.recv_from(ip_pr, port_pr, data[2] + ' ' + data[3])
                #Enviamos ACK
                ack = 'ACK sip:' + OPCION + ' SIP/2.0\r\n\r\n'
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
                os.system('chmod +x mp32rtp')
                aEjecutar = './mp32rtp -i ' + ip_UA + ' -p ' \
                    + str(port_UA) + ' < ' + path_audio
                print 'Vamos a ejecutar', aEjecutar
                os.system(aEjecutar)
                print 'Ha terminado la cancion\r\n'

    # Cerramos todo
    my_socket.close()
    print "Fin."
