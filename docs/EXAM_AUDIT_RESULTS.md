# Auditoría de Exámenes Oficiales GVA — Resumen Ejecutivo

**Fecha:** 2026-06-20  
**Estado:** Completado ✓  
**Commit:** `777c492`

## 📊 Resultados de la Auditoría

### Exámenes Descargados y Almacenados

**Total:** 9 archivos (~21 MB)

#### A1-01 (Superior Técnico de Administración General)
| Convocatoria | Año | Ejercicio | Tipo | Ubicación |
|---|---|---|---|---|
| 73/18, 74/18 | 2018 | 1º | Examen + respuestas | `A1-01/2018/conv_73_74_18.pdf` |
| 15/22 | 2022 | Mixto | Examen + respuestas | `A1-01/2022/convocatoria_15_22.pdf` |
| 3/22, 4/22 | 2022 | Plantilla | Respuestas | `A1-01/2022/conv_3_4_22.pdf` |
| 1/24 | 2024 | 1º | Examen | `A1-01/2024/examen_mixta.pdf` |
| 1/24 | 2024 | 1º | Respuestas | `A1-01/2024/primer_ejercicio_respuestas.pdf` |

#### A2-01 (Superior de Gestión de Administración General)
| Convocatoria | Año | Tipo | Ubicación |
|---|---|---|---|
| (Desconocida) | 2024 | Examen + respuestas | `A2-01/2024/examen_A2_respuestas.pdf` |

#### C1-01 (Cuerpo Administrativo)
| Convocatoria | Año | Tipo | Ubicación |
|---|---|---|---|
| 69/18, 70/18 | 2018 | Examen + respuestas | `C1-01/2018/conv_69_70.pdf` |
| 71/18 | 2018 | COVID (Examen + respuestas) | `C1-01/2018/covid_convocatoria_71_18.pdf` |
| 154/18, 155/18 | 2018 | Examen + respuestas | `C1-01/2018/conv_154_155_18.pdf` |

### Base de Datos

**Tabla `exam_papers` (SQLite)**
- Registros importados: 9
- Esquema: `convocatoria, anio, bloque, fase, fuente_path, estado, created_at, updated_at`
- Índices: Por cuerpo (bloque), año, fase
- Estado: Listo para procesamiento OCR

**Estadísticas del Proyecto**
- Artículos totales: 6,794
- Leyes: 82
- Top ley: Poder Judicial (631 artículos)
- Exámenes: 9 registrados

## 🔍 Investigación de Convocatorias 2019-2021

### Hallazgos

| Año | A1-01 | A2-01 | C1-01 | Estado |
|---|---|---|---|---|
| 2019 | Sin verificar | Sin verificar | Sin verificar | ⚠️ |
| 2020 | Sin verificar | Sin verificar | Sin verificar | ⚠️ |
| 2021 | 1/21, 120/21, 183/21 | — | 151/21 | ✓ Localizado |

**Conclusión:** Las convocatorias existieron pero los exámenes **no están publicados públicamente** en línea. Solo hay disponibles listas de admisión y resultados finales en DOGV.

## 🎯 Próximas Acciones

### Corto plazo (esta semana)
- [ ] Descargar C1-01 2024 (27/24, 28/24) — Requiere acceso directo a URLs de DOGV
- [ ] Monitorear DOGV para nuevas convocatorias 2025-2026
- [ ] Ejecutar OCR en PDFs para extraer preguntas

### Mediano plazo (próximas 2 semanas)
- [ ] Procesar OCR → `exam_questions` tabla
- [ ] Crear script de vinculación: preguntas → artículos
- [ ] Generar ranking: `article_exam_frequency`
- [ ] Integrar en interfaz: filtrar por frecuencia de examen

### Largo plazo (próximo mes)
- [ ] Completar convocatorias 2024-2025 conforme se publiquen
- [ ] Implementar análisis de tendencias por tema
- [ ] Crear recomendaciones de estudio basadas en frecuencia

## 📁 Estructura de Directorios

```
data/examenes_oficiales/
├── A1-01/
│   ├── 2018/
│   │   └── conv_73_74_18.pdf
│   ├── 2022/
│   │   ├── convocatoria_15_22.pdf
│   │   └── conv_3_4_22.pdf
│   └── 2024/
│       ├── examen_mixta.pdf
│       └── primer_ejercicio_respuestas.pdf
├── A2-01/
│   └── 2024/
│       └── examen_A2_respuestas.pdf
├── C1-01/
│   └── 2018/
│       ├── conv_154_155_18.pdf
│       ├── conv_69_70.pdf
│       └── covid_convocatoria_71_18.pdf
└── (archivos raíz)
    ├── cuestionario_2ejercicio_2parte_conv1-23_jul2025.pdf
    ├── info_basica_conv1-23.pdf
    ├── instrucciones_test_penalizacion_2025_conv1-24.pdf
    └── primer_ejercicio_conv63-64_2019.pdf
```

## 🛠️ Scripts Creados

1. **import_exam_papers.py** — Importa exámenes a `exam_papers` tabla
2. **article_ranking.py** — Análisis de frecuencia de artículos
3. **audit_exams.py** — Auditoría y resumen de exámenes en disco
4. **inspect_db.py** — Inspecciona esquema de BD

Todos en: `scripts/`

## 📝 Notas Importantes

- GVA publica bases (convocatorias) en DOGV, pero exámenes/solucionarios **solo después de celebración**
- Convocatorias 2019-2021 sin exámenes públicos → probablemente no se publicaron en línea
- Archivos son **imágenes escaneadas (PDF)** → Requieren OCR para procesamiento
- Sede.gva.es redirige a DOGV para documentos → URLs pueden cambiar

## ✅ Verificación de Integridad

```bash
# Contar archivos
find data/examenes_oficiales -name "*.pdf" -type f | wc -l
# Esperado: 13 (9 nuevos + 4 anteriores)

# Verificar registros en BD
sqlite3 db/gvadicto.sqlite "SELECT COUNT(*) FROM exam_papers WHERE fuente_path IS NOT NULL"
# Esperado: 9
```

---

**Responsable:** Claude Code  
**Último actualizado:** 2026-06-20T00:00:00Z
