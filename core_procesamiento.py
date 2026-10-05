# -*- coding: utf-8 -*-
import processing
from qgis.core import (QgsProject, QgsVectorLayer, QgsVectorLayerJoinInfo, 
                       QgsFeatureRequest, QgsCoordinateReferenceSystem)
from .optimizaciones_externas import OptimizadorExterno # Enlace directo

class ProcesadorCatastral:
    def __init__(self, interface):
        self.ui = interface 
        self.proceso_terminado = False # Variable de estado inicial

    def detectar_faja_posgar(self, capa):
        """Calcula dinámicamente la faja POSGAR 2007 (2, 3 o 4) según los rangos oficiales del IGN."""
        extensión = capa.extent()
        longitud_centro = (extensión.xMinimum() + extensión.xMaximum()) / 2.0
        
        # Salvaguarda por si los datos miden en millones (3857) pero la capa está mal declarada
        if longitud_centro < -180 or longitud_centro > 180:
            self.ui.log("⚠️ Coordenadas métricas detectadas. Asumiendo Faja 2 por defecto para Alto Valle.", "DEBUG")
            return QgsCoordinateReferenceSystem("EPSG:5344"), "Faja 2 (EPSG:5344)"

        self.ui.log(f"Centro geográfico de la zona (Longitud): {longitud_centro:.4f}° O")
        
        # Ajuste político-catastral para el Alto Valle (Contiene Cinco Saltos en Faja 2)
        if longitud_centro <= -67.1000:
            return QgsCoordinateReferenceSystem("EPSG:5344"), "Faja 2 (Alto Valle / Bariloche - EPSG:5344)"
        elif -67.1000 < longitud_centro <= -64.5000:
            return QgsCoordinateReferenceSystem("EPSG:5345"), "Faja 3 (Valle Medio / Línea Sur - EPSG:5345)"
        else:
            return QgsCoordinateReferenceSystem("EPSG:5346"), "Faja 4 (Viedma / Atlántica - EPSG:5346)"

    def ejecutar(self, path_val, path_vm1, path_par):
        self.ui.log("Iniciando procesamiento de datos catastrales...")
        self.ui.actualizar_progreso(5)
        
        capa_val_id = None
        capa_vm1_id = None
        
        try:
            self.ui.log("Cargando capas y archivos CSV en el sistema...")
            
            uri_val = f"file:///{path_val}?delimiter=;&quote=\"&detectTypes=no&useHeader=yes"
            uri_vm1 = f"file:///{path_vm1}?delimiter=,&quote=\"&detectTypes=no&useHeader=yes"
            
            capa_val = QgsVectorLayer(uri_val, "valuaciones_temp", "delimitedtext")
            capa_vm1 = QgsVectorLayer(uri_vm1, "vm1_temp", "delimitedtext")
            capa_parcelario = QgsVectorLayer(path_par, "PARCELARIO", "ogr")

            if not capa_parcelario.isValid() or not capa_val.isValid() or not capa_vm1.isValid():
                raise Exception("No se pudo cargar correctamente uno o más archivos. Verifique las rutas.")

            QgsProject.instance().addMapLayers([capa_val, capa_vm1], False)
            capa_val_id = capa_val.id()
            capa_vm1_id = capa_vm1.id()

            # --- VALIDACIÓN DE COLUMNAS ---
            campos_par_limpios = [f.name().strip() for f in capa_parcelario.fields()]

            campo_nomenclatura_vm1 = None
            campo_atr_texto = None
            for f in capa_vm1.fields():
                nombre_limpio = f.name().strip().upper()
                if nombre_limpio == "NOMENCLATURA":
                    campo_nomenclatura_vm1 = f.name()
                elif nombre_limpio in ["ATR TEXTO", "ATRTEXTO"]:
                    campo_atr_texto = f.name()

            campo_nomenclatura_val = None
            campo_mejora_val = None
            for f in capa_val.fields():
                nombre_normalizado = f.name().strip().lower().replace("é", "e")
                if "nomenclatura" in nombre_normalizado:
                    campo_nomenclatura_val = f.name()
                elif "mejora fiscal" in nombre_normalizado or "mejorafiscal" in nombre_normalizado:
                    campo_mejora_val = f.name()

            if campo_nomenclatura_val is None or campo_mejora_val is None:
                raise Exception("El CSV de Valuaciones no contiene las columnas requeridas ('Nomenclatura' o 'Mejora Fiscal').")
            if campo_nomenclatura_vm1 is None or campo_atr_texto is None:
                raise Exception("El CSV de VM1 no contiene las columnas requeridas ('NOMENCLATURA' o 'ATR TEXTO').")
            if "CCA" not in campos_par_limpios:
                raise Exception("La capa Shapefile PARCELARIO no posee la columna clave 'CCA'.")

            # 🚀 1. DETERMINAMOS LA FAJA CORRECTA EN GRADOS ANTES DE TOCAR LA GEOMETRÍA
            crs_faja_detectada, faja_texto = self.detectar_faja_posgar(capa_parcelario)
            self.ui.log(f"Sistema métrico de destino unificado: <b>{faja_texto}</b>", "DEBUG")

            self.ui.actualizar_progreso(20)

            # 2. Unión Virtual VM1 -> PARCELARIO
            self.ui.log("Realizando unión de datos con tabla VM1...")
            union_vm1 = QgsVectorLayerJoinInfo()
            union_vm1.setJoinLayer(capa_vm1)
            union_vm1.setJoinFieldName(campo_nomenclatura_vm1)
            union_vm1.setTargetFieldName("CCA")
            union_vm1.setUsingMemoryCache(True)
            union_vm1.setPrefix("vm1_")
            capa_parcelario.addJoin(union_vm1)
            self.ui.actualizar_progreso(35)

            # 3. Unión Virtual Valuaciones -> PARCELARIO
            self.ui.log("Realizando unión de datos con tabla Valuaciones...")
            union_val = QgsVectorLayerJoinInfo()
            union_val.setJoinLayer(capa_val)
            union_val.setJoinFieldName(campo_nomenclatura_val)
            union_val.setTargetFieldName("CCA")
            union_val.setUsingMemoryCache(True)
            union_val.setPrefix("valuaciones_vigentes_") 
            capa_parcelario.addJoin(union_val)
            self.ui.actualizar_progreso(50)

            # --- PRIMER FILTRO MANUAL ---
            self.ui.log("Filtrando parcelas útiles (Descartando 'Mejora Fiscal' IS NULL)...")
            expr_paso1 = f'"valuaciones_vigentes_{campo_mejora_val}" IS NOT NULL'
            req_paso1 = QgsFeatureRequest().setFilterExpression(expr_paso1)
            capa_filtrada_temp = capa_parcelario.materialize(req_paso1)
            
            # 🚀 REPROYECCIÓN FORMAL: Convertimos los grados decimales a metros reales de la Faja POSGAR
            self.ui.log(f"Transformando matriz geométrica de Grados a Metros Verdaderos ({crs_faja_detectada.authid()})...")
            capa_filtrada = processing.run("native:reprojectlayer", {
                'INPUT': capa_filtrada_temp,
                'TARGET_CRS': crs_faja_detectada,
                'OUTPUT': 'memory:'
            })['OUTPUT']
            capa_filtrada.setName("Parcelario de la Localidad")
            
            cant_paso1 = capa_filtrada.featureCount()
            QgsProject.instance().addMapLayer(capa_filtrada)
            self.ui.log(f"Capa intermedia 'Parcelario de la Localidad' generada con {cant_paso1} parcelas métricas.")
            self.ui.actualizar_progreso(70)

            # --- SEGUNDO FILTRO MANUAL ---
            self.ui.log("Cortando parcelario intermedio para extraer baldíos...")
            expr_baldios = (
                f'"valuaciones_vigentes_{campo_mejora_val}" = \'0,00\' AND '
                f'("vm1_{campo_atr_texto}" IS NULL OR length(trim("vm1_{campo_atr_texto}")) = 0)'
            )
            req_baldios = QgsFeatureRequest().setFilterExpression(expr_baldios)
            
            # Como capa_filtrada ya está en metros reales de Faja 2, materialize() la extrae perfecta en metros
            capa_baldios = capa_filtrada.materialize(req_baldios)
            capa_baldios.setName("baldios")

            # 🛠️ REMOCIÓN SEGURA DE UNIONES (Sintaxis universal por ID de texto de capa)
            try:
                capa_parcelario.removeJoin(str(capa_vm1_id))
                capa_parcelario.removeJoin(str(capa_val_id))
            except:
                pass

            if capa_val_id: QgsProject.instance().removeMapLayers([capa_val_id])
            if capa_vm1_id: QgsProject.instance().removeMapLayers([capa_vm1_id])
            self.ui.actualizar_progreso(100)

            QgsProject.instance().addMapLayer(capa_baldios)
            
            self.proceso_terminado = True
            OptimizadorExterno.aplicar_estilos_foto_baldios(self.ui)
            
            self.ui.log("Proceso de backend finalizado correctamente en metros planos reales.", "EXITO")
            
            return crs_faja_detectada

        except Exception as e:
            self.proceso_terminado = False
            self.ui.log(f"Ocurrió un error inesperado durante el procesamiento: {str(e)}", "ERROR")
            self.ui.actualizar_progreso(0)
            if capa_val_id: QgsProject.instance().removeMapLayers([capa_val_id])
            if capa_vm1_id: QgsProject.instance().removeMapLayers([capa_vm1_id])
            return QgsCoordinateReferenceSystem("EPSG:3857")
