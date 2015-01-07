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
import uaclient
from xml.sax import make_parser
from xml.sax.handler import ContentHandler


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
            'log': ['path']}

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
        while 1:
            # Leyendo línea a línea lo que nos envía el cliente
            line = self.rfile.read()
            if not line:
                break

            ip_emisor = self.client_address[0]
            port_emisor = self.client_address[1]
            log.recv_from(ip_emisor, port_emisor, line)

            peticion = line.split()
            metodo = peticion[0]
            find_emisor = False
            find_recep = False
            #Es un metodo válido?
            if metodo not in metodos:
                respuesta = 'SIP/2.0 400 Method Not Allowed\r\n\r\n'
                self.wfile.write(respuesta)
                log.sent_to(ip_emisor, port_emisor, respuesta)

            else:
                #La peticion sigue el estandar SIP?
                sip = peticion[1][:4]
                version = peticion[2]
                user = peticion[1][4:]
                if sip == 'sip:' and '@' in user and version == 'SIP/2.0':

                    self.buscar_clientes()

                    if metodo == 'REGISTER':

                        port = user.split(':')[1]
                        emisor = user.split(':')[0]
                        exp = int(peticion[4])

                        if exp == 0:
                            #Borramos al cliente del diccionario
                            if emisor in dic_clients:
                                del dic_clients[emisor]
                                print "Borramos a :" + emisor
                        else:
                            hora = time.time()
                            formato = '%Y-%m-%d %H:%M:%S'
                            date = time.strftime(formato, time.gmtime(hora))
                            hora_exp = time.time() + exp
                            expires = time.strftime(
                                formato, time.gmtime(hora_exp))
                            print "Guardamos user:" + emisor + " IP:" \
                                + ip_emisor + ' Port:' + str(port) + ' Date:' \
                                + str(date) + ' Exp:' + str(expires) + '\n'
                            dic_clients[emisor] = [
                                ip_emisor, port, date, expires]

                        self.register2file()

                        respuesta = 'SIP/2.0 200 OK\r\n\r\n'
                        self.wfile.write(respuesta)
                        log.sent_to(ip_emisor, port_emisor, respuesta)

                    elif metodo == 'INVITE':

                        #Guardamos los datos del sdp
                        peticion = line.split('\r\n\r\n')
                        sdp = peticion[1].split('\r\n')
                        dic_sdp = {}
                        for parametro in sdp:
                            key = parametro.split('=')[0]
                            dic_sdp[key] = parametro.split('=')[1]

                        #Comprobamos que el sdp es correcto
                        check_sdp(dic_sdp)

                        #Buscamos si destinatario y emisor están registrados
                        emisor = dic_sdp['o'].split()[0]
                        for client in dic_clients.keys():
                            if client == emisor:
                                find_emisor = True
                            elif client == user:
                                find_recep = True

                        if find_emisor is False or find_recep is False:
                            respuesta = 'SIP/2.0 404 User Not Found\r\n\r\n'
                            self.wfile.write(respuesta)
                            log.sent_to(ip_emisor, port_emisor, respuesta)
                        else:
                            #Guardamos a los participantes de la conversación
                            participantes = [emisor, user]

                            #Reenviamos el mensaje a receptor
                            ip_receptor = dic_clients[user][0]
                            port_receptor = int(dic_clients[user][1])
                            my_socket = socket.socket(
                                socket.AF_INET, socket.SOCK_DGRAM)
                            my_socket.setsockopt(
                                socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                            my_socket.connect((ip_receptor, port_receptor))
                            my_socket.send(line)
                            log.sent_to(ip_receptor, port_receptor, line)

                            #Esperamos la respuesta del servidor
                            try:
                                data = my_socket.recv(1024)
                            except socket.error:
                                error = 'Error: No server listening at ' \
                                    + ip_receptor + ' port ' \
                                    + str(port_receptor)
                                log.error(error)
                                break
                            log.recv_from(ip_receptor, port_receptor, data)

                            #Reenviamos el asentimiento al emisor
                            self.wfile.write(data)
                            log.sent_to(ip_emisor, port_emisor, data)

                    elif metodo == 'ACK':

                        #Buscamos si el destinatario esta registrado
                        for client in dic_clients.keys():

                            if client == user:
                                encontrado = True
                                ip_receptor = dic_clients[user][0]
                                port_receptor = int(dic_clients[user][1])
                                #Reenviamos el ACK al receptor
                                my_socket = socket.socket(
                                    socket.AF_INET, socket.SOCK_DGRAM)
                                my_socket.setsockopt(
                                    socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                                my_socket.connect((ip_receptor, port_receptor))
                                my_socket.send(line)
                                log.sent_to(ip_receptor, port_receptor, line)

                        if encontrado is False:
                            respuesta = 'SIP/2.0 404 User Not Found\r\n\r\n'
                            self.wfile.write(respuesta)
                            log.sent_to(ip_emisor, port_emisor, respuesta)

                    elif metodo == 'BYE':

                        #Buscamos si el destinatario esta registrado
                        #Buscamos si es participante de la conversación
                        for client in dic_clients.keys():

                            if client == user and user in participantes:
                                encontrado = True
                                ip_receptor = dic_clients[user][0]
                                port_receptor = int(dic_clients[user][1])
                                #Reenviamos el BYE al receptor
                                my_socket = socket.socket(
                                    socket.AF_INET, socket.SOCK_DGRAM)
                                my_socket.setsockopt(
                                    socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                                my_socket.connect((ip_receptor, port_receptor))
                                my_socket.send(line)
                                log.sent_to(ip_receptor, port_receptor, line)

                        if encontrado is False:
                            respuesta = 'SIP/2.0 404 User Not Found\r\n\r\n'
                            self.wfile.write(respuesta)
                            log.sent_to(ip_emisor, port_emisor, respuesta)
                        else:
                            #Esperamos la respuesta del servidor
                            try:
                                data = my_socket.recv(1024)
                            except socket.error:
                                error = 'Error: No server listening at ' \
                                    + ip_receptor + ' port ' \
                                    + str(port_receptor)
                                log.error(error)
                                break
                            log.recv_from(ip_receptor, port_receptor, data)

                            #Reenviamos el asentimiento al emisor
                            self.wfile.write(data)
                            log.sent_to(ip_emisor, port_emisor, data)
                            log.eventos('Finishing.')

                else:
                    self.wfile.write('SIP/2.0 400 Bad Request\r\n\r\n')
                    log.sent_to(ip_emisor, port_emisor, respuesta)

            print "DICCIONARIO CLIENTES:", dic_clients
            print

    def register2file(self):
        """
        Registramos a los clientes en un fichero:
        """
        fich = open(data_path, 'w')
        fich.write('User\tIP\tPuerto\tResgistro\tExpires\n')
        for key in dic_clients.keys():
            ip = dic_clients[key][0]
            port = str(dic_clients[key][1])
            date = dic_clients[key][2]
            expire = str(dic_clients[key][3])
            fich.write(
                key + '\t' + ip + '\t' + port + '\t'
                + date + '\t' + expire + '\n')
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


def check_ip(ip):
    """
    Función que comprueba que una IP sea de un rango correcto
    """
    campo_ip = ip_pr.split('.')
    check = False
    if campo_ip[0] >= '0' and campo_ip[0] <= '255':
        if campo_ip[1] >= '0' and campo_ip[1] <= '255':
            if campo_ip[2] >= '0' and campo_ip[2] <= '255':
                if campo_ip[3] >= '0' and campo_ip[3] <= '255':
                    check = True
    if check is False:
        print 'Usage: python proxy_registrar.py config'
        raise SystemExit


                  
if __name__ == "__main__":

    #Comprobamos errores en los datos
    try:
        CONFIG = sys.argv[1]
    except IndexError:
        print 'Usage: python proxy_registrar.py config'
        raise SystemExit

    parser = make_parser()
    xHandler = XMLHandlerPR()
    parser.setContentHandler(xHandler)

    #Comprobamos que el fichero .xml es válido
    try:
        parser.parse(open(CONFIG))
    except IOError:
        print 'Usage: python proxy_registrar.py config'
        raise SystemExit

    #Obtenemos los datos de la configuracion y comprobamos errores
    for dicc in xHandler.lista_dic:
        if dicc['tag'] == 'server':
            name = dicc['name']
            ip_pr = dicc['ip']
            if ip_pr == "":
                ip_pr = "127.0.0.1"
            check_ip(ip_pr)
            port_pr = dicc['puerto']
            try:
                port_pr = int(port_pr)
            except ValueError:
                print 'Usage: python uaclient.py config method option'
                raise SystemExit
        elif dicc['tag'] == 'database':
            data_path = dicc['path']
            passwdpath = dicc['passwdpath']
        elif dicc['tag'] == 'log':
            path_log = dicc['path']

    # Creamos servidor register y escuchamos
    serv = SocketServer.UDPServer(("", port_pr), SIPRegisterHandler)
    print 'Server ' + name + ' listening at port ' + str(port_pr) + '...'
    log = uaclient.Log(path_log)
    log.eventos('Starting...')
    serv.serve_forever()
