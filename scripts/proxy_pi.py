# -*- coding: utf-8 -*-
"""
proxy_pi.py — Reenviador TCP que corre DENTRO de WSL2.
================================================================================
Expone la pasarela PiGateway (que corre en Windows) hacia otras PC de la red,
reutilizando el mismo camino de exposición que ya usa Vite.

POR QUÉ DENTRO DE WSL Y NO EN WINDOWS
--------------------------------------------------------------------------------
El puerto 5173 es alcanzable desde otras PC porque el servidor de Vite vive
dentro de WSL2. Lo que el firewall de Windows permite no es un `node.exe` de
Windows, sino el relay de WSL. Un proceso arrancado del lado Windows NO hereda
esa regla; uno arrancado dentro de WSL sí, porque sale por el mismo camino.

    Otra PC  --->  Windows:5173  --->  [relay WSL]  --->  WSL:5173 (este proxy)
                                                              |
                                                              v
                                              Windows:5000 (gw4Pi.exe)

DOS CONTROLES DE ACCESO, COMPLEMENTARIOS
--------------------------------------------------------------------------------
ALLOW_PREFIX filtra por IP de origen en el accept(), antes de leer un solo
byte de la petición. Su eficacia depende del modo de red de WSL:

  - Modo espejo (mirrored): WSL comparte las interfaces de Windows y la IP de
    origen real se conserva. El filtro funciona y es el control más barato.
  - Modo NAT: el relay reescribe el origen y toda conexión remota llega con la
    misma dirección 172.18.x.x. El filtro no distingue clientes.

Para saber en cuál está, mire el log: si ve IP distintas entre sí, se conserva
el origen real y el filtro sirve.

PI_TOKEN funciona en ambos modos: el proxy lee la cabecera de la petición
HTTP, exige `X-PI-Token: <valor>` y responde 403 si falta o no coincide. El
cuerpo y la respuesta siguen pasando sin modificación.

En una PC con dos interfaces (red corporativa por cable y hotspot por WiFi),
use los dos: ALLOW_PREFIX acota a la subred del hotspot y el token cubre el
caso de que otro equipo entre por esa misma subred.

USO
--------------------------------------------------------------------------------
    # 1. En Windows, la pasarela en loopback:
    #    .\\gw4Pi.exe 5000 tpi.southernperu.com.pe
    #
    # 2. En WSL (con Vite detenido, porque comparten el 5173):
    PI_TOKEN="una-frase-larga-y-privada" python3 proxy_pi.py
    #
    # 3. Desde otra PC:
    #    curl -H "X-PI-Token: una-frase-larga-y-privada" http://10.60.72.85:5173/health

Variables de entorno:
    PROXY_PORT    puerto de escucha en WSL      (por defecto 5173)
    TARGET_HOST   destino: la pasarela          (por defecto 127.0.0.1)
    TARGET_PORT   puerto de la pasarela         (por defecto 5000)
    PI_TOKEN      token exigido en X-PI-Token   (vacío = sin verificación)
    ALLOW_PREFIX  prefijos IP permitidos, separados por comas
                  ej. "10.60.72.72" para una sola laptop, o "10.60." para
                  toda la subred del hotspot   (vacío = cualquiera)

ADVERTENCIA: sin PI_TOKEN, quien alcance este puerto consulta el PI con las
credenciales de Windows del proceso gw4Pi.
================================================================================
"""

import os
import sys
import socket
import threading
from datetime import datetime

PROXY_PORT   = int(os.environ.get('PROXY_PORT', '5173'))
TARGET_HOST  = os.environ.get('TARGET_HOST', '127.0.0.1')
TARGET_PORT  = int(os.environ.get('TARGET_PORT', '5000'))
PI_TOKEN     = os.environ.get('PI_TOKEN', '').strip()
ALLOW_PREFIX = [p.strip() for p in os.environ.get('ALLOW_PREFIX', '').split(',')
                if p.strip()]

BUFFER            = 65536
MAX_CABECERA      = 65536   # tope de la cabecera HTTP que se inspecciona
TIMEOUT_CABECERA  = 15      # segundos para recibir la cabecera completa
FIN_CABECERA      = b'\r\n\r\n'

_CUERPO_403 = b'{"error":"Falta o no coincide la cabecera X-PI-Token."}'
# Content-Length calculado, nunca escrito a mano: un valor mayor que el cuerpo
# real deja al cliente esperando bytes que jamas llegan.
RESP_403 = (b'HTTP/1.1 403 Forbidden\r\n'
            b'Content-Type: application/json; charset=utf-8\r\n'
            b'Content-Length: ' + str(len(_CUERPO_403)).encode() + b'\r\n'
            b'Connection: close\r\n'
            b'\r\n' + _CUERPO_403)


def log(msg):
    print('[{}] {}'.format(datetime.now().strftime('%H:%M:%S'), msg), flush=True)


def permitido(ip):
    if not ALLOW_PREFIX:
        return True
    return any(ip.startswith(p) for p in ALLOW_PREFIX)


