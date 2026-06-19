# SOLICITUD PRO: Auditoría normas vigentes A1-01 2025

> Nota 2026-06-18: este documento contiene cifras historicas previas a la reconstruccion deduplicada de `articles`. Para estado actual usar `docs/CLAUDE_HANDOFF.md`.

**Fecha**: 2026-06-18  
**De**: Code  
**Para**: PRO  
**Estado**: Esperando validación jurídica

---

## RESUMEN EJECUTIVO

Code ejecutó auditoría READ-ONLY de normas en BD para 8 temas A1-01. Resultado: discrepancias entre leyes en BD e leyes esperadas en convocatoria.

**Halazgo crítico**: Leyes en BD son MÁS RECIENTES que las buscadas. Requiere validar vigencia 2025 en BOE/DOGV oficial.

---

## DATOS DE CODE (SIN MODIFICACIONES)

### Temas y normas mapeadas

**TEMA 8** (Les Corts, procedimiento legislativo)
- ✅ Reglamento Les Corts consolidado DOGV — 191 artículos
- ✅ LO 5/1982 Estatuto Autonomía CV — 167 arts
- ✅ Ley 5/1983 Gobierno Valenciano — 159 arts
- ✅ Ley 1/1987 Electoral Valenciana — 93 arts

**TEMA 17** (Patrimonio de AAPP)
- ✅ Ley 14/2003 Patrimonio Generalitat CV — 440 artículos
- ✅ Ley 33/2003 Patrimonio AAPP — 217 arts
- ⚠️ Ley 8/2010 (Régimen Local CV): EN BD ID 19, PERO NO ENLAZADA a tema 17

**TEMA 18** (Formas actividad administrativa)
- ✅ Ley 40/2015 Régimen Jurídico SP — 191 artículos
- ⚠️ Ley 39/2015 (Procedimiento Administrativo): EN BD, NO ENLAZADA a tema 18

**TEMA 21** (Contratos sector público)
- ✅ Ley 9/2017 (LCSP) — 416 artículos

**TEMA 32** (Seguridad Social)
- ✅ RD Legislativo 8/2015 LGSS — 463 artículos

**TEMA 52** (Competencias: Justicia, Interior)
- ⚠️ SOLO LO 5/1982 Estatuto — 167 artículos (comparte con 54, 55)

**TEMA 54** (Competencias: Sanidad)
- ⚠️ SOLO LO 5/1982 Estatuto — 167 artículos (comparte con 52, 55)

**TEMA 55** (Competencias: Economía)
- ⚠️ SOLO LO 5/1982 Estatuto — 167 artículos (comparte con 52, 54)

---

## DISCREPANCIAS CRÍTICAS

| Búsqueda esperada | Encontrada en BD | Comentario |
|---|---|---|
| **Ley 12/2006** Hacienda Pública CV | **Ley 1/2015** Hacienda Pública Generalitat | ¿Cuál es vigente 2025? |
| **Ley 7/2017** Funciones Públicas CV | **Ley 4/2021** Funciones Públicas Valenciana | ¿Cuál es vigente 2025? |

---

## PROBLEMAS PENDIENTES DE VALIDACIÓN

### P1: Vigencia 2025 (nivel: extremadamente alto)

1. **Hacienda Pública Generalitat**
   - ¿Es Ley 1/2015 vigente en 2025?
   - Si NO: dónde obtener Ley 12/2006 (DOGV link)
   - Si SÍ: confirma BOE/DOGV de publicación

2. **Funciones Públicas Valenciana**
   - ¿Es Ley 4/2021 vigente en 2025?
   - Si NO: dónde obtener Ley 7/2017 (DOGV link)
   - Si SÍ: confirma DOGV de publicación

3. **Reglamento Les Corts**
   - ¿La versión "consolidado DOGV" es auténtica oficial?
   - ¿Existe decreto/resolución más reciente?

### P2: Delimitación de artículos (8 hallazgos pendientes de validación_fina)

**Tema 8**: ¿Qué artículos del Reglamento Les Corts (191 total) aplican realmente?
- Arts específicos a incluir: [ ]

**Tema 17**: ¿Ley 8/2010 debe enlazarse a tema patrimonio?
- Si SÍ: qué artículos de Ley 8/2010
- Si NO: por qué (no aplica a patrimonio CV)

**Tema 18**: ¿Ley 39/2015 debe enlazarse a tema formas actividad?
- Si SÍ: qué artículos de Ley 39/2015
- Si NO: por qué

**Tema 52 (Justicia/Interior)**: Artículos del Estatuto (LO 5/1982) específicos para estas competencias
- Arts: [ ]

**Tema 54 (Sanidad)**: Artículos del Estatuto específicos para sanidad
- Arts: [ ]

**Tema 55 (Economía)**: Artículos del Estatuto específicos para economía
- Arts: [ ]

### P3: Consolidados vs Auténticos

¿Los textos "consolidados" de DOGV/BOE son válidos para A1-01 2025 o se requieren versiones "auténticas" (originales de BOE del año de publicación)?

---

## FORMATO DE RESPUESTA ESPERADO

```
## P1 Vigencia 2025
- Ley 1/2015 Hacienda: [VIGENTE / DEROGADA] — razón + BOE/DOGV
- Ley 4/2021 Funciones: [VIGENTE / DEROGADA] — razón + DOGV
- Reglamento Les Corts: [versión vigente + link DOGV]

## P2 Delimitación artículos
- Tema 8: Reglamento Les Corts arts. [X-Y]
- Tema 17: Ley 8/2010 arts. [A-B] (incluir / NO incluir)
- Tema 18: Ley 39/2015 arts. [C-D] (incluir / NO incluir)
- Tema 52: Estatuto arts. [números específicos para Justicia/Interior]
- Tema 54: Estatuto arts. [números específicos para Sanidad]
- Tema 55: Estatuto arts. [números específicos para Economía]

## P3 Consolidados
[Recomendación: consolidados VÁLIDOS / NO VÁLIDOS para A1-01 2025]
```

---

## CONTEXTO TÉCNICO

- **BD**: `db/gvadicto.sqlite`
- **Leyes importadas**: 80
- **Artículos**: 12,838
- **Temas A1-01**: 75
- **topic_sources mappings**: 204 (sin delimitación article_id)
- **Hallazgos abiertos**: 23 (8 de estos son delimitación_articulos_pendiente)

---

## SIGUIENTE PASO

PRO valida P1, P2, P3 → Code actualiza `topic_sources` con `article_id` específicos → Code regenera preguntas sobre temas validados.

**Sin modificación BD. Read-only audit. Esperando tu validación.**
