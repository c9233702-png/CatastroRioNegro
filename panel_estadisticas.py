# -*- coding: utf-8 -*-
from qgis.PyQt.QtWidgets import QDockWidget, QWidget, QVBoxLayout, QGridLayout, QLabel, QFrame
from qgis.PyQt.QtGui import QIcon, QPixmap, QPainter, QColor, QFont
from qgis.PyQt.QtCore import Qt, QRectF
from qgis.core import QgsProject

class PanelEstadisticasCatastral(QDockWidget):
    def __init__(self, iface, parent=None):
        super(PanelEstadisticasCatastral, self).__init__(parent)
        self.iface = iface
        self.setWindowTitle("RN - Monitoreo de Carga")
        
        # 🚀 1. COMPATIBILIDAD DUAL DE ÁREAS DE ACOPLAMIENTO (PyQt5 / PyQt6)
        if hasattr(Qt, 'DockWidgetArea'):
            self.setAllowedAreas(Qt.DockWidgetArea.LeftDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea)
        else:
            self.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        
        # 🚀 2. COMPATIBILIDAD DUAL DE PROPIEDADES ENUM DE QFRAME Y ALINEACIONES
        if hasattr(QFrame, 'Shape'):
            ESTILO_PANEL = QFrame.Shape.StyledPanel
            LINEA_HORIZONTAL = QFrame.Shape.HLine
            SOMBRA_HUNDIDA = QFrame.Shadow.Sunken
        else:
            ESTILO_PANEL = QFrame.StyledPanel
            LINEA_HORIZONTAL = QFrame.HLine
            SOMBRA_HUNDIDA = QFrame.Sunken
            
        # Mapeo seguro para la alineación del texto en las celdas del Grid
        ALI_DERECHA = Qt.AlignmentFlag.AlignRight if hasattr(Qt, 'AlignmentFlag') else Qt.AlignRight
            
        self.setWindowIcon(self.crear_icono_estadisticas_e())

        self.setMinimumSize(380, 350)
        self.resize(380, 350)
        self.setFloating(True)

        self.widget_contenedor = QWidget()
        self.widget_contenedor.setMinimumSize(360, 330)
        self.widget_contenedor.setMaximumSize(380, 360)
        
        layout_principal = QVBoxLayout(self.widget_contenedor)
        layout_principal.setContentsMargins(10, 10, 10, 10)
        layout_principal.setSpacing(10)

        lbl_seccion_part = QLabel("<b>📊 ESTADO DE PARCELAS</b>")
        lbl_seccion_part.setStyleSheet("color: #2b5b84; font-size: 11px;")
        layout_principal.addWidget(lbl_seccion_part)

        marco_parcelas = QFrame()
        marco_parcelas.setFrameShape(ESTILO_PANEL)
        marco_parcelas.setStyleSheet("background-color: #f8f9fa; border-radius: 4px; padding: 4px;")
        grid_parcelas = QGridLayout(marco_parcelas)
        grid_parcelas.setContentsMargins(6, 6, 6, 6)

        grid_parcelas.addWidget(QLabel("🟢 Cargadas (Con Edif.):"), 0, 0)
        self.lbl_cargadas = QLabel("0")
        self.lbl_cargadas.setStyleSheet("font-weight: bold; color: green;")
        grid_parcelas.addWidget(self.lbl_cargadas, 0, 1, ALI_DERECHA)

        grid_parcelas.addWidget(QLabel("🔴 Sin Cargar (Baldíos):"), 1, 0)
        self.lbl_sin_cargar = QLabel("0")
        self.lbl_sin_cargar.setStyleSheet("font-weight: bold; color: crimson;")
        grid_parcelas.addWidget(self.lbl_sin_cargar, 1, 1, ALI_DERECHA)

        layout_principal.addWidget(marco_parcelas)

        lbl_seccion_sup = QLabel("<b>📐 METROS CUADRADOS (m²)</b>")
        lbl_seccion_sup.setStyleSheet("color: #2b5b84; font-size: 11px;")
        layout_principal.addWidget(lbl_seccion_sup)

        marco_superficies = QFrame()
        marco_superficies.setFrameShape(ESTILO_PANEL)
        marco_superficies.setStyleSheet("background-color: #f1f3f5; border-radius: 4px; padding: 4px;")
        grid_sups = QGridLayout(marco_superficies)
        grid_sups.setContentsMargins(6, 6, 6, 6)

        grid_sups.addWidget(QLabel("🏢 Cubierta:"), 0, 0)
        self.lbl_val_cub = QLabel("0.00 m²")
        self.lbl_val_cub.setStyleSheet("font-weight: bold;")
        grid_sups.addWidget(self.lbl_val_cub, 0, 1, ALI_DERECHA)

        grid_sups.addWidget(QLabel("📐 Semicubierta:"), 1, 0)
        self.lbl_val_semi = QLabel("0.00 m²")
        self.lbl_val_semi.setStyleSheet("font-weight: bold;")
        grid_sups.addWidget(self.lbl_val_semi, 1, 1, ALI_DERECHA)

        grid_sups.addWidget(QLabel("🏊 Pileta:"), 2, 0)
        self.lbl_val_pil = QLabel("0.00 m²")
        self.lbl_val_pil.setStyleSheet("font-weight: bold;")
        grid_sups.addWidget(self.lbl_val_pil, 2, 1, ALI_DERECHA)

        linea = QFrame()
        linea.setFrameShape(LINEA_HORIZONTAL)
        linea.setFrameShadow(SOMBRA_HUNDIDA)
        grid_sups.addWidget(linea, 3, 0, 1, 2)

        lbl_total_txt = QLabel("🟨 <b>TOTAL GENERAL:</b>")
        grid_sups.addWidget(lbl_total_txt, 4, 0)
        self.lbl_val_total = QLabel("0.00 m²")
        self.lbl_val_total.setStyleSheet("font-weight: bold; color: #2b5b84; font-size: 12px;")
        grid_sups.addWidget(self.lbl_val_total, 4, 1, ALI_DERECHA)

        layout_principal.addWidget(marco_superficies)
        layout_principal.addStretch()

        self.setWidget(self.widget_contenedor)
        self.conectar_senales_capas()

    def crear_icono_estadisticas_e(self):
        pixmap = QPixmap(32, 32)
        pixmap.fill(QColor(0, 0, 0, 0))
        painter = QPainter(pixmap)
        
        if hasattr(QPainter, 'RenderHint') and hasattr(QPainter.RenderHint, 'Antialiasing'):
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        elif hasattr(QPainter, 'Antialiasing'):
            painter.setRenderHint(QPainter.Antialiasing)
            
        painter.setBrush(QColor("#66cc47"))
        painter.setPen(QColor("#54b337"))
        painter.drawRoundedRect(2, 2, 28, 28, 4, 4)
        painter.setBrush(QColor("white"))
        
        if hasattr(Qt, 'PenStyle') and hasattr(Qt.PenStyle, 'NoPen'):
            painter.setPen(Qt.PenStyle.NoPen)
        elif hasattr(Qt, 'NoPen'):
            painter.setPen(Qt.NoPen)
        else:
            painter.setPen(Qt.PenStyle.NoPen)
            
        painter.drawRect(8, 17, 4, 9)   
        painter.drawRect(14, 12, 4, 14) 
        painter.drawRect(20, 7, 4, 19)  
        painter.end()
        return QIcon(pixmap)

    def conectar_senales_capas(self):
        instancia = QgsProject.instance()
        instancia.layersAdded.connect(self.conectar_disparadores_individuales)
        self.conectar_disparadores_individuales()

    def conectar_disparadores_individuales(self, *args):
        nombres_observados = ["GC_PLANTAP00", "GC_PLANTAP01", "baldios"]
        for nombre in nombres_observados:
            capas = QgsProject.instance().mapLayersByName(nombre)
            if capas and len(capas) > 0:
                capa = capas[0]
                try: capa.geometryChanged.disconnect(self.recalcular_metricas_tiempo_real)
                except: pass
                try: capa.attributeValueChanged.disconnect(self.recalcular_metricas_tiempo_real)
                except: pass
                try: capa.featureAdded.disconnect(self.recalcular_metricas_tiempo_real)
                except: pass
                try: capa.featureDeleted.disconnect(self.recalcular_metricas_tiempo_real)
                except: pass
                try: capa.editCommandEnded.disconnect(self.recalcular_metricas_tiempo_real)
                except: pass
                if capa.dataProvider():
                    try: capa.dataProvider().dataChanged.disconnect(self.recalcular_metricas_tiempo_real)
                    except: pass
                capa.geometryChanged.connect(self.recalcular_metricas_tiempo_real)
                capa.attributeValueChanged.connect(self.recalcular_metricas_tiempo_real)
                capa.featureAdded.connect(self.recalcular_metricas_tiempo_real)
                capa.featureDeleted.connect(self.recalcular_metricas_tiempo_real)
                capa.editCommandEnded.connect(self.recalcular_metricas_tiempo_real)
                if capa.dataProvider():
                    capa.dataProvider().dataChanged.connect(self.recalcular_metricas_tiempo_real)
        self.recalcular_metricas_tiempo_real()
    def recalcular_metricas_tiempo_real(self, *args):
        total_cubierta = 0.0
        total_semicubierta = 0.0
        total_pileta = 0.0
        
        for nombre_planta in ["GC_PLANTAP00", "GC_PLANTAP01"]:
            capas_planta = QgsProject.instance().mapLayersByName(nombre_planta)
            if capas_planta and len(capas_planta) > 0:
                capa_p = capas_planta[0]
                idx_cub = -1
                for campo in capa_p.fields():
                    if campo.name().lower() in ["cub-semi", "cub_semi", "cub/semi"]:
                        idx_cub = capa_p.fields().indexOf(campo.name())
                        break
                for objeto in capa_p.getFeatures():
                    geom = objeto.geometry()
                    if geom.isEmpty(): 
                        continue
                    area_objeto = geom.area()
                    tipo_mejora = "cubierta"
                    if idx_cub != -1 and objeto.attributes()[idx_cub] is not None:
                        tipo_mejora = str(objeto.attributes()[idx_cub]).strip().lower()
                    if "semi" in tipo_mejora:
                        total_semicubierta += area_objeto
                    elif "pileta" in tipo_mejora or "piscina" in tipo_mejora:
                        total_pileta += area_objeto
                    else:
                        total_cubierta += area_objeto
                        
        cant_cargadas = 0
        cant_sin_cargar = 0
        capas_baldios = QgsProject.instance().mapLayersByName("baldios")
        capas_p00 = QgsProject.instance().mapLayersByName("GC_PLANTAP00")
        
        if capas_baldios and len(capas_baldios) > 0:
            capa_b = capas_baldios[0]
            total_baldios = capa_b.featureCount()
            if capas_p00 and len(capas_p00) > 0 and capas_p00[0].featureCount() > 0:
                capa_p00_act = capas_p00[0]
                for f_baldio in capa_b.getFeatures():
                    geom_b = f_baldio.geometry()
                    interseca = False
                    if not geom_b.isEmpty():
                        for f_p00 in capa_p00_act.getFeatures():
                            if geom_b.intersects(f_p00.geometry()):
                                interseca = True
                                break
                    if interseca:
                        cant_cargadas += 1
                    else:
                        cant_sin_cargar += 1
            else:
                cant_sin_cargar = total_baldios
                
        self.lbl_cargadas.setText(str(cant_cargadas))
        self.lbl_sin_cargar.setText(str(cant_sin_cargar))
        self.lbl_val_cub.setText(f"{total_cubierta:.2f} m²")
        self.lbl_val_semi.setText(f"{total_semicubierta:.2f} m²")
        self.lbl_val_pil.setText(f"{total_pileta:.2f} m²")
        suma_total = total_cubierta + total_semicubierta + total_pileta
        self.lbl_val_total.setText(f"{suma_total:.2f} m²")
