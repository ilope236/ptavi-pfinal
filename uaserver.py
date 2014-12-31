#!/usr/bin/python
# -*- coding: iso-8859-15 -*-
"""
Clase (y programa principal) para un servidor de eco en UDP simple
"""

import SocketServer
import sys
import os


try:
    IP = sys.argv[1]
    PORT = int(sys.argv[2])
    CANCION = sys.argv[3]
except IndexError:
    print 'Usage: python server.py IP port audio_file'
    raise SystemExit
except ValueError:
    print 'Usage: python server.py IP port audio_file'
    raise SystemExit

metodos = ('INVITE', 'BYE', 'ACK')
aEjecutar = './mp32rtp -i 127.0.0.1 -p 23032 < ' + CANCION


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
    # Creamos servidor de eco y escuchamos
    serv = SocketServer.UDPServer(("", PORT), EchoHandler)
    print 'Listening...'
    serv.serve_forever()
