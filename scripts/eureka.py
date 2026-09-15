#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=========================================================================
  MONITOR LOCAL — Hogar Inteligente (Eureka 2026)
  I.E.F. "Toquepala" - 6.° "B"
-------------------------------------------------------------------------
  Lee el puerto USB del Arduino y muestra las curvas de temperatura y
  humedad en el navegador. Funciona en Firefox, Chrome o el que tengas.

  COMO USARLO
  -----------
  1) Instalar la libreria que lee el puerto serie (una sola vez):

         sudo apt install python3-serial
         (o bien:  pip3 install pyserial)

  2) Cerrar el Monitor Serie del IDE de Arduino.
     Solo un programa puede usar el puerto USB a la vez.

  3) Ejecutar este archivo:

         python3 monitor_local.py

  4) Abrir en el navegador:   http://localhost:8000

  SI DICE "Permission denied" AL ABRIR EL PUERTO
  ----------------------------------------------
  Tu usuario necesita permiso para usar el puerto serie. Ejecutar:

         sudo usermod -a -G dialout $USER

  ...y despues CERRAR SESION y volver a entrar (o reiniciar).
  Como solucion rapida tambien sirve:  sudo python3 monitor_local.py

  DONDE QUEDAN GUARDADOS LOS DATOS
  --------------------------------
  Cada vez que se ejecuta el programa se crea un archivo nuevo dentro de
  la carpeta  datos/  con la fecha y la hora en el nombre, por ejemplo:

         datos/hogar_2026-09-02_15-40-12.csv

  Cada medicion se escribe en ese archivo APENAS LLEGA del Arduino. Si se
  corta la luz o se cierra el programa, lo ya medido NO se pierde.
  El boton "Descargar datos" de la pagina entrega una copia de ese mismo
  archivo, listo para abrir en Excel o LibreOffice Calc.
