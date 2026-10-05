# -*- coding: utf-8 -*-
from qgis.PyQt.QtGui import QColor
from qgis.PyQt.QtCore import QVariant
from qgis.core import (QgsProject, QgsVectorLayer, QgsRuleBasedRenderer, 
                       QgsSymbol, QgsSimpleFillSymbolLayer, QgsSingleSymbolRenderer,
                       QgsField, QgsDefaultValue, QgsEditorWidgetSetup, Qgis, QgsWkbTypes)

# 🚀 INYECCIÓN DE TIPOS DUALES PARA CAMPOS VECTORIALES (QGIS 3 / 4)
try:
    from qgis.core import QMetaType
    TIPO_TEXTO = QMetaType.Type.QString
    TIPO_REAL = QMetaType.Type.Double
except:
    TIPO_TEXTO = QVariant.String
    TIPO_REAL = QVariant.Double

class OptimizadorExterno:
    @staticmethod
    def crear_capas_de_dibujo_vacias(iface, ui=None):
        if ui: ui.log("[PUNTO CONTROL] Iniciando estructuración de capas de digitalización vectoriales...")
        
        try:
            capas_baldios = QgsProject.instance().mapLayersByName("baldios")
            if capas_baldios and len(capas_baldios) > 0:
                crs_id = capas_baldios[0].crs().authid()
            else:
                crs_id = QgsProject.instance().crs().authid()

            if hasattr(Qgis, 'GeometryType'):
                geom_tipo_poligono = Qgis.GeometryType.Polygon
            else:
                geom_tipo_poligono = QgsWkbTypes.PolygonGeometry

            simbolo_planta = QgsSymbol.defaultSymbol(geom_tipo_poligono)
            capa_estilo_planta = QgsSimpleFillSymbolLayer()
            capa_estilo_planta.setFillColor(QColor(0, 0, 0, 0))
            capa_estilo_planta.setStrokeColor(QColor("red"))
            capa_estilo_planta.setStrokeWidth(0.0000)
            simbolo_planta.changeSymbolLayer(0, capa_estilo_planta)
            renderizador_planta = QgsSingleSymbolRenderer(simbolo_planta)

            nombres_capas = ["GC_PLANTAP00", "GC_PLANTAP01"]

            for nombre in nombres_capas:
                capas_viejas = QgsProject.instance().mapLayersByName(nombre)
                if capas_viejas:
                    if ui: ui.log(f"[LIMPIEZA] Eliminando capa previa '{nombre}' de la memoria de QGIS...")
                    for capa_viejalayer in capas_viejas:
                        QgsProject.instance().removeMapLayer(capa_viejalayer.id())

                if ui: ui.log(f"[PUNTO CONTROL] Generating estructura virgen para '{nombre}'...")
                
                capa = QgsVectorLayer(f"Polygon?crs={crs_id}", nombre, "memory")
                prov = capa.dataProvider()
                
                # 📐 ASIGNACIÓN ADAPTATIVA BLINDADA PARA QGIS 4.2.2 Y QGIS 3.22
                campos_nuevos = [
                    QgsField("Cub-Semi", TIPO_TEXTO),
                    QgsField("Superficie", TIPO_REAL),
                    QgsField("NC", TIPO_TEXTO),
                    QgsField("Puntaje", TIPO_TEXTO),
                    QgsField("Formulario", TIPO_TEXTO)
                ]
                prov.addAttributes(campos_nuevos)
                capa.updateFields()
                
                campos_actuales = [f.name() for f in capa.fields()]
                if ui: ui.log(f"[AUDITORÍA CAMPOS] '{nombre}' creada con {len(campos_actuales)} campos: {campos_actuales}")

                expr_nc = (
                    "if(\"NC\" IS NULL, "
                    "with_variable('parcela_mayor', aggregate(layer:='baldios', aggregate:='array_agg', expression:=\"CCA\", filter:=intersects($geometry, geometry(@parent)), order_by:=area(intersection($geometry, geometry(@parent))) * -1), array_first(@parcela_mayor)), "
                    "\"NC\")"
                )
                expr_superficie_metros = "round($area, 2)"

                idx_cub = capa.fields().indexOf("Cub-Semi")
                idx_sup = capa.fields().indexOf("Superficie")
                idx_nc = capa.fields().indexOf("NC")
                idx_pun = capa.fields().indexOf("Puntaje")
                idx_form = capa.fields().indexOf("Formulario")
                
                if idx_cub != -1: capa.setDefaultValueDefinition(idx_cub, QgsDefaultValue("'Cubierta'", False))
                if idx_sup != -1: capa.setDefaultValueDefinition(idx_sup, QgsDefaultValue(expr_superficie_metros, True))
                if idx_nc != -1: capa.setDefaultValueDefinition(idx_nc, QgsDefaultValue(expr_nc, False))
                if idx_pun != -1: capa.setDefaultValueDefinition(idx_pun, QgsDefaultValue("'Categ C'", False))
                if idx_form != -1: capa.setDefaultValueDefinition(idx_form, QgsDefaultValue("'Vivienda'", False))

                if idx_cub != -1:
                    capa.setEditorWidgetSetup(idx_cub, QgsEditorWidgetSetup("ValueMap", {"map": {"Cubierta": "Cubierta", "Semicubierta": "Semicubierta", "Pileta": "Pileta"}}))
                if idx_pun != -1:
                    capa.setEditorWidgetSetup(idx_pun, QgsEditorWidgetSetup("ValueMap", {"map": {"Categ A": "Categ A", "Categ B": "Categ B", "Categ C": "Categ C", "Categ D": "Categ D"}}))
                if idx_form != -1:
                    capa.setEditorWidgetSetup(idx_form, QgsEditorWidgetSetup("ValueMap", {"map": {"Vivienda": "Vivienda", "Galpón": "Galpón", "Oficina": "Oficina", "Comercio": "Comercio"}}))

                capa.setRenderer(renderizador_planta.clone())
                QgsProject.instance().addMapLayer(capa)
                if ui: ui.log(f"[ÉXITO INTERNO] Capa '{nombre}' inyectada en el panel correctamente.")
            if iface:
                iface.layerTreeView().refreshLayerSymbology("")
                
                # 🚀 RECONEXIÓN DINÁMICA: Forzamos al panel de estadísticas a escuchar las nuevas capas en caliente
                clase_capa = QgsProject.instance().mapLayersByName("GC_PLANTAP00")[0].__class__ if QgsProject.instance().mapLayersByName("GC_PLANTAP00") else None
                if clase_capa:
                    for dock in iface.mainWindow().findChildren(clase_capa):
                        if hasattr(dock, "conectar_disparadores_individuales"):
                            dock.conectar_disparadores_individuales()
                        
            if ui: ui.log("Capas plantas listas, estructuradas y automatizadas con éxito.", "INFO")

        except Exception as e:
            if ui: ui.log(f"Error crítico al estructurar las bases de datos de dibujo: {str(e)}", "ERROR")

    @staticmethod
    def aplicar_estilos_foto_baldios(ui=None):
        if ui: ui.log("Iniciando inyección de simbología externa basada en reglas...")
        
        capas = QgsProject.instance().mapLayersByName("baldios")
        if not capas:
            if ui: ui.log("No se encontró la capa resultante 'baldios' en el mapa.", "ERROR")
            return
        
        capa_baldios_individual = capas[0]

        try:
            if ui: ui.log("Construyendo árbol de reglas estilísticas con overlay nativo...")
            raiz_regla = QgsRuleBasedRenderer.Rule(None)
            expr_edif = "overlay_intersects('GC_PLANTAP00')"
            
            if hasattr(Qgis, 'GeometryType'):
                geom_tipo_regla = Qgis.GeometryType.Polygon
            else:
                geom_tipo_regla = QgsWkbTypes.PolygonGeometry

            simbolo_verde = QgsSymbol.defaultSymbol(geom_tipo_regla)
            capa_relleno_verde = QgsSimpleFillSymbolLayer()
            capa_relleno_verde.setFillColor(QColor(0, 0, 0, 0))
            capa_relleno_verde.setStrokeColor(QColor("#15bc42"))
            capa_relleno_verde.setStrokeWidth(0.96)
            simbolo_verde.changeSymbolLayer(0, capa_relleno_verde)
            raiz_regla.appendChild(QgsRuleBasedRenderer.Rule(simbolo_verde, filterExp=expr_edif, label="Con Edificación"))
            
            simbolo_rojo = QgsSymbol.defaultSymbol(geom_tipo_regla)
            capa_relleno_rojo = QgsSimpleFillSymbolLayer()
            capa_relleno_rojo.setFillColor(QColor(0, 0, 0, 0))
            capa_relleno_rojo.setStrokeColor(QColor("red"))
            capa_relleno_rojo.setStrokeWidth(0.96)
            simbolo_rojo.changeSymbolLayer(0, capa_relleno_rojo)
            raiz_regla.appendChild(QgsRuleBasedRenderer.Rule(simbolo_rojo, filterExp="ELSE", label="Faltan Cargar"))
            
            capa_baldios_individual.setRenderer(QgsRuleBasedRenderer(raiz_regla))
            capa_baldios_individual.triggerRepaint()
            
            if ui and hasattr(ui, 'iface') and ui.iface:
                ui.iface.layerTreeView().refreshLayerSymbology(capa_baldios_individual.id())
            if ui: ui.log("Simbología basada en reglas aplicada con éxito.", "EXITO")
            
        except Exception as e:
            if ui: ui.log(f"Falló el renderizado estético: {str(e)}", "ERROR")

