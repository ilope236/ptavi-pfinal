#!/usr/bin/python
# -*- coding: iso-8859-15 -*-
"""
Clase (y programa principal) para un servidor de un UA en SIP
"""

import SocketServer
import sys
import os
import uaclient
from xml.sax import make_parser
from xml.sax.handler import ContentHandler

metodos = ('INVITE', 'BYE', 'ACK')
dic_sdp = {}


class EchoHandler(SocketServer.DatagramRequestHandler):
    """
    SIP Server
    """

    def handle(self):
        while 1:
            # Leyendo línea a línea lo que nos envía el cliente
            line = self.rfile.read()

            # Si no hay más líneas salimos del bucle infinito
            if not line:
                break

            ip_emisor = self.client_address[0]
            port_emisor = self.client_address[1]
            log.recv_from(ip_emisor, port_emisor, line)

            peticion = line.split()
            #Obtenemos el método del cliente
            metodo = peticion[0]

            #Esta en mis metodos?
            if metodo not in metodos:
                self.wfile.write('SIP/2.0 400 Method Not Allowed\r\n\r\n')
                log.sent_to(ip_emisor, port_emisor, line)
            else:
                sip = peticion[1][:4]
                version = peticion[2]
                user = peticion[1][4:]
                if sip == 'sip:' and '@' in user and version == 'SIP/2.0':
                    if metodo == 'INVITE':

                        #Guardamos los datos del sdp del INVITE
                        peticion = line.split('\r\n\r\n')
                        sdp = peticion[1].split('\r\n')
                        for parametro in sdp:
                            key = parametro.split('=')[0]
                            dic_sdp[key] = parametro.split('=')[1]

                        respuesta = 'SIP/2.0 100 Trying\r\n\r\n'
                        self.wfile.write(respuesta)
                        log.sent_to(ip_emisor, port_emisor, respuesta)
                        respuesta = 'SIP/2.0 180 Ringing\r\n\r\n'
                        self.wfile.write(respuesta)
                        log.sent_to(ip_emisor, port_emisor, respuesta)

                        #Creamos la cabecera y sdp del 200 OK
                        respuesta = 'SIP/2.0 200 OK\r\n'
                        CABECERA = 'Content-Type: application/sdp\r\n\r\n'
                        sdp = 'v=0\r\n' + 'o=' + username + ' ' + ip_server \
                            + '\r\n' + 's=MiSesion\r\n' + 't=0\r\n' \
                            + 'm=audio ' + str(port_rtp) + ' RTP'
                        respuesta = respuesta + CABECERA + sdp
                        self.wfile.write(respuesta)
                        log.sent_to(ip_emisor, port_emisor, respuesta)

                    elif metodo == 'BYE':

                        #Enviamos el 200 OK
                        respuesta = 'SIP/2.0 200 OK\r\n\r\n'
                        self.wfile.write(respuesta)
                        log.sent_to(ip_emisor, port_emisor, respuesta)
                        log.eventos('Finishing.')

                    elif metodo == 'ACK':

                        ip_receptor = dic_sdp['o'].split()[1]
                        port_rtp_recp = dic_sdp['m'].split()[1]

                        #Enviamos RTP
                        os.system('chmod +x mp32rtp')
                        aEjecutar = './mp32rtp -i ' + ip_receptor + ' -p ' \
                            + str(port_rtp_recp) + ' < ' + path_audio
                        print 'Vamos a ejecutar ', aEjecutar
                        os.system(aEjecutar)
                        print 'Ha terminado la cancion\r\n'
                else:
                    respuesta = 'SIP/2.0 405 Bad Request\r\n\r\n'
                    self.wfile.write(respuesta)
                    log.sent_to(ip_emisor, port_emisor, respuesta)

if __name__ == "__main__":

    #Comprobamos la introducción de datos
    try:
        CONFIG = sys.argv[1]
    except IndexError:
        print 'Usage: python uaserver.py config'
        raise SystemExit

    parser = make_parser()
    xHandler = uaclient.XMLHandlerUA()
    parser.setContentHandler(xHandler)
    #Comprobamos que el fichero .xml es válido
    try:
        parser.parse(open(CONFIG))
    except:
        print 'Usage: python uaserver.py config'
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
            c_ip_serv = uaclient.check_ip(ip_server)
            port_server = dicc['puerto']
            c_port_serv = uaclient.check_port(port_server)
        elif dicc['tag'] == 'rtpaudio':
            port_rtp = dicc['puerto']
            c_port_rtp = uaclient.check_port(port_rtp)
        elif dicc['tag'] == 'regproxy':
            ip_pr = dicc['ip']
            c_ip_pr = uaclient.check_ip(ip_pr)
            port_pr = dicc['puerto']
            c_port_pr = uaclient.check_port(port_pr)
        elif dicc['tag'] == 'log':
            path_log = dicc['path']
        elif dicc['tag'] == 'audio':
            path_audio = dicc['path']

    #Si hay alguna IP o puerto incorrecto imprimimos error
    if c_ip_serv is False or c_port_serv is False or c_port_rtp is False \
        or c_ip_pr is False or c_port_pr is False:
        print 'Usage: python uaclient.py config method option'
        raise SystemExit 

    # Creamos servidor de eco y escuchamos
    serv = SocketServer.UDPServer(("", int(port_server)), EchoHandler)
    print 'Listening...'
    log = uaclient.Log(path_log)
    log.eventos('Starting...')
    serv.serve_forever()
