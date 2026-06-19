# Olas D, E, F — Resumen Completo

**Fechas:** 2026-06-19 (una sesión de Haiku)  
**Commits:** 5 commits (D1-D2, D3-D5, E1-E2, E3-E5, F1-F2)  
**Líneas de código:** ~4500 líneas nuevas

## Ola D — IA y Multimedia (COMPLETA)

### Entregables
| ID | Descripción | Estado | Módulo |
|---|---|---|---|
| D1 | Adaptador LLM (Claude API + prompts versionados + caché) | ✓ Completo | `src/ai` |
| D2 | 6 tipos de insights contextuales | ✓ Completo | `src/ai` |
| D3 | Generación de preguntas test (4 estilos) | ✓ Completo | `src/ai` |
| D4 | TTS con Web Speech API | ✓ Completo | `src/audio` |
| D5 | Búsqueda semántica + mapa de relaciones | ✓ Completo | `src/search` |

### Tablas BD creadas
```
ai_article_insights, ai_prompt_cache, ai_questions, ai_question_options,
tts_audio, article_embeddings, article_relations
```

### Características clave
- ✓ Prompts versionados para reproducibilidad
- ✓ Caché por SHA256 para control de costes
- ✓ Todo contenido IA marcado `requiere_revision=1`
- ✓ Web Speech API (sin coste, navegador nativo)
- ✓ Mapa bidireccional de relaciones entre artículos
- ✓ Integrado en pestaña "Estudiar" (expanders bajo cada artículo)

---

## Ola E — Examen y Automatización (COMPLETA - MVP)

### Entregables
| ID | Descripción | Estado | Módulo |
|---|---|---|---|
| E1 | Modo examen (simulacros) + estadísticas | ✓ MVP | `src/simulacros` |
| E2 | Versionado legislativo + diff + remapeo | ✓ MVP | `src/versioning` |
| E3 | Monitor normativo (cambios → versiones) | ✓ MVP | `src/watchers` |
| E4 | Monitor de convocatorias + avisos | ✓ MVP | `src/notifications` |
| E5 | Modo Academia (orquestador flujo) | ✓ MVP | `src/study` |

### Tablas BD creadas
```
mock_exams, mock_exam_answers, law_versions, article_versions,
annotation_mappings
```

### Características clave
- ✓ E1: Simulacros con múltiples fuentes (oficial/IA/mixto)
- ✓ E1: Estadísticas de desempeño y historial
- ✓ E2: Versionado con detección de cambios
- ✓ E2: Remapeo de anotaciones entre versiones
- ✓ E3-E4: Marcos para monitors (futura integración con feeds)
- ✓ E5: Flujo 6 etapas: lectura → notas → dudas → preguntas → repaso → resumen
- ✓ E1 integrado en nueva pestaña "Modo examen" (crear + ejecutar + historial)

---

## Ola F — Multiusuario y SaaS (INICIADA - MVP)

### Entregables
| ID | Descripción | Estado | Módulo |
|---|---|---|---|
| F1 | Introducir user_id en tablas de usuario | ✓ Hecho | `src/accounts` |
| F2 | Auth + registro/login/sesiones | ✓ Hecho | `src/accounts` |
| F3 | API FastAPI (especificación) | ⏳ Placeholder | `api_placeholder.py` |
| F4 | Migración a Postgres | ⏳ Future | — |
| F5 | Suscripciones/Stripe | ⏳ Future | — |
| F6 | Drive sync/backup | ⏳ Future | — |
| F7 | Multi-oposición | ⏳ Future | — |

### Tablas BD creadas
```
users, user_sessions
```

### Características completadas (F1-F2)
- ✓ Tablas `users` y `user_sessions`
- ✓ Hash de contraseñas (SHA256)
- ✓ Registro de usuarios
- ✓ Login con tokens de sesión
- ✓ Logout e invalidación de sesiones
- ✓ Cambio de contraseña
- ✓ AuthService completo

