# -*- coding: utf-8 -*-
import os
import gc
import shutil
import csv
from qgis.core import (QgsProject, QgsFeatureRequest, QgsExpression, QgsField,
                       QgsDxfExport, Qgis, QgsSymbol, QgsSimpleLineSymbolLayer)
from qgis.PyQt.QtCore import QFile, QVariant, QCoreApplication
from qgis.PyQt.QtGui import QColor

class MotorExportacionDxf:
    def __init__(self, iface, ruta_destino, fn_log, fn_progreso):
        self.iface = iface
        self.carpeta_destino = os.path.normpath(ruta_destino)
        self.fn_log = fn_log
        self.fn_progreso = fn_progreso

    def ejecutar(self):
        self.fn_log("🧹 Preparando y vaciando el directorio de salida catastral...")
        gc.collect()

        if os.path.exists(self.carpeta_destino):
            for elemento in os.listdir(self.carpeta_destino):
                ruta_elemento = os.path.join(self.carpeta_destino, elemento)
                try:
                    if os.path.isdir(ruta_elemento):
                        shutil.rmtree(ruta_elemento)
                    else:
                        os.remove(ruta_elemento)
                except:
                    pass
        else:
            os.makedirs(self.carpeta_destino)

        nombres_capas = ["GC_PLANTAP00_Corregido_Ortogonal", "GC_PLANTAP01_Corregido_Ortogonal"]
        datos_reporte = {}
        nomenclaturas_p00_unicas = set()

        for idx_capa, nombre_capa in enumerate(nombres_capas):
            capas_encontradas = QgsProject.instance().mapLayersByName(nombre_capa)
            if not capas_encontradas:
                self.fn_log(f"❌ No se encontró la capa '{nombre_capa}' en el proyecto.", "ERROR")
                continue
                
            capa_original = capas_encontradas[0]
            self.fn_log(f"🔄 Analizando estructura de: {nombre_capa}...")

            nombre_capa_cad = "GC_PLANTAP00" if "P00" in nombre_capa else "GC_PLANTAP01"
            es_p00 = "P00" in nombre_capa

            total_original_qgis = capa_original.featureCount()
            datos_reporte[nombre_capa_cad] = {
                'total_original_qgis': total_original_qgis,
                'categorias': {},
                'suma_verificacion_cad': 0
            }

            campo_cub = "Cub-Semi"

            # 🧠 ESCANEO DIRECTO EN MEMORIA RAM
            subgrupos_unicos = set()
            for f in capa_original.getFeatures():
                form_val = str(f["Formulario"]).strip() if f["Formulario"] is not None else "Vivienda"
                cub_val = str(f[campo_cub]).strip() if f[campo_cub] is not None else "Cubierta"
                punt_val = str(f["Puntaje"]).strip() if f["Puntaje"] is not None else "Categ_C"
                
                form_val_limpio = form_val.replace(" ", "_").replace("/", "-")
                cub_val_limpio = cub_val.replace(" ", "_").replace("/", "-")
                punt_val_limpio = punt_val.replace(" ", "_").replace("/", "-")
                
                comb_str = f"{form_val_limpio}_{cub_val_limpio}_{punt_val_limpio}"
                subgrupos_unicos.add((comb_str, form_val, cub_val, punt_val))

                nc_val = str(f["NC"]).strip() if f["NC"] is not None else ""
                if nc_val and nc_val.lower() != "null":
                    if es_p00:
                        nomenclaturas_p00_unicas.add(nc_val)

            self.fn_log(f"   -> Encontrados {len(subgrupos_unicos)} sub-grupos únicos en RAM. Generando DXF...")
            
            lista_subgrupos = sorted(subgrupos_unicos)
            for idx_sub, (comb_str, f_orig, c_orig, p_orig) in enumerate(lista_subgrupos):
                nombre_final_dxf = f"{nombre_capa_cad}_{comb_str}"
                ruta_dxf = os.path.join(self.carpeta_destino, f"{nombre_final_dxf}.dxf")

                # 🚀 FILTRADO POR EXPRESIÓN EN CALIENTE
                query = f'"Formulario" = \'{f_orig}\' AND "{campo_cub}" = \'{c_orig}\' AND "Puntaje" = \'{p_orig}\''
                request = QgsFeatureRequest().setFilterExpression(query)
                
                capa_filtrada = capa_original.materialize(request)
                cant_geometrias_cad = capa_filtrada.featureCount()
                
                if cant_geometrias_cad > 0:
                    datos_reporte[nombre_capa_cad]['categorias'][comb_str] = cant_geometrias_cad
                    datos_reporte[nombre_capa_cad]['suma_verificacion_cad'] += cant_geometrias_cad

                    QgsProject.instance().addMapLayer(capa_filtrada, False)

                    capa_line_layer = QgsSimpleLineSymbolLayer()
                    capa_line_layer.setColor(QColor(255, 0, 0)) 
                    capa_line_layer.setWidth(0.35)
                    
                    simbolo_rojo = QgsSymbol.defaultSymbol(capa_filtrada.geometryType())
                    if simbolo_rojo:
                        simbolo_rojo.changeSymbolLayer(0, capa_line_layer)
                        capa_filtrada.renderer().setSymbol(simbolo_rojo)

                    capa_filtrada.setName(nombre_capa_cad)

                    # MOTOR DE EXPORTACIÓN HÍBRIDO (UNIVERSAL PARA 3.X Y 4.X)
                    exportador = QgsDxfExport()
                    exportador.setMapSettings(self.iface.mapCanvas().mapSettings())
                    exportador.setDestinationCrs(capa_filtrada.crs())
                    exportador.addLayers([QgsDxfExport.DxfLayer(capa_filtrada)])
                    
                    # 🧠 DETECCIÓN INTELIGENTE DE ENUMERADORES
                    if hasattr(Qgis, 'FeatureSymbologyExport'):
                        # Ruta usada en QGIS 4.x
                        exportador.setSymbologyExport(Qgis.FeatureSymbologyExport.FeatureSymbology)
                    else:
                        # Ruta clásica usada en QGIS 3.x
                        exportador.setSymbologyExport(QgsDxfExport.FeatureSymbology)
                    
                    exportador.setForce2d(True)
                    exportador.setLayerTitleAsName(True)
                    os.environ["DXF_WRITE_HATCH"] = "FALSE"

                    archivo_salida = QFile(ruta_dxf)
                    resultado = exportador.writeToFile(archivo_salida, "UTF-8") 
                    archivo_salida.close()
                    
                    QgsProject.instance().removeMapLayer(capa_filtrada)
                    
                    if resultado == QgsDxfExport.ExportResult.Success:
                        self.fn_log(f"      ✅ DXF Creado: {nombre_final_dxf}.dxf")
                    else:
                        self.fn_log(f"      ❌ Error código {resultado} en {nombre_final_dxf}", "ERROR")
                
                progreso_parcial = 5 + (idx_capa * 45) + int(((idx_sub + 1) / len(lista_subgrupos)) * 45)
                self.fn_progreso(progreso_parcial)

        # 📝 ESCRITURA DE INFORMES DE AUDITORÍA FINAL .TXT
        self.fn_progreso(95)
        self.fn_log("📝 Creando reporte de auditoría de elementos (Control_Exportacion.txt)...")
        
        ruta_reporte = os.path.join(self.carpeta_destino, "Control_Exportacion.txt")
        with open(ruta_reporte, "w", encoding="utf-8") as f:
            f.write("=========================================================\n")
            f.write("         REPORTE DE AUDITORÍA Y CONTROL DE ELEMENTOS     \n")
            f.write("=========================================================\n\n")
            
            total_general_proyecto_cad = 0
            for planta, datos in datos_reporte.items():
                f.write(f"🏢 PLANTA: {planta}\n")
                f.write(f"---------------------------------------------------------\n")
                f.write(f"  • Registros en la tabla de QGIS original: {datos['total_original_qgis']}\n")
                f.write(f"  • Polígonos físicos reales inyectados en CAD: {datos['suma_verificacion_cad']}\n\n")
                f.write(f"  📦 Desglose de elementos reales por archivo .dxf:\n")
                for cat, cant in sorted(datos['categorias'].items()):
                    f.write(f"    - {cat.replace('_', ' ')}: {cant} polígonos cerrados.\n")
                f.write(f"\n  📊 TOTAL EN AUTOCAD PARA ESTA PLANTA: {datos['suma_verificacion_cad']} elementos.\n")
                total_general_proyecto_cad += datos['suma_verificacion_cad']
            f.write(f"\n🚀 TOTAL DE ELEMENTOS GEOMÉTRICOS EXPORTADOS AL CAD: {total_general_proyecto_cad}\n")

        # --- EXPORTACIÓN 1: Archivo CSV ---
        self.fn_log("💾 Escribiendo archivo CSV de nomenclaturas únicas...")
        ruta_csv = os.path.join(self.carpeta_destino, "Nomenclaturas_Unicas_P00.csv")
        try:
            with open(ruta_csv, mode="w", newline="", encoding="utf-8") as archivo_csv:
                escritor = csv.writer(archivo_csv, delimiter=";")
                escritor.writerow(["NC"])  
                for nc in sorted(nomenclaturas_p00_unicas):
                    escritor.writerow([nc])
        except Exception as e:
            self.fn_log(f"⚠️ Error al guardar CSV: {e}", "ERROR")

        self.fn_progreso(100)