=========================================================================
"""

import csv
import datetime
import glob
import json
import os
import re
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer

try:
    import serial
except ImportError:
    print("\n  FALTA LA LIBRERIA pyserial")
    print("  Instalala con:   sudo apt install python3-serial")
    print("              o:   pip3 install pyserial\n")
    sys.exit(1)


# ---------------------------------------------------------------- ajustes
PUERTO_HTTP = 8000
BAUDIOS     = 9600
MAX_DATOS   = 5000          # cuantas mediciones guardamos en memoria (grafico)
CARPETA_CSV = "datos"       # carpeta donde se guardan los archivos CSV

# Columnas del archivo CSV
CABECERA = ["fecha_hora", "segundos", "temperatura", "meta_temp",
            "humedad", "meta_hum", "foco", "ingreso",
            "humidificador", "extractor"]

# Formato de texto del sketch:
#   T: 21.0 / 22.0   H: 50.0 / 50.0   [F---]
RE_TEXTO = re.compile(
    r"T:\s*(-?[\d.]+)\s*/\s*(-?[\d.]+)\s+H:\s*(-?[\d.]+)\s*/\s*(-?[\d.]+)\s*\[(.{4})\]"
)
# Formato del modo grafico:
#   Temp:21.0,MetaTemp:22.0,Hum:50.0,MetaHum:50.0
RE_GRAF = re.compile(
    r"Temp:(-?[\d.]+),MetaTemp:(-?[\d.]+),Hum:(-?[\d.]+),MetaHum:(-?[\d.]+)"
)

datos = []                  # lista de mediciones (solo para el grafico)
candado = threading.Lock()  # para que no se pisen los dos hilos
inicio = time.time()
estado = {"conectado": False, "puerto": "", "mensaje": "Buscando el Arduino...",
          "archivo": "", "guardadas": 0}

ruta_csv = ""               # ruta completa del archivo de esta sesion
archivo_csv = None          # el archivo abierto, listo para escribir
escritor_csv = None


# -------------------------------------------------------------- archivo CSV
def abrir_csv():
    """Crea la carpeta y el archivo CSV de esta sesion, con su cabecera."""
    global ruta_csv, archivo_csv, escritor_csv

    os.makedirs(CARPETA_CSV, exist_ok=True)
    sello = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    ruta_csv = os.path.join(CARPETA_CSV, "hogar_%s.csv" % sello)

    # newline="" es lo que pide el modulo csv para no dejar lineas en blanco
    archivo_csv = open(ruta_csv, "a", newline="", encoding="utf-8")
    escritor_csv = csv.writer(archivo_csv)
    escritor_csv.writerow(CABECERA)
    archivo_csv.flush()

    estado["archivo"] = os.path.basename(ruta_csv)
    return ruta_csv


def guardar_en_csv(medicion):
    """Escribe UNA medicion y la manda al disco de inmediato.

    El flush() es importante: sin el, el sistema guardaria las lineas en
    una memoria intermedia y se perderian si se corta la corriente.
    """
    if escritor_csv is None:
        return
    act = medicion["act"]
    escritor_csv.writerow([
        medicion["fecha"],
        medicion["t"],
        medicion["temp"],
        medicion["metaT"],
        medicion["hum"],
        medicion["metaH"],
        0 if act[0] == "-" else 1,
        0 if act[1] == "-" else 1,
        0 if act[2] == "-" else 1,
        0 if act[3] == "-" else 1,
    ])
    archivo_csv.flush()
    os.fsync(archivo_csv.fileno())
    estado["guardadas"] += 1


# ------------------------------------------------------------ puerto serie
def buscar_puerto():
    """Busca el Arduino entre los puertos USB del sistema."""
    candidatos = sorted(glob.glob("/dev/ttyUSB*") + glob.glob("/dev/ttyACM*"))
    if not candidatos:                       # por si es Windows
        candidatos = ["COM%d" % i for i in range(1, 20)]
    return candidatos


def hilo_serie():
    """Lee el puerto sin parar y va guardando cada medicion."""
    while True:
        puerto = None
        for nombre in buscar_puerto():
            try:
                puerto = serial.Serial(nombre, BAUDIOS, timeout=2)
                estado["conectado"] = True
                estado["puerto"] = nombre
                estado["mensaje"] = "Conectado a " + nombre
                print("  >>> Conectado a", nombre)
                # El reloj NO se reinicia aqui: asi, si el cable se suelta
                # y se vuelve a conectar, el archivo CSV sigue en orden.
                break
            except Exception:
                continue

        if puerto is None:
            estado["conectado"] = False
            estado["mensaje"] = ("No se encontro el Arduino. Revisa el cable USB "
                                 "y que el Monitor Serie del IDE este cerrado.")
            time.sleep(3)
            continue

        # ---- leer linea por linea ----
        try:
            while True:
                cruda = puerto.readline()
                if not cruda:
                    continue
                linea = cruda.decode("utf-8", errors="ignore").strip()
                if not linea:
                    continue

                aparatos = "----"
                m = RE_TEXTO.search(linea)
                if m:
                    aparatos = m.group(5)
                else:
                    m = RE_GRAF.search(linea)
                    if not m:
                        continue          # linea de aviso: la ignoramos

                medicion = {
                    "t":     round(time.time() - inicio, 1),
                    "fecha": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "temp":  float(m.group(1)),
                    "metaT": float(m.group(2)),
                    "hum":   float(m.group(3)),
                    "metaH": float(m.group(4)),
                    "act":   aparatos,
                }
                with candado:
                    # 1) al archivo CSV: queda guardado para siempre
                    try:
                        guardar_en_csv(medicion)
                    except Exception as err:
                        print("  !!! No se pudo escribir en el CSV:", err)
                    # 2) a la memoria: solo para dibujar las curvas
                    datos.append(medicion)
                    if len(datos) > MAX_DATOS:
                        datos.pop(0)

        except Exception as e:
            estado["conectado"] = False
            estado["mensaje"] = "Se perdio la conexion: %s" % e
            print("  !!! Conexion perdida:", e)
            try:
                puerto.close()
            except Exception:
                pass
            time.sleep(2)


# ------------------------------------------------------------ servidor web
PAGINA = r"""<!DOCTYPE html>
<html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Hogar Inteligente - Monitor en vivo</title>
<style>
 :root{--tinta:#1a1a17;--papel:#faf9f5;--borde:#d8d5cc;--azul:#1f4e79;
       --rojo:#c0392b;--cian:#0e7490;--verde:#2e7d32;--gris:#6b6a65}
 *{box-sizing:border-box;margin:0;padding:0}
 body{font-family:'Segoe UI',system-ui,sans-serif;background:var(--papel);
      color:var(--tinta);padding:20px;line-height:1.5}
 .c{max-width:1100px;margin:0 auto}
 header{border-bottom:2px solid var(--tinta);padding-bottom:14px;
        margin-bottom:22px;display:flex;justify-content:space-between;
        align-items:flex-end;flex-wrap:wrap;gap:14px}
 h1{font-size:1.45rem}
 .sub{font-size:.82rem;color:var(--gris);margin-top:2px}
 button,a.boton{font:inherit;font-size:.85rem;font-weight:600;padding:8px 16px;
        border-radius:6px;cursor:pointer;border:1.5px solid var(--tinta);
        background:transparent;color:var(--tinta);margin-left:8px;
        text-decoration:none;display:inline-block}
 a.boton{background:var(--tinta);color:var(--papel)}
 button:hover,a.boton:hover{opacity:.75}
 .aviso{background:#fff8e1;border:1px solid #e0c56a;border-left:4px solid #b8860b;
        padding:12px 16px;border-radius:6px;margin-bottom:20px;font-size:.86rem}
 .aviso.ok{background:#f1f8f1;border-color:#8bbf8f;border-left-color:#2e7d32}
 .tarjetas{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));
           gap:12px;margin-bottom:22px}
 .tj{background:#fff;border:1px solid var(--borde);border-radius:8px;padding:14px 16px}
 .rot{font-size:.68rem;text-transform:uppercase;letter-spacing:.07em;
      color:var(--gris);font-weight:600}
 .val{font-size:1.85rem;font-weight:700;line-height:1.15;margin-top:3px}
 .meta{font-size:.76rem;color:var(--gris)}
 .aparatos{display:flex;gap:10px;flex-wrap:wrap;margin-bottom:22px}
 .ap{flex:1;min-width:120px;background:#fff;border:1px solid var(--borde);
     border-radius:8px;padding:11px 14px;text-align:center;transition:.2s}
 .ap .n{font-size:.74rem;color:var(--gris);font-weight:600}
 .ap .e{font-size:.94rem;font-weight:700;margin-top:2px}
 .ap.on{background:var(--verde);border-color:var(--verde);color:#fff}
 .ap.on .n{color:rgba(255,255,255,.82)}
 .gr{background:#fff;border:1px solid var(--borde);border-radius:8px;
     padding:16px;margin-bottom:16px}
 .gr h2{font-size:.95rem;margin-bottom:10px;display:flex;
        justify-content:space-between;align-items:center}
 .ley{font-size:.74rem;font-weight:500;color:var(--gris)}
 .ley i{display:inline-block;width:11px;height:3px;vertical-align:middle;margin:0 4px 0 10px}
 canvas{width:100%;height:210px;display:block}
 footer{border-top:1px solid var(--borde);padding-top:14px;font-size:.78rem;color:var(--gris)}
</style></head><body><div class="c">

<header>
 <div><h1>Hogar Inteligente — Monitor en vivo</h1>
 <div class="sub">I.E.F. "Toquepala" · Eureka 2026 · Categoría C</div></div>
 <div><a class="boton" href="/datos.csv" download>Descargar datos</a>
      <button onclick="borrar()">Limpiar gráfico</button></div>
</header>

<div id="aviso" class="aviso">Conectando con el Arduino…</div>

<div class="tarjetas">
 <div class="tj"><div class="rot">Temperatura</div>
   <div class="val" id="vT" style="color:var(--rojo)">—</div>
   <div class="meta" id="mT">meta —</div></div>
 <div class="tj"><div class="rot">Humedad</div>
   <div class="val" id="vH" style="color:var(--cian)">—</div>
   <div class="meta" id="mH">meta —</div></div>
 <div class="tj"><div class="rot">Mediciones</div>
   <div class="val" id="vN">0</div><div class="meta">cada 2 segundos</div></div>
 <div class="tj"><div class="rot">Tiempo</div>
   <div class="val" id="vTi">0:00</div><div class="meta">desde el inicio</div></div>
</div>

<div class="aparatos">
 <div class="ap" id="apF"><div class="n">Foco</div><div class="e">apagado</div></div>
 <div class="ap" id="apI"><div class="n">Ingreso</div><div class="e">apagado</div></div>
 <div class="ap" id="apH"><div class="n">Humidificador</div><div class="e">apagado</div></div>
 <div class="ap" id="apE"><div class="n">Extractor</div><div class="e">apagado</div></div>
</div>

<div class="gr"><h2>Temperatura (°C)
 <span class="ley"><i style="background:#c0392b"></i>medida
 <i style="background:#1f4e79"></i>meta
 <i style="background:#2e7d32;height:9px;opacity:.18"></i>rango saludable</span></h2>
 <canvas id="cT"></canvas></div>

<div class="gr"><h2>Humedad relativa (%)
 <span class="ley"><i style="background:#0e7490"></i>medida
 <i style="background:#1f4e79"></i>meta
 <i style="background:#2e7d32;height:9px;opacity:.18"></i>rango saludable</span></h2>
 <canvas id="cH"></canvas></div>

<footer>Guardando en <code id="fArch">…</code> ·
<span id="fNum">0</span> mediciones escritas en disco.<br>
Cada dato se guarda apenas llega, aunque se cierre esta página.
<strong>Limpiar gráfico</strong> solo borra las curvas de la pantalla: el archivo no se toca.</footer>
</div>

<script>
let datos = [];

async function actualizar(){
  try{
    const r = await fetch('/datos.json');
    const j = await r.json();
    datos = j.datos;
    const a = document.getElementById('aviso');
    a.className = 'aviso' + (j.estado.conectado ? ' ok' : '');
    a.textContent = j.estado.mensaje;
    if(datos.length){ tarjetas(datos[datos.length-1]); }
    document.getElementById('vN').textContent = datos.length;
    document.getElementById('fArch').textContent = j.estado.archivo || '—';
    document.getElementById('fNum').textContent  = j.estado.guardadas || 0;
    dibujar();
  }catch(e){}
}

function tarjetas(p){
  document.getElementById('vT').textContent = p.temp.toFixed(1)+' °C';
  document.getElementById('mT').textContent = 'meta '+p.metaT.toFixed(1)+' °C';
  document.getElementById('vH').textContent = p.hum.toFixed(1)+' %';
  document.getElementById('mH').textContent = 'meta '+p.metaH.toFixed(1)+' %';
  const s = Math.floor(p.t);
  document.getElementById('vTi').textContent =
      Math.floor(s/60)+':'+String(s%60).padStart(2,'0');
  const ids=['apF','apI','apH','apE'];
  ids.forEach((id,i)=>{
    const on = p.act[i] !== '-';
    const el = document.getElementById(id);
    el.classList.toggle('on', on);
    el.querySelector('.e').textContent = on ? 'ENCENDIDO' : 'apagado';
  });
}

function dibujar(){
  graficar(document.getElementById('cT'),'temp','metaT','#c0392b',20,24,'°C');
  graficar(document.getElementById('cH'),'hum','metaH','#0e7490',45,55,'%');
}

function graficar(cv,campo,campoMeta,color,bMin,bMax,uni){
  const dpr=window.devicePixelRatio||1, aw=cv.clientWidth, ah=210;
  cv.width=aw*dpr; cv.height=ah*dpr;
  const x=cv.getContext('2d'); x.setTransform(dpr,0,0,dpr,0,0);
  x.clearRect(0,0,aw,ah);
  const mI=44,mD=12,mS=12,mF=26, w=aw-mI-mD, h=ah-mS-mF;

  if(datos.length<2){
    x.fillStyle='#9b9a94'; x.font='13px system-ui'; x.textAlign='center';
    x.fillText('Esperando datos del Arduino…',aw/2,ah/2); return;
  }

  let vs=datos.map(d=>d[campo]).concat(datos.map(d=>d[campoMeta]));
  vs.push(bMin,bMax);
  let mn=Math.min(...vs), mx=Math.max(...vs);
  const hg=Math.max((mx-mn)*0.15,1.5); mn-=hg; mx+=hg;

  const t0=datos[0].t, t1=datos[datos.length-1].t, rt=Math.max(t1-t0,1);
  const X=t=>mI+(t-t0)/rt*w, Y=v=>mS+(1-(v-mn)/(mx-mn))*h;

  x.fillStyle='rgba(46,125,50,.13)';
  x.fillRect(mI,Y(bMax),w,Y(bMin)-Y(bMax));

  x.strokeStyle='#e8e6df'; x.lineWidth=1;
  x.fillStyle='#8a8983'; x.font='11px system-ui'; x.textAlign='right';
  for(let i=0;i<=4;i++){
    const v=mn+(mx-mn)*i/4, y=Y(v);
    x.beginPath(); x.moveTo(mI,y); x.lineTo(mI+w,y); x.stroke();
    x.fillText(v.toFixed(1),mI-7,y+4);
  }
  x.textAlign='center';
  for(let i=0;i<=4;i++){
    const t=t0+rt*i/4;
    x.fillText(Math.floor(t/60)+':'+String(Math.floor(t%60)).padStart(2,'0'),X(t),ah-8);
  }

  x.strokeStyle='#1f4e79'; x.lineWidth=1.5; x.setLineDash([5,4]); x.beginPath();
  datos.forEach((d,i)=> i?x.lineTo(X(d.t),Y(d[campoMeta])):x.moveTo(X(d.t),Y(d[campoMeta])));
  x.stroke(); x.setLineDash([]);

  x.strokeStyle=color; x.lineWidth=2.2; x.lineJoin='round'; x.beginPath();
  datos.forEach((d,i)=> i?x.lineTo(X(d.t),Y(d[campo])):x.moveTo(X(d.t),Y(d[campo])));
  x.stroke();

  const u=datos[datos.length-1];
  x.fillStyle=color; x.beginPath(); x.arc(X(u.t),Y(u[campo]),3.5,0,7); x.fill();
  x.font='bold 12px system-ui'; x.textAlign='right';
  x.fillText(u[campo].toFixed(1)+' '+uni,mI+w-4,Y(u[campo])-9);
}

// La descarga la entrega el servidor en /datos.csv (ver el enlace de arriba).
// Asi el archivo que se baja es el MISMO que esta guardado en el disco,
// con todas las mediciones, y no solo las que caben en el grafico.

function borrar(){
  if(!confirm('Se borrarán las curvas de la pantalla.\n'+
              'El archivo CSV guardado NO se borra. ¿Continuar?')) return;
  fetch('/borrar'); datos=[]; dibujar();
}

window.addEventListener('resize',dibujar);
setInterval(actualizar,1000);
actualizar();
</script></body></html>
"""


class Manejador(BaseHTTPRequestHandler):

    def log_message(self, *args):
        pass                                   # no ensuciar la consola

    def do_GET(self):
        if self.path == "/" or self.path.startswith("/index"):
            cuerpo = PAGINA.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(cuerpo)))
            self.end_headers()
            self.wfile.write(cuerpo)

        elif self.path.startswith("/datos.json"):
            with candado:
                cuerpo = json.dumps({"datos": datos, "estado": estado}).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(cuerpo)))
            self.end_headers()
            self.wfile.write(cuerpo)

        elif self.path.startswith("/datos.csv"):
            # Entrega el archivo tal como esta guardado en el disco.
            try:
                with candado:
                    if archivo_csv is not None:
                        archivo_csv.flush()
                    with open(ruta_csv, "rb") as f:
                        cuerpo = f.read()
                nombre = os.path.basename(ruta_csv)
            except Exception as err:
                cuerpo = ("No se pudo leer el archivo: %s" % err).encode("utf-8")
                nombre = "error.txt"

            self.send_response(200)
            self.send_header("Content-Type", "text/csv; charset=utf-8")
            self.send_header("Content-Disposition",
                             'attachment; filename="%s"' % nombre)
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(cuerpo)))
            self.end_headers()
            self.wfile.write(cuerpo)

        elif self.path.startswith("/borrar"):
            with candado:
                datos.clear()
            self.send_response(204)
            self.end_headers()

        else:
            self.send_response(404)
            self.end_headers()


# ------------------------------------------------------------------ inicio
if __name__ == "__main__":
    print("=" * 62)
    print("   MONITOR LOCAL — Hogar Inteligente (Eureka 2026)")
    print("=" * 62)
    print("   Abre en el navegador:   http://localhost:%d" % PUERTO_HTTP)
    print("   Para detenerlo:         Ctrl + C")

    try:
        ruta = abrir_csv()
        print("   Guardando los datos en: %s" % os.path.abspath(ruta))
    except Exception as e:
        print("   !!! No se pudo crear el archivo CSV: %s" % e)
        print("   !!! Revisa que tengas permiso de escritura en esta carpeta.")
        sys.exit(1)

    print("=" * 62)

    hilo = threading.Thread(target=hilo_serie, daemon=True)
    hilo.start()

    servidor = HTTPServer(("127.0.0.1", PUERTO_HTTP), Manejador)
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        print("\n   Cerrando...")
    finally:
        servidor.server_close()
        if archivo_csv is not None:
            archivo_csv.flush()
            archivo_csv.close()
        print("   Se guardaron %d mediciones en:" % estado["guardadas"])
        print("   %s\n" % os.path.abspath(ruta_csv))