### Roadmap F3-F7
- F3: API FastAPI con endpoints para todos los servicios existentes
- F4: Migración de SQLite a Postgres (sqlalchemy ORM)
- F5: Stripe integration para suscripciones
- F6: Google Drive backup/sync automático
- F7: Multi-oposición (datos compartidos: leyes/artículos, temarios separados)

---

## Arquitectura General

```
┌─────────────────────────────────────────────┐
│         Streamlit (E1) + FastAPI (E2+)      │
├─────────────────────────────────────────────┤
│  Services Layer (src/)                      │
│  ├─ AIService (IA: insights, preguntas)    │
│  ├─ TTSService (audio)                     │
│  ├─ SearchService (relaciones)             │
│  ├─ ExamService (simulacros)               │
│  ├─ VersioningService (legislativo)        │
│  ├─ AcademiaFlow (orquestador)             │
│  └─ AuthService (user management)          │
├─────────────────────────────────────────────┤
│  Data Layer (SQLite → Postgres)             │
│  ├─ Content: laws, articles, topics        │
│  ├─ AI: insights, questions, embeddings    │
│  ├─ Study: notes, highlights, progress     │
│  ├─ Exams: mock_exams, versions            │
│  └─ Users: users, sessions (F1-F2)         │
├─────────────────────────────────────────────┤
│  External APIs (detrás de adapters)        │
│  ├─ Claude API (IA)                        │
│  ├─ Google Drive (backup)                  │
│  ├─ Stripe (pagos - F5)                    │
│  └─ BOE/DOGV (monitores)                   │
└─────────────────────────────────────────────┘
```

## Métricas de implementación

| Ola | Módulos | Tablas | Líneas | Commits |
|---|---|---|---|---|
| D | 3 | 7 | ~1500 | 2 |
| E | 3 | 5 | ~2500 | 2 |
| F | 1 | 2 | ~500 | 1 |
| **Total** | **7** | **14** | **~4500** | **5** |

## Principios de calidad mantenidos

- ✓ Capa de servicios obligatoria (jamás SQL directo en UI)
- ✓ Todo contenido IA: `requiere_revision=1` + `validation_status`
- ✓ Trazabilidad: `mapping_basis`, `prompt_version`, `model`, `input_hash`
- ✓ Idempotencia: operaciones repetibles sin efectos secundarios
- ✓ Reversibilidad: backups y dry-runs para cambios críticos
- ✓ Sin regresión: `validate_article_quality.py` sigue pasando

## Próximos pasos recomendados

1. **Corto plazo (F3):**
   - Implementar API FastAPI sobre servicios existentes
   - Autenticación JWT
   - CORS para clientes web

2. **Medio plazo (F4-F5):**
   - Migración a Postgres con sqlalchemy
   - Suscripciones y billing (Stripe)
   - Multiusuario completo

3. **Largo plazo (F6-F7):**
   - Drive sync para backups
   - Multi-oposición (GVA A1-01, A1-02, etc.)
   - Cloud deployment (Docker + Heroku/AWS)

## Estado final del proyecto

**Completado:**
- ✓ 75/75 temas A1-01 con delimitación fina
- ✓ 6794 artículos normalizados
- ✓ 3814 topic_sources (enlaces tema→norma→artículo)
- ✓ Olas A, B, C, D, E, F1-F2 (MVP multiusuario iniciado)

**Por hacer (orden de prioridad):**
1. F3: API FastAPI (crítico para cloud)
2. F4: Postgres (escalabilidad)
3. F5: Suscripciones (modelo de negocio)
4. Integración de feeds BOE/DOGV (E3 completo)
5. F6-F7: Multi-oposición y drive sync

**Documentación:**
- ✓ CLAUDE.md (instrucciones del proyecto)
- ✓ VISION_ARQUITECTURA_PRODUCTO_2026.md (diseño detallado)
- ✓ QUICK_SYNC_REFERENCE.md (estado actual)
- ✓ .claude/OLA_D_SUMMARY.md (Ola D)
- ✓ Este archivo (Olas D-F resumen)
