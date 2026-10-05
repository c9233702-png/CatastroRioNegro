# -*- coding: utf-8 -*-
import processing
from datetime import datetime
from qgis.PyQt.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QTextEdit, QMessageBox
from qgis.PyQt.QtCore import QCoreApplication
from qgis.core import QgsProject, QgsSymbol, QgsSingleSymbolRenderer, Qgis, QgsWkbTypes

class CorrectorGeometriasDialog(QDialog):
    def __init__(self, iface, parent=None):
        super(CorrectorGeometriasDialog, self).__init__(parent or iface.mainWindow())
        self.iface = iface
        self.setWindowTitle("Parámetros de Ortogonalización y Limpieza")
        self.resize(550, 450)
        
        layout = QVBoxLayout()

        layout.addWidget(QLabel("<b>Tolerancia de Ángulo (Grados °):</b>"))
        self.txt_angulo = QLineEdit("20.0")
        layout.addWidget(self.txt_angulo)

        layout.addWidget(QLabel("<b>Tolerancia de Pegado / Snap (Metros):</b>"))
        self.txt_pegado = QLineEdit("0.5")
        layout.addWidget(self.txt_pegado)

        layout.addWidget(QLabel("<b>Detalle del Resultado / Consola de Estado:</b>"))
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setStyleSheet("background-color: #ffffff; color: #000000; font-family: 'Segoe UI', Arial, sans-serif; font-size: 12px;")
        layout.addWidget(self.log_output)

        self.btn_lanzar = QPushButton("PROCESAR Y REFINAR EDIFICACIONES")
        self.btn_lanzar.setStyleSheet("background-color: #27ae60; color: white; font-weight: bold; padding: 8px; font-size: 12px;")
        self.btn_lanzar.clicked.connect(self.disparar_proceso)
        layout.addWidget(self.btn_lanzar)

        self.setLayout(layout)

    def log(self, texto, tipo="INFO"):
        if tipo == "ERROR":
            self.log_output.append(f"<b>[ERROR]</b> <font color='red'>{texto}</font>")
        elif tipo == "EXITO":
            self.log_output.append(f"<b><font color='green'>[ÉXITO ABSOLUTO]</font></b> <font color='green'>{texto}</font>")
        elif tipo == "DEBUG":
            self.log_output.append(f"<b><font color='orange'>[DEBUG]</font></b> {texto}")
        else:
            self.log_output.append(f"<b>[INFO]</b> {texto}")
        QCoreApplication.processEvents()

    def disparar_proceso(self):
        try:
            angulo = float(self.txt_angulo.text())
            pegado = float(self.txt_pegado.text())
        except ValueError:
            QMessageBox.critical(self, "Error de Datos", "Por favor, ingrese valores numéricos válidos.")
            return

        self.btn_lanzar.setEnabled(False)
        self.log_output.clear()
        
        procesadas = 0
        for nombre_capa in ["GC_PLANTAP00", "GC_PLANTAP01"]:
            exito = self.ejecutar_algoritmo_capa(nombre_capa, angulo, pegado)
            if exito:
                procesadas += 1

        if procesadas > 0:
            self.log("Proceso de refinamiento finalizado correctamente.", "EXITO")
            
            # 🧠 DETECCIÓN HÍBRIDA DEL ENUMERADOR DE MENSAJE (QGIS 3 / QGIS 4)
            if hasattr(Qgis, 'MessageLevel'):
                nivel_msg = Qgis.MessageLevel.Success
            else:
                nivel_msg = Qgis.Success # Sintaxis compatible con QGIS 3.x
                
            if self.iface:
                self.iface.messageBar().pushMessage("Catastro RN", "Refinamiento geométrico finalizado.", nivel_msg, 4)
        else:
            self.log("No se pudo procesar ninguna capa. Verifique que tengan polígonos dibujados.", "ERROR")
        
        self.btn_lanzar.setEnabled(True)

    def ejecutar_algoritmo_capa(self, nombre_capa, tolerancia_angulo, tolerancia_pegado):
        lista_capas = QgsProject.instance().mapLayersByName(nombre_capa)
        if not lista_capas or len(lista_capas) == 0:
            self.log(f"Capa '{nombre_capa}' no encontrada en el panel lateral. Saltando...")
            return False

        capa_origen = lista_capas[0]
        
        if capa_origen.featureCount() == 0:
            self.log(f"La capa '{nombre_capa}' está vacía (0 objetos). Saltando...")
            return False
        
        self.log(f"Iniciando secuencia de limpieza y ortogonalización para '{nombre_capa}'...")
        
        try:
            # 1. Corregir Geometrías Inválidas iniciales
            self.log(f"[{nombre_capa}] Paso 1/4: Reparando topología geométrica inicial...")
            paso1 = processing.run("native:fixgeometries", {'INPUT': capa_origen, 'OUTPUT': 'memory:'})

            # 2. Ortogonalizar
            self.log(f"[{nombre_capa}] Paso 2/4: Forzando ángulos rectos (Ortogonalizar)...")
            paso2 = processing.run("native:orthogonalize", {
                'INPUT': paso1['OUTPUT'],
                'ANGLE': tolerancia_angulo,
                'MAX_ITERATIONS': 1000,
                'OUTPUT': 'memory:'
            })

            # 2b. Reparar geometrías inválidas generadas por la ortogonalización
            self.log(f"[{nombre_capa}] Paso 2b: Purgando quiebres inválidos post-ortogonalización...")
            paso2_reparado = processing.run("native:fixgeometries", {'INPUT': paso2['OUTPUT'], 'OUTPUT': 'memory:'})

            # 3. Snap masivo
            self.log(f"[{nombre_capa}] Paso 3/4: Ensamblando muros contiguos y linderos vecinos...")
            paso3 = processing.run("native:snapgeometries", {
                'INPUT': paso2_reparado['OUTPUT'],
                'REFERENCE_LAYER': paso2_reparado['OUTPUT'],
                'TOLERANCE': tolerancia_pegado,
                'BEHAVIOR': 3,
                'OUTPUT': 'memory:'
            })

            # 4. Limpieza final de geometrías
            self.log(f"[{nombre_capa}] Paso 4/4: Ejecutando validación topológica final...")
            paso_final = processing.run("native:fixgeometries", {'INPUT': paso3['OUTPUT'], 'OUTPUT': 'memory:'})

            capa_resultado = paso_final['OUTPUT']
            
            # Heredamos de forma nativa el CRS POSGAR unificado que ya tiene seteado el proyecto
            capa_resultado.setCrs(QgsProject.instance().crs())

            nombre_final = f"{nombre_capa}_Corregido_Ortogonal"
            capa_resultado.setName(nombre_final)
            
            # 🧠 INYECCIÓN HÍBRIDA PRECISA: Asignación de tipo geométrico primitivo para defaultSymbol
            if hasattr(Qgis, 'GeometryType'):
                geom_tipo_simbolo = Qgis.GeometryType.Polygon # QGIS 4.x
            else:
                geom_tipo_simbolo = QgsWkbTypes.PolygonGeometry # QGIS 3.x
            
            # Aplicamos renderizador simple estándar por default de QGIS
            simbolo_default = QgsSymbol.defaultSymbol(geom_tipo_simbolo)
            renderizador_default = QgsSingleSymbolRenderer(simbolo_default)
            capa_resultado.setRenderer(renderizador_default)
            
            QgsProject.instance().addMapLayer(capa_resultado)
            self.log(f"Capa '{nombre_final}' inyectada en metros de Faja con éxito!", "EXITO")
            return True

        except Exception as e:
            self.log(f"Fallo en el algoritmo de corrección para {nombre_capa}: {str(e)}", "ERROR")
            return False