def leer_cabecera(sock):
    """
    Lee hasta el fin de la cabecera HTTP y devuelve esos bytes.

    Los bytes leídos se reenvían después tal cual, de modo que el cuerpo de la
    petición nunca se toca. Devuelve None si la conexión cierra antes, si la
    cabecera excede el tope, o si vence el plazo de lectura.

    El plazo importa: tráfico que no es HTTP (TLS contra un puerto plano,
    sondas de escáner) nunca contiene \\r\\n\\r\\n, así que sin timeout cada
    conexión de esas retendría un hilo hasta que el otro extremo se rinda.
    """
    datos = b''
    sock.settimeout(TIMEOUT_CABECERA)
    try:
        while FIN_CABECERA not in datos:
            if len(datos) > MAX_CABECERA:
                return None
            try:
                trozo = sock.recv(BUFFER)
            except (OSError, socket.timeout):
                return None
            if not trozo:
                return None
            datos += trozo
        return datos
    finally:
        # Vuelve a modo bloqueante: el túnel posterior no debe tener plazo,
        # porque una consulta al PI puede tardar minutos.
        try:
            sock.settimeout(None)
        except OSError:
            pass


def token_valido(cabecera):
    """Compara X-PI-Token sin distinguir mayúsculas en el nombre."""
    for linea in cabecera.split(b'\r\n'):
        if b':' not in linea:
            continue
        nombre, _, valor = linea.partition(b':')
        if nombre.strip().lower() == b'x-pi-token':
            return valor.strip().decode('utf-8', 'replace') == PI_TOKEN
    return False


def bombear(origen, destino):
    """Copia bytes en un sentido hasta que la conexión cierre."""
    try:
        while True:
            datos = origen.recv(BUFFER)
            if not datos:
                break
            destino.sendall(datos)
    except OSError:
        pass
    finally:
        # half-close: avisa al otro extremo que no habrá más datos en este
        # sentido, sin cortar el sentido contrario.
        try:
            destino.shutdown(socket.SHUT_WR)
        except OSError:
            pass


def atender(cliente, origen):
    cabecera = b''

    # Verificación de token: solo si PI_TOKEN está definido.
    if PI_TOKEN:
        cabecera = leer_cabecera(cliente)
        if cabecera is None:
            cliente.close()
            return
        if not token_valido(cabecera):
            log('RECHAZADO ({}) token ausente o incorrecto'.format(origen))
            try:
                cliente.sendall(RESP_403)
            except OSError:
                pass
            cliente.close()
            return

    destino = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        destino.connect((TARGET_HOST, TARGET_PORT))
    except OSError as e:
        log('error hacia la pasarela {}:{} -> {}'.format(
            TARGET_HOST, TARGET_PORT, e))
        cliente.close()
        destino.close()
        return

    # Reenvía la cabecera ya leída antes de abrir el túnel.
    if cabecera:
        try:
            destino.sendall(cabecera)
        except OSError:
            cliente.close()
            destino.close()
            return

    ida = threading.Thread(target=bombear, args=(cliente, destino), daemon=True)
    vuelta = threading.Thread(target=bombear, args=(destino, cliente), daemon=True)
    ida.start()
    vuelta.start()
    ida.join()
    vuelta.join()

    for s in (cliente, destino):
        try:
            s.close()
        except OSError:
            pass


def main():
    servidor = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    servidor.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    try:
        # 0.0.0.0 dentro de WSL: es lo que el relay expone hacia la red.
        servidor.bind(('0.0.0.0', PROXY_PORT))
    except OSError as e:
        if e.errno == 98:   # EADDRINUSE
            log('El puerto {} ya está ocupado dentro de WSL. '
                '¿Está corriendo Vite? Deténgalo o use PROXY_PORT=<otro>.'
                .format(PROXY_PORT))
        else:
            log('No se pudo escuchar en {}: {}'.format(PROXY_PORT, e))
        sys.exit(1)

    servidor.listen(64)
    log('Proxy TCP activo en 0.0.0.0:{} (dentro de WSL)'.format(PROXY_PORT))
    log('Reenviando a {}:{}'.format(TARGET_HOST, TARGET_PORT))
    log('Token X-PI-Token: {}'.format(
        'EXIGIDO' if PI_TOKEN else 'sin verificación (acceso abierto)'))
    log('Filtro de IP: {}'.format(
        ', '.join(ALLOW_PREFIX) if ALLOW_PREFIX else 'ninguno (abierto)'))
    if not ALLOW_PREFIX and not PI_TOKEN:
        log('AVISO: sin filtro de IP y sin token. Cualquiera que alcance este '
            'puerto consulta el PI con sus credenciales de Windows.')
    log('Ctrl+C para detener.')

    try:
        while True:
            cliente, addr = servidor.accept()
            origen = addr[0]
            if not permitido(origen):
                log('RECHAZADO {} (fuera de ALLOW_PREFIX)'.format(origen))
                cliente.close()
                continue
            threading.Thread(target=atender, args=(cliente, origen),
                             daemon=True).start()
    except KeyboardInterrupt:
        log('Detenido.')
    finally:
        servidor.close()


if __name__ == '__main__':
    main()
