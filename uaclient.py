#!/usr/bin/python
# -*- coding: iso-8859-15 -*-
"""
Programa cliente que abre un socket a un servidor
"""

import socket
import sys

# Cliente UDP simple.

#Comprobamos errores en los datos
metodos = ('INVITE', 'BYE')

try:
    METODO = sys.argv[1]
    USER = sys.argv[2].split('@')[0]
    IP = sys.argv[2].split('@')[1].split(':')[0]
    PORT = int(sys.argv[2].split(':')[1])
    if METODO not in metodos:
        print 'Usage: python client.py method receiver@IP:SIPport'
        raise SystemExit
except IndexError:
    print 'Usage: python client.py method receiver@IP:SIPport'
    raise SystemExit
except ValueError:
    print 'Usage: python client.py method receiver@IP:SIPport'
    raise SystemExit


def enviar_peticion(metodo):
    """
    Función que crea las peticiones y las envía
    """
    peticion = metodo + ' sip:' + USER + '@' + IP + ' SIP/2.0\r\n\r\n'
    print "Enviando: " + peticion
    my_socket.send(peticion)

# Creamos el socket, lo configuramos y lo atamos a un servidor/puerto
my_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
my_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
my_socket.connect((IP, PORT))

# Enviamos la peticion
enviar_peticion(METODO)

#Comprobamos que se escucha en el servidor
try:
    data = my_socket.recv(1024)
except socket.error:
    print 'Error: No server listening at ' + IP + ' port ' + str(PORT)
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
