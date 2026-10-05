# -*- coding: utf-8 -*-
import os
import traceback
from qgis.PyQt.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton, 
                                 QTextEdit, QLabel, QProgressBar, QLineEdit, QFileDialog)
from qgis.PyQt.QtGui import QColor, QFont
from qgis.PyQt.QtCore import Qt, QCoreApplication

from .core_exportacion import MotorExportacionDxf

class ExportadorDxfDialog(QDialog):
    def __init__(self, iface, parent=None):
        super().__init__(parent or iface.mainWindow())
        self.iface = iface
        self.init_ui()

    def init_ui(self):
        """Inicializa la interfaz gráfica del plugin catastral"""
        self.setWindowTitle("Exportación Masiva y Reportes - Catastro RN")
        self.resize(580, 520)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)
        
        layout.addWidget(QLabel("<b>Carpeta de Destino para DXF y Reportes:</b>"))
        contenedor_ruta = QHBoxLayout()
        
        self.txt_ruta_destino = QLineEdit(self)
        self.txt_ruta_destino.setReadOnly(True)
        self.txt_ruta_destino.setStyleSheet("background-color: #f8f9fa; color: #333300; border: 1px solid #bdc3c7; padding: 4px;")
        
        escritorio_usuario = os.path.join(os.path.expanduser("~"), "Desktop")
        ruta_defecto = os.path.normpath(os.path.join(escritorio_usuario, "Exportacion_Catastral"))
        self.txt_ruta_destino.setText(ruta_defecto)
        contenedor_ruta.addWidget(self.txt_ruta_destino)
        
        self.btn_buscar_carpeta = QPushButton("Buscar...", self)
        self.btn_buscar_carpeta.setStyleSheet("padding: 4px 12px; font-weight: bold;")
        self.btn_buscar_carpeta.clicked.connect(self.seleccionar_carpeta_destino)
        contenedor_ruta.addWidget(self.btn_buscar_carpeta)
        layout.addLayout(contenedor_ruta)
        
        layout.addWidget(QLabel("<b>Detalle del Resultado / Consola de Estado:</b>"))
        self.log_viewer = QTextEdit(self)
        self.log_viewer.setReadOnly(True)
        self.log_viewer.setStyleSheet("background-color: #ffffff; color: #000000; font-family: 'Segoe UI', Arial, sans-serif; font-size: 12px; border: 1px solid #bdc3c7;")
        layout.addWidget(self.log_viewer)
        
        layout.addWidget(QLabel("<b>Progreso del Proceso:</b>"))
        self.barra_progreso = QProgressBar(self)
        self.barra_progreso.setValue(0)
        
        # 🧠 FIXED: Adaptación de la propiedad de Alineación Universal PyQt5/PyQt6
        if hasattr(Qt, 'AlignmentFlag'):
            self.barra_progreso.setAlignment(Qt.AlignmentFlag.AlignCenter)
        else:
            self.barra_progreso.setAlignment(Qt.AlignCenter)
            
        self.barra_progreso.setStyleSheet("""
            QProgressBar { border: 1px solid #bdc3c7; border-radius: 2px; text-align: center; background-color: #f8f9fa; }
            QProgressBar::chunk { background-color: #66cc47; width: 20px; }
        """)
        layout.addWidget(self.barra_progreso)
        
        self.btn_exportar = QPushButton("INICIAR EXPORTACIÓN DXF Y REPORTES", self)
        self.btn_exportar.setStyleSheet(
            "background-color: #66cc47; color: white; font-weight: bold; padding: 10px; border-radius: 4px; font-size: 12px;"
        )
        self.btn_exportar.clicked.connect(self.ejecutar_exportacion)
        layout.addWidget(self.btn_exportar)
        
        self.log("Listo para iniciar. Arquitectura desacoplada por módulos cargada con éxito.")

    def seleccionar_carpeta_destino(self):
        ruta_inicial = self.txt_ruta_destino.text()
        if not os.path.exists(ruta_inicial):
            ruta_inicial = os.path.expanduser("~")
        carpeta_seleccionada = QFileDialog.getExistingDirectory(
            self, "Seleccionar Carpeta de Destino", ruta_inicial, QFileDialog.Option.ShowDirsOnly
        )
        if carpeta_seleccionada:
            self.txt_ruta_destino.setText(os.path.normpath(carpeta_seleccionada))

    def log(self, texto, tipo="INFO"):
        if tipo == "ERROR":
            self.log_viewer.append(f"<b>[ERROR]</b> <font color='red'>{texto}</font>")
        elif tipo == "EXITO":
            self.log_viewer.append(f"<b>[ÉXITO]</b> <font color='green'>{texto}</font>")
        else:
            self.log_viewer.append(f"<b>[INFO]</b> {texto}")
        self.log_viewer.ensureCursorVisible()
        QCoreApplication.processEvents()

    def actualizar_progreso(self, valor):
        self.barra_progreso.setValue(int(valor))
        QCoreApplication.processEvents()

    def ejecutar_exportacion(self):
        self.btn_exportar.setEnabled(False)
        self.btn_buscar_carpeta.setEnabled(False)
        self.log_viewer.clear()
        self.actualizar_progreso(0)
        
        try:
            motor = MotorExportacionDxf(
                iface=self.iface,
                ruta_destino=self.txt_ruta_destino.text(),
                fn_log=self.log,
                fn_progreso=self.actualizar_progreso
            )
            motor.ejecutar()
            self.log("🚀 ¡Todo el proceso masivo ha finalizado con éxito absoluto!", "EXITO")
            
        except Exception as e:
            self.log(f"❌ Fallo crítico en el motor de exportación: {str(e)}", "ERROR")
            self.log(traceback.format_exc(), "INFO")
            
        self.btn_exportar.setEnabled(True)
        self.btn_buscar_carpeta.setEnabled(True)
