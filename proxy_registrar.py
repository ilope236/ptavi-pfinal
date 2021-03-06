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
import random
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
                            #Comprobamos que están los =
                            key = parametro.split('=')[0]
                            try:
                                dic_sdp[key] = parametro.split('=')[1]
                            except IndexError:
                                check_sdp = False

                        #Comprobamos que el sdp es correcto
                        check_sdp = self.check_sdp(dic_sdp)

                        if check_sdp is False:
                            respuesta = 'SIP/2.0 400 Bad Request\r\n\r\n'
                            self.wfile.write(respuesta)
                            log.sent_to(ip_emisor, port_emisor, respuesta)
                        else:
                            #Buscamos si destinatario y emisor están
                            #registrados
                            emisor = dic_sdp['o'].split()[0]
                            for client in dic_clients.keys():
                                if client == emisor:
                                    find_emisor = True
                                elif client == user:
                                    find_recep = True

                            if find_emisor is False or find_recep is False:
                                respuest = 'SIP/2.0 404 User Not Found\r\n\r\n'
                                self.wfile.write(respuest)
                                log.sent_to(ip_emisor, port_emisor, respuest)
                            else:

                                #Introducimos cabecera proxy
                                cab_pr = self.cabecera_proxy()
                                new_inv = peticion[0].split('\r\n')
                                cab = new_inv[0] + '\r\n' + cab_pr + \
                                    new_inv[1] + '\r\n\r\n'
                                new_inv = cab + peticion[1]

                                #Reenviamos el mensaje a receptor
                                ip_receptor = dic_clients[user][0]
                                port_receptor = int(dic_clients[user][1])
                                my_socket = socket.socket(
                                    socket.AF_INET, socket.SOCK_DGRAM)
                                my_socket.setsockopt(
                                    socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                                my_socket.connect((ip_receptor, port_receptor))
                                my_socket.send(new_inv)
                                log.sent_to(
                                    ip_receptor, port_receptor, new_inv)

                                #Esperamos el 100, 180 y 200 del servidor
                                try:
                                    data = my_socket.recv(1024)
                                except socket.error:
                                    error = 'Error: No server listening at ' \
                                        + ip_receptor + ' port ' \
                                        + str(port_receptor)
                                    log.error(error)
                                    resp = 'SIP/2.0 404 User Not Found\r\n\r\n'
                                    self.wfile.write(respuesta)
                                    log.sent_to(ip_emisor, port_emisor, resp)
                                    break
                                log.recv_from(ip_receptor, port_receptor, data)

                                #Introducimos cabecera proxy
                                new_data = data.split('\r\n\r\n')
                                cab_pr = self.cabecera_proxy()
                                trying = new_data[0] + '\r\n' + cab_pr + '\r\n'
                                cab_pr = self.cabecera_proxy()
                                ring = new_data[1] + '\r\n' + cab_pr + '\r\n'
                                cab_pr = self.cabecera_proxy()
                                ok = new_data[2].split('\r\n')
                                sdp = new_data[3]
                                ok = ok[0] + '\r\n' + cab_pr + ok[1] \
                                    + '\r\n\r\n'
                                new_data = trying + ring + ok + sdp

                                #Reenviamos el nuevo asentimiento al emisor
                                self.wfile.write(new_data)
                                log.sent_to(ip_emisor, port_emisor, new_data)

                    elif metodo == 'ACK':

                        #Buscamos si el destinatario esta registrado
                        for client in dic_clients.keys():

                            if client == user:
                                encontrado = True
                                ip_receptor = dic_clients[user][0]
                                port_receptor = int(dic_clients[user][1])

                                #Introducimos cabecera proxy
                                cab_pr = self.cabecera_proxy()
                                ack = line.split('\r\n\r\n')[0] + '\r\n'
                                new_ack = ack + cab_pr + '\r\n'

                                #Reenviamos el nuevo ACK al receptor
                                my_socket = socket.socket(
                                    socket.AF_INET, socket.SOCK_DGRAM)
                                my_socket.setsockopt(
                                    socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                                my_socket.connect((ip_receptor, port_receptor))
                                my_socket.send(new_ack)
                                log.sent_to(
                                    ip_receptor, port_receptor, new_ack)

                        if encontrado is False:
                            respuesta = 'SIP/2.0 404 User Not Found\r\n\r\n'
                            self.wfile.write(respuesta)
                            log.sent_to(ip_emisor, port_emisor, respuesta)

                    elif metodo == 'BYE':

                        #Buscamos si el destinatario está registrado
                        for client in dic_clients.keys():
                            if client == user:
                                find_recep = True
                                ip_receptor = dic_clients[user][0]
                                port_receptor = int(dic_clients[user][1])

                                #Introducimos cabecera proxy
                                cab_pr = self.cabecera_proxy()
                                bye = line.split('\r\n\r\n')[0] + '\r\n'
                                new_bye = bye + cab_pr + '\r\n'

                                #Reenviamos el nuevo BYE al receptor
                                my_socket = socket.socket(
                                    socket.AF_INET, socket.SOCK_DGRAM)
                                my_socket.setsockopt(
                                    socket.SOL_SOCKET,
                                    socket.SO_REUSEADDR, 1)
                                my_socket.connect((ip_receptor, port_receptor))
                                my_socket.send(new_bye)
                                log.sent_to(
                                    ip_receptor, port_receptor, new_bye)

                        if find_recep is False:
                            respuesta = 'SIP/2.0 404 User Not Found\r\n\r\n'
                            self.wfile.write(respuesta)
                            log.sent_to(ip_emisor, port_emisor, respuesta)
                        else:
                            #Esperamos el 200 OK del servidor
                            try:
                                data = my_socket.recv(1024)
                            except socket.error:
                                error = 'Error: No server listening at ' \
                                    + ip_receptor + ' port ' \
                                    + str(port_receptor)
                                log.error(error)
                                resp = 'SIP/2.0 404 User Not Found\r\n\r\n'
                                self.wfile.write(resp)
                                log.sent_to(ip_emisor, port_emisor, resp)
                                break
                            log.recv_from(ip_receptor, port_receptor, data)

                            #Introducimos cabecera proxy
                            cab_pr = self.cabecera_proxy()
                            ok = data.split('\r\n\r\n')[0] + '\r\n'
                            new_ok = ok + cab_pr + '\r\n'

                            #Reenviamos el asentimiento al emisor
                            self.wfile.write(new_ok)
                            log.sent_to(ip_emisor, port_emisor, new_ok)
                            log.eventos('Finishing.')

                else:
                    respuesta = 'SIP/2.0 400 Bad Request\r\n\r\n'
                    self.wfile.write(respuesta)
                    log.sent_to(ip_emisor, port_emisor, respuesta)

            print "DICCIONARIO CLIENTES:", dic_clients, '\r\n\r\n'

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

    def check_sdp(self, dic_sdp):
        """
        Función que comprueba que el sdp es correcto
        """
        #Están todos los campos (v, o, s, t, m) y son correctos?
        campos_sdp = False
        if 'v' in dic_sdp.keys() and dic_sdp['v'] == '0':
            if 't' in dic_sdp.keys() and dic_sdp['t'] == '0':
                #s puede ser cualquier nombre pero no estar vacío
                if 's' in dic_sdp.keys() and len(dic_sdp['s']) != 0:
                    if 'o' in dic_sdp.keys():
                        datos_o = dic_sdp['o'].split()
                        #Comprobamos que hay dos campos en o (user, IP)
                        if len(datos_o) == 2:
                            emisor = datos_o[0]
                            ip = datos_o[1]
                            #Comprobamos que la IP es válida
                            check_ip = uaclient.check_ip(ip)
                            if check_ip and 'm' in dic_sdp.keys():
                                datos_m = dic_sdp['m'].split()
                                #Comprobamos que hay 3 campos
                                if len(datos_m) == 3:
                                    audio = datos_m[0]
                                    port = datos_m[1]
                                    rtp = datos_m[2]
                                    #El puerto de rtp es correcto?
                                    check_port = uaclient.check_port(port)
                                    if check_port:
                                        if audio == 'audio' and rtp == 'RTP':
                                            campos_sdp = True
        return campos_sdp

    def cabecera_proxy(self):
        """
        Función que crea la cabecera del proxy
        """
        num = random.random()
        cabecera = 'Via: SIP/2.0/UDP ' + ip_pr + ':' + port_pr + ';' + \
            'branch=' + str(num) + '\r\n'
        return cabecera


def reestab_usuarios(data_path, dic_clients):
        """
        Reestablecemos usuarios que ya estaban registrados
        """
        fich = open(data_path, 'r')
        usuarios = fich.readlines()
        #Quitamos la primera línea que no contiene usuarios
        usuarios = usuarios[1:]

        for usuario in usuarios:
            datos = usuario.split('\t')
            user = datos[0]
            ip = datos[1]
            port = datos[2]
            date = datos[3]
            #Quitamos \n del expires
            expires = datos[4][:-1]
            print "Guardamos user:" + user + " IP:" + ip + ' Port:' \
                + str(port) + ' Date:' + str(date) + ' Exp:' + str(expires) \
                + '\n'
            dic_clients[user] = [ip, port, date, expires]

        print "DICCIONARIO CLIENTES:", dic_clients, '\r\n\r\n'


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
            c_ip_pr = uaclient.check_ip(ip_pr)
            port_pr = dicc['puerto']
            c_port_pr = uaclient.check_port(port_pr)
        elif dicc['tag'] == 'database':
            data_path = dicc['path']
            passwdpath = dicc['passwdpath']
        elif dicc['tag'] == 'log':
            path_log = dicc['path']

    #Si hay alguna IP o puerto incorrecto imprimimos error
    if c_ip_pr is False or c_port_pr is False:
        print 'Usage: python proxy_registrar.py config'
        raise SystemExit

    #Buscamos si ya había clientes registrados
    reestab_usuarios(data_path, dic_clients)

    # Creamos servidor register y escuchamos
    serv = SocketServer.UDPServer(("", int(port_pr)), SIPRegisterHandler)
    print 'Server ' + name + ' listening at port ' + port_pr + '...'
    log = uaclient.Log(path_log)
    log.eventos('Starting...')
    serv.serve_forever()
