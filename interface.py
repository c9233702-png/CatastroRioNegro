# -*- coding: utf-8 -*-
import urllib.parse  
from qgis.PyQt.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QFileDialog, QTextEdit, QProgressBar
from qgis.PyQt.QtCore import QCoreApplication, Qt
from qgis.core import QgsSettings, QgsProject, QgsRasterLayer, QgsCoordinateReferenceSystem
from .core_procesamiento import ProcesadorCatastral
from .optimizaciones_externas import OptimizadorExterno 

class CatastroInterface(QDialog):
    def __init__(self, iface, parent=None):
        super(CatastroInterface, self).__init__(parent or iface.mainWindow())
        self.iface = iface
        self.setWindowTitle("Catastro Río Negro - Segmentación de Baldíos")
        self.resize(600, 500)  
        
        self.settings = QgsSettings()
        layout = QVBoxLayout()
        
        layout.addWidget(QLabel("<b>Archivo CSV de Valuaciones:</b>"))
        h_box1 = QHBoxLayout()
        self.txt_valuaciones = QLineEdit()
        self.btn_valuaciones = QPushButton("Buscar...")
        self.btn_valuaciones.clicked.connect(lambda: self.seleccionar_archivo(self.txt_valuaciones, "CSV (*.csv)", "path_val"))
        h_box1.addWidget(self.txt_valuaciones)
        h_box1.addWidget(self.btn_valuaciones)
        layout.addLayout(h_box1)

        layout.addWidget(QLabel("<b>Archivo CSV de Parcelas VM1:</b>"))
        h_box2 = QHBoxLayout()
        self.txt_vm1 = QLineEdit()
        self.btn_vm1 = QPushButton("Buscar...")
        self.btn_vm1.clicked.connect(lambda: self.seleccionar_archivo(self.txt_vm1, "CSV (*.csv)", "path_vm1"))
        h_box2.addWidget(self.txt_vm1)
        h_box2.addWidget(self.btn_vm1)
        layout.addLayout(h_box2)

        layout.addWidget(QLabel("<b>Capa Shapefile PARCELARIO:</b>"))
        h_box3 = QHBoxLayout()
        self.txt_parcelario = QLineEdit()
        self.btn_parcelario = QPushButton("Buscar...")
        self.btn_parcelario.clicked.connect(lambda: self.seleccionar_archivo(self.txt_parcelario, "Shapefile (*.shp)", "path_par"))
        h_box3.addWidget(self.txt_parcelario)
        h_box3.addWidget(self.btn_parcelario)
        layout.addLayout(h_box3)

        layout.addWidget(QLabel("<b>Detalle del Resultado / Consola de Estado:</b>"))
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        layout.addWidget(self.log_output)

        layout.addWidget(QLabel("<b>Progreso del Proceso:</b>"))
        self.progreso = QProgressBar()
        self.progreso.setRange(0, 100)
        self.progreso.setValue(0)
        
        if hasattr(Qt, 'AlignmentFlag'):
            self.progreso.setAlignment(Qt.AlignmentFlag.AlignCenter)
        else:
            self.progreso.setAlignment(Qt.AlignCenter)
            
        layout.addWidget(self.progreso)

        self.btn_procesar = QPushButton("EJECUTAR PROCESAMIENTO CATASTRAL")
        self.btn_procesar.setStyleSheet("background-color: #2b5b84; color: white; font-weight: bold; font-size: 13px; padding: 8px;")
        self.btn_procesar.clicked.connect(self.ejecutar_proceso)
        layout.addWidget(self.btn_procesar)

        self.setLayout(layout)
        self.cargar_rutas_guardadas()

    def seleccionar_archivo(self, qline_edit, filtro, setting_key):
        carpeta_inicial = self.settings.value(f"CatastroRioNegro/{setting_key}", "")
        archivo, _ = QFileDialog.getOpenFileName(self, "Seleccionar archivo", carpeta_inicial, filtro)
        if archivo:
            qline_edit.setText(archivo)
            self.settings.setValue(f"CatastroRioNegro/{setting_key}", archivo)

    def cargar_rutas_guardadas(self):
        self.txt_valuaciones.setText(self.settings.value("CatastroRioNegro/path_val", ""))
        self.txt_vm1.setText(self.settings.value("CatastroRioNegro/path_vm1", ""))
        self.txt_parcelario.setText(self.settings.value("CatastroRioNegro/path_par", ""))

    def log(self, texto, tipo="INFO"):
        if tipo == "ERROR":
            self.log_output.append(f"<font color='red'><b>[ERROR]</b> {texto}</font>")
        elif tipo == "EXITO":
            self.log_output.append(f"<font color='green'><b>[ÉXITO ABSOLUTO]</b> {texto}</font>")
        elif tipo == "DEBUG":
            self.log_output.append(f"<font color='orange'><b>[DEBUG]</b> {texto}</font>")
        else:
            self.log_output.append(f"<b>[INFO]</b> {texto}")
        self.log_output.ensureCursorVisible()
        QCoreApplication.processEvents()

    def actualizar_progreso(self, valor):
        self.progreso.setValue(valor)
        QCoreApplication.processEvents()

    def ordenar_capas_de_dibujo_arriba(self):
        raiz = QgsProject.instance().layerTreeRoot()
        if not raiz: return
        nombres_prioritarios = ["GC_PLANTAP00", "GC_PLANTAP01"]
        for nombre in nombres_prioritarios:
            capas = QgsProject.instance().mapLayersByName(nombre)
            if capas and len(capas) > 0:
                capa = capas[0]
                nodo_existente = raiz.findLayer(capa.id())
                if nodo_existente:
                    clon = nodo_existente.clone()
                    raiz.insertChildNode(0, clon)
                    raiz.removeChildNode(nodo_existente)
        self.log("Capas de dibujo ordenadas de forma jerárquica (P01 arriba de P00).", "DEBUG")

    def ejecutar_proceso(self):
        self.log_output.clear()
        self.actualizar_progreso(0)
        
        path_val = self.txt_valuaciones.text()
        path_vm1 = self.txt_vm1.text()
        path_par = self.txt_parcelario.text()

        if not path_val or not path_vm1 or not path_par:
            self.log("Faltan ingresar rutas de archivos.", "ERROR")
            return

        self.btn_procesar.setEnabled(False)
        
        try:
            # Enlazamos con el backend y recibimos el CRS de la faja catastral detectada
            procesador = ProcesadorCatastral(self)
            crs_faja_oficial = procesador.ejecutar(path_val, path_vm1, path_par)
            
            # 🛠️ TU NUEVA DIRECCIÓN WEB DETECTADA Y VALIDADA INTEGRADA DIRECTAMENTE
            nombre_capa = "Google Satellite"
            url_base = "http://www.google.com/maps/vt?lyrs=s@189&gl=cn&x={x}&y={y}&z={z}"
            url_codificada = urllib.parse.quote(url_base)
            fuente_completa = f"type=xyz&zmin=0&zmax=20&url={url_codificada}"
            
            # Limpieza preventiva de intentos fallidos anteriores
            capas_viejas = QgsProject.instance().mapLayersByName(nombre_capa)
            for capa_vieja in capas_viejas:
                QgsProject.instance().removeMapLayer(capa_vieja.id())
            
            # Instanciamos la capa pasándole la fuente perfectamente codificada
            capa_satelital = QgsRasterLayer(fuente_completa, nombre_capa, "wms")
            
            if capa_satelital.isValid():
                # Insertar en el fondo absoluto del proyecto (índice -1)
                QgsProject.instance().addMapLayer(capa_satelital, False)
                raiz = QgsProject.instance().layerTreeRoot()
                if raiz:
                    raiz.insertLayer(-1, capa_satelital)
                    nodo = raiz.findLayer(capa_satelital.id())
                    if nodo:
                        nodo.setItemVisibilityChecked(True)
                
                # Forzar re-pintado de texturas ráster en segundo plano
                capa_satelital.triggerRepaint()
                self.log("Capa ráster Google Satellite cargada y posicionada en el fondo con éxito.", "DEBUG")
            else:
                self.log(f"Error técnico del proveedor: {capa_satelital.error().summary()}", "ERROR")
            
            # Imponemos el CRS de la faja oficial calculada al lienzo de QGIS
            if crs_faja_oficial and crs_faja_oficial.isValid():
                self.log(f"Fijando CRS oficial del lienzo a la faja detectada: {crs_faja_oficial.authid()}", "INFO")
                QgsProject.instance().setCrs(crs_faja_oficial)
            else:
                self.log("No se pudo validar el CRS de la faja catastral devuelta.", "ERROR")

            OptimizadorExterno.crear_capas_de_dibujo_vacias(self.iface, self)
            self.ordenar_capas_de_dibujo_arriba()
            
            # Forzar Zoom automático sobre las geometrías de los baldíos generados
            capas_baldios = QgsProject.instance().mapLayersByName("baldios")
            if capas_baldios and len(capas_baldios) > 0 and self.iface:
                self.iface.mapCanvas().setExtent(capas_baldios[0].extent())
            
            # Forzar el refresco gráfico adaptativo según versión de QGIS
            if self.iface and self.iface.mapCanvas():
                if hasattr(self.iface.mapCanvas(), 'refreshAllLayers'):
                    self.iface.mapCanvas().refreshAllLayers()
                else:
                    self.iface.mapCanvas().refresh()
            
            self.actualizar_progreso(100)
            self.log("Proceso finalizado correctamente con faja unificada.", "EXITO")
            
        except Exception as e:
            self.log(f"Error en la cadena secuencial: {str(e)}", "ERROR")
            self.actualizar_progreso(0)
            
        self.btn_procesar.setEnabled(True)
