# -*- coding: utf-8 -*-
import sys
import importlib
from qgis.PyQt.QtWidgets import QAction, QMessageBox, QMenu
from qgis.PyQt.QtGui import QIcon, QPixmap, QPainter, QColor, QFont, QPolygonF  
from qgis.PyQt.QtCore import Qt, QRectF, QPointF  
from qgis.core import QgsProject

MODULOS_A_RECARGAR = [
    'CatastroRioNegro.interface',
    'CatastroRioNegro.core_procesamiento',
    'CatastroRioNegro.optimizaciones_externas',
    'CatastroRioNegro.corrector_geometrias',
    'CatastroRioNegro.core_exportacion',      
    'CatastroRioNegro.exportador_dxf',
    'CatastroRioNegro.panel_estadisticas'   
]

class CatastroRioNegroPlugin:
    def __init__(self, iface):
        self.iface = iface
        self.action_interfaz = None
        self.action_corrector = None
        self.action_exportador = None  
        self.action_panel_est = None        
        self.submenu_catastro = None  
        self.dlg = None
        self.dlg_corrector = None
        self.dlg_exportador = None  
        self.dock_estadisticas = None       

    def unload(self):
        """Remueve de forma segura todos los elementos gráficos de QGIS"""
        if self.action_interfaz: self.iface.removeToolBarIcon(self.action_interfaz)
        if self.action_panel_est: self.iface.removeToolBarIcon(self.action_panel_est)
        if self.action_corrector: self.iface.removeToolBarIcon(self.action_corrector)
        if self.action_exportador: self.iface.removeToolBarIcon(self.action_exportador)
            
        if self.submenu_catastro:
            menu_complementos = self.iface.pluginMenu()
            menu_complementos.removeAction(self.submenu_catastro.menuAction())
            
        if self.dock_estadisticas:
            self.iface.removeDockWidget(self.dock_estadisticas)
            self.dock_estadisticas.deleteLater()

    def run_interfaz(self):
        self.recargar_modulos()
        from .interface import CatastroInterface
        if self.dlg: self.dlg.deleteLater()
        self.dlg = CatastroInterface(self.iface)
        self.dlg.show()

    def run_corrector_directo(self):
        self.recargar_modulos()
        lista_p00 = QgsProject.instance().mapLayersByName("GC_PLANTAP00")
        lista_p01 = QgsProject.instance().mapLayersByName("GC_PLANTAP01")
        if not lista_p00 and not lista_p01:
            QMessageBox.warning(self.iface.mainWindow(), "Catastro RN", "No se encontraron las capas de plantas en el proyecto. Corre el proceso base primero.")
            return
        from .corrector_geometrias import CorrectorGeometriasDialog
        if self.dlg_corrector: self.dlg_corrector.deleteLater()
        self.dlg_corrector = CorrectorGeometriasDialog(self.iface)
        self.dlg_corrector.show()

    def run_corrector_directo(self):
        self.recargar_modulos()
        lista_p00 = QgsProject.instance().mapLayersByName("GC_PLANTAP00")
        lista_p01 = QgsProject.instance().mapLayersByName("GC_PLANTAP01")
        if not lista_p00 and not lista_p01:
            QMessageBox.warning(self.iface.mainWindow(), "Catastro RN", "No se encontraron las capas de plantas en el proyecto. Corre el proceso base primero.")
            return
        from .corrector_geometrias import CorrectorGeometriasDialog
        if self.dlg_corrector: self.dlg_corrector.deleteLater()
        self.dlg_corrector = CorrectorGeometriasDialog(self.iface)
        self.dlg_corrector.show()

    def run_exportador(self):
        self.recargar_modulos()
        from .exportador_dxf import ExportadorDxfDialog
        if self.dlg_exportador: self.dlg_exportador.deleteLater()
        self.dlg_exportador = ExportadorDxfDialog(self.iface)
        self.dlg_exportador.show()

    def conmutar_panel_estadisticas(self):
        """🚀 SOPORTE DUAL UNIFICADO: Abre, posiciona y conmuta el dock en QGIS 3 y QGIS 4"""
        self.recargar_modulos()
        
        # Interceptamos el área de acoplamiento según la API de Qt activa
        if hasattr(Qt, 'DockWidgetArea'):
            AREA_DERECHA = Qt.DockWidgetArea.RightDockWidgetArea
        else:
            AREA_DERECHA = Qt.RightDockWidgetArea

        if not self.dock_estadisticas:
            from .panel_estadisticas import PanelEstadisticasCatastral
            self.dock_estadisticas = PanelEstadisticasCatastral(self.iface)
            
            self.iface.addDockWidget(AREA_DERECHA, self.dock_estadisticas)
            self.dock_estadisticas.visibilityChanged.connect(self.sincronizar_estado_boton_check)
            
            self.dock_estadisticas.setFloating(True)
            
            ventana_principal = self.iface.mainWindow()
            geometria_qgis = ventana_principal.geometry()
            
            x_flotante = geometria_qgis.right() - 420
            y_flotante = geometria_qgis.top() + 140
            
            try:
                if self.dock_estadisticas.window():
                    self.dock_estadisticas.window().move(x_flotante, y_flotante)
                else:
                    self.dock_estadisticas.move(x_flotante, y_flotante)
            except:
                try:
                    self.dock_estadisticas.move(x_flotante, y_flotante)
                except:
                    pass
        else:
            # Control dinámico de encendido/ocultado al pulsar el botón repetidas veces
            if self.dock_estadisticas.isVisible():
                self.dock_estadisticas.hide()
            else:
                self.dock_estadisticas.show()
                if hasattr(self.dock_estadisticas, "conectar_disparadores_individuales"):
                    self.dock_estadisticas.conectar_disparadores_individuales()

        visibilidad = self.action_panel_est.isChecked()
        self.dock_estadisticas.setVisible(visibilidad)
        if visibilidad:
            self.dock_estadisticas.conectar_disparadores_individuales()

    def sincronizar_estado_boton_check(self, visible):
        if self.action_panel_est:
            self.action_panel_est.setChecked(visible)

    def recargar_modulos(self):
        for mod_nombre in MODULOS_A_RECARGAR:
            if mod_nombre in sys.modules:
                try: importlib.reload(sys.modules[mod_nombre])
                except: pass

    def crear_icono_principal_rn(self):
        pixmap = QPixmap(32, 32)
        pixmap.fill(QColor(0, 0, 0, 0)) 
        painter = QPainter(pixmap)
        if hasattr(QPainter, 'Antialiasing'): painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(QColor("#66cc47"))  
        painter.setPen(QColor("#54b337"))    
        painter.drawRoundedRect(2, 2, 28, 28, 4, 4)
        font = QFont("Segoe UI", 12, QFont.Weight.Bold if hasattr(QFont, 'Weight') else QFont.Bold) 
        painter.setFont(font)
        painter.setPen(QColor("white"))    
        flag_centro = Qt.AlignmentFlag.AlignCenter if hasattr(Qt, 'AlignmentFlag') else Qt.AlignCenter
        painter.drawText(QRectF(2, 2, 28, 28), flag_centro, "RN")
        painter.end()
        return QIcon(pixmap)

    def crear_icono_mejoras(self):
        pixmap = QPixmap(32, 32)
        pixmap.fill(QColor(0, 0, 0, 0)) 
        painter = QPainter(pixmap)
        if hasattr(QPainter, 'Antialiasing'): painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(QColor("#66cc47"))  
        painter.setPen(QColor("#54b337"))    
        painter.drawRoundedRect(2, 2, 28, 28, 4, 4)
        painter.setBrush(QColor("white"))
        painter.setPen(QColor("white"))
        painter.drawRect(6, 14, 12, 11)
        puntos_techo = QPolygonF([QPointF(12, 7), QPointF(4, 14), QPointF(20, 14)])
        painter.drawPolygon(puntos_techo)
        painter.setBrush(QColor(0, 0, 0, 0))
        pen_lupa = painter.pen()
        pen_lupa.setWidth(2)
        painter.setPen(pen_lupa)
        painter.drawEllipse(17, 15, 8, 8)  
        painter.drawLine(24, 22, 28, 26)
        painter.end()
        return QIcon(pixmap)

    def crear_icono_estadisticas_barras(self):
        pixmap = QPixmap(32, 32)
        pixmap.fill(QColor(0, 0, 0, 0))
        painter = QPainter(pixmap)
        if hasattr(QPainter, 'Antialiasing'): painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(QColor("#66cc47"))
        painter.setPen(QColor("#54b337"))
        painter.drawRoundedRect(2, 2, 28, 28, 4, 4)
        painter.setBrush(QColor("white"))
        if hasattr(Qt, 'PenStyle'):
            painter.setPen(Qt.PenStyle.NoPen)
        else:
            painter.setPen(Qt.NoPen)
        painter.drawRect(8, 17, 4, 9)   
        painter.drawRect(14, 12, 4, 14) 
        painter.drawRect(20, 7, 4, 19)  
        painter.end()
        return QIcon(pixmap)

    def crear_icono_ortogonalizar(self):
        pixmap = QPixmap(32, 32)
        pixmap.fill(QColor(0, 0, 0, 0)) 
        painter = QPainter(pixmap)
        if hasattr(QPainter, 'Antialiasing'): painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(QColor("#66cc47"))  
        painter.setPen(QColor("#54b337"))    
        painter.drawRoundedRect(2, 2, 28, 28, 4, 4)
        painter.setBrush(QColor(255, 255, 255, 140))  
        painter.setPen(QColor(255, 255, 255, 180))
        painter.drawRect(6, 12, 10, 10)
        painter.save() 
        painter.translate(21, 17) 
        painter.rotate(45)        
        painter.setBrush(QColor("white"))  
        painter.setPen(QColor("#4b9e33")) 
        painter.drawRect(-5, -5, 10, 10)
        painter.restore() 
        painter.end()
        return QIcon(pixmap)

    def crear_icono_exportar(self):
        pixmap = QPixmap(32, 32)
        pixmap.fill(QColor(0, 0, 0, 0))
        painter = QPainter(pixmap)
        if hasattr(QPainter, 'Antialiasing'): painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(QColor("#66cc47"))
        painter.setPen(QColor("#54b337"))
        painter.drawRoundedRect(2, 2, 28, 28, 4, 4)
        painter.setBrush(QColor(0, 0, 0, 0))
        painter.setPen(QColor("white"))
        pen_caja = painter.pen()
        pen_caja.setWidth(2)
        painter.setPen(pen_caja)
        painter.drawLine(6, 20, 6, 25)
        painter.drawLine(6, 25, 26, 25)
        painter.drawLine(26, 25, 26, 20)
        painter.setBrush(QColor("white"))
        painter.drawLine(16, 22, 16, 8)
        puntos_flecha = QPolygonF([QPointF(11, 13), QPointF(16, 7), QPointF(21, 13)])
        painter.drawPolygon(puntos_flecha)
        painter.end()
        return QIcon(pixmap)

    def initGui(self):
        icono_menu_padre = self.crear_icono_principal_rn()
        icono_base = self.crear_icono_mejoras()
        icono_reparar = self.crear_icono_ortogonalizar()
        icono_dxf = self.crear_icono_exportar()
        icono_analitica = self.crear_icono_estadisticas_barras()

        self.action_interfaz = QAction(icono_base, "Detección de Mejoras y Baldíos", self.iface.mainWindow())
        self.action_interfaz.setStatusTip("Ejecutar procesamiento catastral de parcelas")
        self.action_interfaz.triggered.connect(self.run_interfaz)
        
        self.action_panel_est = QAction(icono_analitica, "Estadísticas de Carga", self.iface.mainWindow())
        self.action_panel_est.setStatusTip("Encender/Apagar el monitor de control de superficies en tiempo real")
        self.action_panel_est.setCheckable(True)
        self.action_panel_est.triggered.connect(self.conmutar_panel_estadisticas)

        self.action_corrector = QAction(icono_reparar, "Corregir y Ortogonalizar Geometría", self.iface.mainWindow())
        self.action_corrector.setStatusTip("Ortogonalizar muros contiguos y linderos")
        self.action_corrector.triggered.connect(self.run_corrector_directo)

        self.action_exportador = QAction(icono_dxf, "Exportación Masiva a CAD y Reportes", self.iface.mainWindow())
        self.action_exportador.setStatusTip("Abrir el panel masivo de conversión DXF y auditorías")
        self.action_exportador.triggered.connect(self.run_exportador)

        menu_complementos = self.iface.pluginMenu()
        self.submenu_catastro = QMenu("Catastro Río Negro", menu_complementos)
        self.submenu_catastro.setIcon(icono_menu_padre) 
        
        self.submenu_catastro.addAction(self.action_interfaz)
        self.submenu_catastro.addAction(self.action_panel_est) 
        self.submenu_catastro.addAction(self.action_corrector)
        self.submenu_catastro.addSeparator()
        self.submenu_catastro.addAction(self.action_exportador)
        
        menu_complementos.addMenu(self.submenu_catastro)

        self.iface.addToolBarIcon(self.action_interfaz)
        self.iface.addToolBarIcon(self.action_panel_est) 
        self.iface.addToolBarIcon(self.action_corrector)
        self.iface.addToolBarIcon(self.action_exportador)

