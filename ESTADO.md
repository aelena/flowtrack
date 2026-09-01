# Estado: rama `ui-lock`, 2026-09-01

Escrito para retomar. Dos commits sobre `portfolio-view`, nada empujado, nada
mergeado, y **el servidor no se ha actualizado** por indicación tuya.

```
6b5de28  Throughput on the dashboard, and a health dot in the project list
a9c458c  Ask for a password when the tool is opened, optional
5c3f808  (portfolio-view) Run the formatters the CI actually runs
```

La rama sale de `portfolio-view`, que va dos commits por delante de `main` y
sigue sin mergear. Si `portfolio-view` entra en `main` primero, esta rama queda
limpia detrás.

## Lo que sí está aplicado y no se puede deshacer sin trabajo

**La migración `a1c7f2e93b40` está corrida contra tu base real.** Se ejecutó
antes de que dijeras de no tocar el servidor. Añade `completed_at` y
`completed_at_estimated` a `tasks`, y rellenó las 64 tareas ya cerradas con
`completed_at = updated_at`, marcadas como estimadas. Comprobado:

| status | total | con fecha | estimadas |
|---|---|---|---|
| new | 102 | 0 | 0 |
| in_progress | 3 | 0 | 0 |
| done | 64 | 64 | 64 |

Si hiciera falta volver atrás: `alembic downgrade 3263ecb5dcb5` borra las dos
columnas y con ellas el relleno.

**La API ya sirve el código nuevo**, porque el servicio `api` monta
`./backend` con `--reload`. El endpoint `/api/metrics/throughput` responde ya.

**El frontend NO está actualizado.** El servicio `frontend` de docker compose no
monta nada: sirve el código horneado en la imagen. Para ver el bloqueo, las
tarjetas y el punto de color hay que reconstruirlo:

```bash
docker compose up -d --build frontend
```

Eso es lo que queda pendiente de tu permiso.

## Lo que quedó de la instancia

Sin bloqueo. Puse una contraseña desechable para el recorrido de verificación y
la quité al final: `GET /api/config/lock` devuelve `{"enabled": false}`.

## Lo hecho, en dos piezas

### 1. Bloqueo por contraseña (`a9c458c`)

Off por defecto. Se pone y se quita desde Ajustes. Cubre **la interfaz, no los
datos**: todas las rutas están detrás de la API key, y el servidor MCP, la
extensión y el launcher la tienen. Frena a quien se siente en tu máquina con el
navegador abierto. Convertirlo en frontera real significa sesión delante de cada
ruta y rompe esos tres clientes, así que es otra decisión.

- `backend/app/passwords.py`: scrypt de hashlib, sin dependencias nuevas.
  `verify_password` no lanza nunca.
- `backend/app/routers/config.py`: `GET /lock`, `POST /lock/verify`,
  `PUT /lock/password`, `DELETE /lock/password`, `PUT /lock/settings`.
- `password_hash` entra en los secretos redactados. Eso hace que el hash no
  llegue al navegador **y** que `restore_secrets` lo devuelva cuando Ajustes
  guarda el documento entero. Sin lo segundo, guardar cualquier ajuste escribía
  el placeholder encima del hash y ninguna contraseña volvía a abrir.
- Cambiar o quitar exige la contraseña actual.
- Recuperación si se olvida: está **en la propia pantalla de Ajustes**, al lado
  del campo, con el `docker compose exec` completo para borrar el bloque
  `security` de `storage/flowtrack.yaml`.
- Cliente: `LockScreen.svelte` y una puerta de tres estados en `+layout.svelte`.
  No pinta la app hasta que la API contesta. `unlocked` va en sessionStorage.

### 2. Dashboard (`6b5de28`)

- `completed_at` y su migración, mantenido solo en la transición.
- `backend/app/routers/metrics.py`: `GET /api/metrics/throughput?weeks=12`.
  Devuelve últimos 7 días, los 7 anteriores, cambio, tendencia con banda muerta,
  la serie semanal, y cuántas de las contadas son estimadas.
- Tarjetas en la home con número, delta y sparkline SVG sin dependencias, más la
  nota de cuántas fechas son estimadas.
- `projectHealth()` en `lib/utils.js`, con 13 tests. Umbrales: ámbar a los 21
  días sin actividad o a 14 días de la fecha objetivo, rojo a los 60 o pasada la
  fecha. Gris para `on_hold`, `deprecated` y archivados.
- Columna del punto en la tabla del portfolio. La de "última actividad" ya
  existía.

Sobre tus 30 proyectos reales: 1 rojo (Public Surface, un día pasado de fecha),
21 verdes, 8 grises, 0 desconocidos, 0 ámbar. El ámbar no sale porque la base
tiene dos semanas y todo lo activo se tocó hace menos de 16 días.

## Verificación

- Backend: **87 tests**, ruff check y format limpios.
- Frontend: **41 tests**, eslint y prettier limpios, build correcto. Verificado
  en un `node:22-slim` con el árbol de trabajo montado, no con
  `docker compose exec frontend`, que corre contra la imagen y me dio resultados
  de una copia vieja durante un rato.
- Recorrido en vivo del bloqueo: 12 comprobaciones contra la API en marcha.
- El recorrido en vivo del throughput encontró un bug que los tests no tenían:
  los buckets se alineaban a medianoche de hoy, así que lo cerrado durante el día
  caía en offset negativo y se descartaba. 64 con fecha, 45 contadas. Arreglado y
  con test.

## Pendiente

1. **Reconstruir el frontend** cuando digas: `docker compose up -d --build frontend`.
2. Mirar el bloqueo y el dashboard en pantalla. No puedo hacer capturas.
3. Decidir si esto va a `main` directo o por PR, y si antes entra
   `portfolio-view`.
4. El ámbar del semáforo no se ha visto con datos reales todavía. Los tests lo
   cubren, la vida aún no.
5. Un detalle preexistente que no toqué: una API key ausente da 422 y una
   incorrecta da 401, porque `Header(...)` valida antes de la dependencia. Es de
   toda la API, no de esto.

## Fuera de este repo

El post de LinkedIn de FlowTrack está en
`My Digital Projects/_content/flowtrack-li-post.md`, fuera del repo como
pediste. Inglés y español, con hashtags, y una tabla al final de dónde sale cada
dato. El ángulo son los dos campos que no tiene ningún otro gestor:
`abandonment_criteria` y el avance subjetivo al lado del calculado.
