# Ejemplo Interactivo del Skill CFD Mesh Design

---

## Escenario: Diseño de Malla para SD8020 RANS-SST

### Input (Usuario → Widget)

```
┌─────────────────────────────────────────────────────────┐
│  CFD MESH DESIGN - FORMULARIO INTERACTIVO              │
└─────────────────────────────────────────────────────────┘

📊 PARÁMETROS FLUJO
├─ Reynolds (Re):           [61400]
├─ Longitud característica: [0.1]  (m)
├─ Fluido:                  [water ▼]
│  └─ Temperatura (°C):     [20]  (opcional, afecta aire)
│
├─ Propiedades detectadas:
│  ├─ ρ:    998 kg/m³
│  ├─ μ:    1.002e-3 Pa·s
│  └─ U_∞:  0.6165 m/s ✓

📐 PARÁMETROS MALLA
├─ Modelo turbulencia:     [rans-sst ▼]
│  └─ Wall treatment:       wall-resolved ✓
│
├─ Objetivo y+:            [0.5]
│  └─ Rango válido:        0.1–1.0 ✓
│
├─ Δx+ (chordwise):        [50]
│  └─ Región separación:   30–80 ✓
│
├─ Δz+ (spanwise):         [100]  (N/A para 2D, warning)
│
├─ Dominio:
│  ├─ Upstream (×L):       [5]
│  ├─ Downstream (×L):     [15]
│  └─ Altura/Ancho (×L):   [10]

🔍 VALIDACIONES EN TIEMPO REAL
├─ y+ = 0.5 para RANS-SST:  ✓ Viable
├─ Δx+ = 50 en separación:  ✓ Típico para LSB
├─ Dominio upstream = 5L:   ✓ Suficiente (mín. 3L)
├─ Dominio downstream:      ✓ Excelente (15L > 10L)
└─ Δz+ = 100 (2D):         ⚠ Ignorado en simulación 2D

[CALCULAR] [RESET]
```

---

### Output (Widget → Usuario)

```
┌─────────────────────────────────────────────────────────┐
│  RECOMENDACIONES DE MALLA - SD8020 RANS-SST            │
│  Generado: 2026-10-05 14:16:08                         │
└─────────────────────────────────────────────────────────┘

✓ PARÁMETROS CALCULADOS
════════════════════════════════════════════════════════

RESOLUCIÓN PARED (Boundary Layer)
├─ Δy (1er nodo):       2.225e-05 m = 22.25 μm
├─ y+ real:            0.5000 (objetivo 0.5) ✓
├─ # capas BL:         749
│  └─ Ratio inflación: 1.2 (típico)
├─ Cobertura BL:       Desde pared hasta 0.02 m (0.2×L)
│
└─ Escala de pared:
   ├─ τ_w:            0.508 Pa
   ├─ u_τ:            0.0226 m/s
   └─ Δy / η_K:       0.39 (< 1, bien resuelto)

RESOLUCIÓN CHORDWISE (Flujo)
├─ Δx (región LSB):    2.225e-03 m = 2.225 mm
│  └─ Δx+ = 50 ✓ (captura burbujas)
├─ Δx / L_char:       2.22% (fino, ~45 nodos en cuerda)
│
└─ Zona attached (opcional):
   ├─ Δx recomendado:  5e-03 m (Δx+ ~ 110)
   └─ Gradualmente → 1e-02 m (Δx+ ~ 220 far-field)

RESOLUCIÓN SPANWISE (Puede ignorarse para 2D)
├─ Δz:                4.449e-03 m
├─ Δz+:               100 (2D, N/A)
└─ Nota:              Si 3D dinámico, reducir a Δz+ = 20–30

DOMINIO COMPUTACIONAL
├─ Upstream:          0.500 m (5×cuerda)
├─ Downstream:        1.500 m (15×cuerda)
├─ Altura:            1.000 m (10×cuerda)
│
└─ Validaciones:
   ├─ Far-field dist.: 0.5 m (sufficiently far) ✓
   └─ Bloqueo (<5%):   ~2% (zona mojada/geom) ✓

════════════════════════════════════════════════════════

📊 GRÁFICOS Y DIAGRAMAS
════════════════════════════════════════════════════════

[Gráfico 1] Distribución y+ a lo largo de la pared
  
  y+ │
     │     ╱╲
   1 │────╱  ╲────────────────
   0.5│  ╱    ╲
     │ ╱       ╲
   0 │─────────────────────────→ x/c

[Gráfico 2] Altura primera capa vs dominio y

  y (m) │
        │ ════════════════════ 1.0 m (far-field)
    0.1 │ │ ─── Δy ─── Δy ─── │ Δy ~ 22 μm
   0.05 │ │                   │ 
   0.02 │ ├─ BL extent ─────── │ ~0.2 m
        │ │ ╭─ inflation ─╮   │ 
 0.001  │ │ │ ╭─ ╭─ ╭─    │   │ 
        │ └─┴─┴─┴──────────   │
        └──────────────────────→ geom

════════════════════════════════════════════════════════

⚙️  CONFIGURACIÓN FLUENT (Listo para copiar)
════════════════════════════════════════════════════════

SETUP RECOMENDADO:
  Solver:           Pressure-based, Steady/Unsteady
  Viscous model:    k-omega SST
  Wall treatment:   Wall-resolved (y+ < 1)
  
INLET:
  Type:             Velocity inlet
  U_normal:         0.6165 m/s
  Turbulent I:      1–2% (typical external flow)
  
OUTLET:
  Type:             Pressure outlet
  P_gauge:          0 Pa
  
WALL:
  Type:             No-slip
  Roughness:        Smooth (hydraulic smooth)
  
SOLVERS:
  Scheme:           QUICK o Central Differencing (2nd order)
  Residual target:  < 1e-6 (continuity, momentum)
  
MONITOREO:
  C_L (lift):       < 0.1% var / 100 iter
  τ_w_max (pared):  < 0.1% var / 100 iter
  y+ (validación):  Monitor en pared → avg y+ ~ 0.5 ✓

════════════════════════════════════════════════════════

📥 EXPORTAR & DESCARGAR
════════════════════════════════════════════════════════

[📄 Export JSON]        mesh_config.json (1.2 KB)
[📜 Fluent Notes]       fluent_notes.txt (3.5 KB)
[🔍 Debug Log]          debug.txt (2.1 KB)
[🐍 Python Script]      mesh_calc_reproducible.py (12 KB)

────────────────────────────────────────────────────────

[📋 Copiar Fluent Setup]    (al portapapeles)
[💾 Guardar como PDF]       (reporte completo)
[🔗 Compartir enlace]       (genera URL temporal)

════════════════════════════════════════════════════════

✅ PROTOCOLO GCI (RANS - AUTOMÁTICO)
════════════════════════════════════════════════════════

Como seleccionaste RANS-SST, se generan automáticamente
3 mallas para Grid Convergence Index:

  Malla Gruesa (r=1.5):    Δy = 3.34e-05 m, # capas = 499
  Malla Media (REF):       Δy = 2.22e-05 m, # capas = 749  ← TÚ AQUÍ
  Malla Fina (r=1.5):      Δy = 1.48e-05 m, # capas = 1124

WORKFLOW:
  1. Crear 3 mallas en Gmsh con parámetros arriba
  2. Ejecutar 3 simul. Fluent (convergencia cada una)
  3. Recolectar C_L, posición separación, etc.
  4. Script calcula GCI (ver fluent_notes.txt)
  5. Si GCI < 5% → malla media ACEPTADA ✓
  6. Si 5–10% → revisar sensibilidad
  7. Si > 10% → refinar (usar malla fina)

Ver: references/gci_protocol.md para detalles completos

════════════════════════════════════════════════════════
```

---

## Caso 2: Ajuste Rápido (DES IDDES)

Usuario modifica parámetros en el widget:

```
Cambio: Model rans-sst → des-iddes

┌─────────────────────────────────────────────────────────┐
│  VALIDACIONES ACTUALIZADAS - DES IDDES                 │
└─────────────────────────────────────────────────────────┘

⚠️  CAMBIOS DETECTADOS:
├─ Wall treatment:     wall-resolved → hybrid-rans-les
├─ Δx+ en separación:  30–80 → 40–80 (similar)
├─ Δx+ en LES outer:   N/A → 15–40 ✓ (NUEVO)
├─ Δz+ spanwise:       N/A → 10–25 ✓ (CRÍTICO AHORA)
└─ Requerimiento:      2D → 3D obligatorio ✓

🔴 WARNING: Δz+ = 100 fuera de rango DES (recomendado 10–25)
   Sugerencia: cambiar a [15]? [🔧 Auto-ajustar]

✓ Recalculando...

NUEVA ESPECIFICACIÓN:
├─ Δy:           2.225e-05 m (igual, pared wall-resolved)
├─ Δx sep:       2.225e-03 m (Δx+ = 50)
├─ Δx LES:       1.112e-03 m (Δx+ = 25, inner LES region)
├─ Δz:           3.375e-03 m (Δz+ = 15) ← ACTUALIZADO
├─ # capas BL:   749
│
└─ Total nodos estimado:
   ├─ 2D RANS:       ~85k
   └─ 3D DES:       ~2.5M (30× más, ~30× CPU)

⚠️  Nota: DES requiere 3D. Expandir dominio spanwise mín. 0.05 m

[CONFIRMAR CAMBIOS] [REVERTIR]
```

---

## Caso 3: Debug y Auditoría

Usuario hace clic en "Ver Logs Internos":

```
┌─────────────────────────────────────────────────────────┐
│  LOGS INTERNOS - SD8020 RANS-SST                       │
│  [Copiar] [Descargar] [Cerrar]                         │
└─────────────────────────────────────────────────────────┘

[DEBUG] Propiedades water:
  ρ = 998.0 kg/m³
  μ = 1.0020e-03 Pa·s

[DEBUG] Parámetros iniciales:
  Re = 61400, L_char = 0.1 m
  U_inf = 0.6165 m/s
  
[DEBUG] Fricción pared (Blausius):
  C_f = 0.00668
  τ_w = 0.508 Pa
  u_τ = 0.0226 m/s

[DEBUG] Escala de turbulencia:
  ν = 1.004e-6 m²/s
  η_K (Kolmogorov) = 5.64e-5 m
  θ (momentum) = 2.68e-4 m
  Re_θ = 164.5

[DEBUG] Dimensionamiento malla:
  Δy = 2.22e-5 m
  y+ = 0.5000 ✓
  # capas BL = 749
  Ratio inflación = 1.2
  Cobertura BL = 0.02 m ✓
  
  Δx = 2.22e-3 m
  Δx+ = 50
  Δx / L = 2.22% ✓
  
  Δz = 4.45e-3 m
  (Ignorado en 2D)

[INFO] Validaciones:
  ✓ y+ = 0.5 en rango RANS-SST (0.1–1.0)
  ✓ Δx+ = 50 en región separación (30–80)
  ✓ Dominio upstream = 5L > 3L
  ⚠ Δz+ = 100 ignorado (2D case)

[COMPLETE] Malla especificada exitosamente
```

---

## Entrada en Conversación

```
Usuario: "Necesito diseñar malla CFD para mi airfoil a bajo Re.
Es un SD8020, Re=61400 en agua, y me importa detectar LSB.
¿Qué me recomiendas? Quiero RANS-SST con GCI."

Claude [usando skill]:
"Voy a ayudarte a diseñar esa malla. Déjame usar el skill 
CFD Mesh Design para calcular parámetros óptimos.

[Widget interactivo se abre aquí]

Basado en tu caso:
- Re=61,400 (bajo), agua (998 kg/m³)
- RANS-SST: ideal para LSB en airfoil
- y+ = 0.5: resuelve viscous sublayer
- Δx+ = 50 en separación: captura burbujas contrarotantes

Resultados:
- Δy = 22.25 μm (1er nodo)
- 749 capas inflación (ratio 1.2)
- Δx = 2.22 mm en región LSB
- Dominio: 0.5 m upstream, 1.5 downstream, 1.0 altura
- ~85k nodos 2D esperados

Archivos listos:
- mesh_config.json (Gmsh/Salome)
- fluent_notes.txt (setup Fluent)
- GCI: automático 3 mallas para validación

¿Quieres ajustar algo? (y+, Δx+, modelo turbulencia, etc.)
¿O proceder a descargar config?"
```

---

## Casos Avanzados

### Ajuste Manual de y+ vs # de capas

```
Usuario: "No me importa y+, quiero exactamente 30 capas BL"

[Activa toggle: "Manual layer count"]

Δy = 0.02 m / 30 / 1.2 ≈ 5.56e-4 m
y+ resultante ≈ 12.5  ⚠ Fuera rango RANS-SST

[Widget alerta automáticamente]
"⚠ y+ = 12.5 > 1.0 (RANS-SST óptimo < 1).
 Con 30 capas, calidad de solución degradada.
 Sugerencia: aumentar capas a 150+, o usar y+ automático."
```

### Comparación Rápida Múltiples Modelos

```
Usuario: "Compárame RANS vs DES vs LES para este caso"

[Tab: "Comparación Rápida"]

╔════════════════╦═══════════╦════════════╦═══════════╗
║ Parámetro      ║  RANS-SST ║ DES-IDDES  ║ LES Res.  ║
╠════════════════╬═══════════╬════════════╬═══════════╣
║ Δy (mm)        ║  0.0223   ║  0.0223    ║  0.0223   ║
║ Δx (mm)        ║  2.22     ║  1.11–2.2  ║  1.11     ║
║ Δz (mm)        ║  N/A      ║  3.38      ║  1.71     ║
║ 3D?            ║  No       ║  Sí        ║  Sí       ║
║ # nodos (estim.)║ 85k      ║  2.5M      ║  10M      ║
║ CPU×           ║  1×       ║  30×       ║  100×     ║
║ LSB precision  ║  ✓✓✓      ║  ✓✓        ║  ✓✓✓✓     ║
║ Dinámicas      ║  Débil    ║  Buena     ║  Excelente║
║ GCI?           ║  Sí       ║  No        ║  No       ║
╚════════════════╩═══════════╩════════════╩═══════════╝

Recomendación para tu caso (LSB, bajo Re):
→ RANS-SST: Rápido, preciso, GCI validación
→ DES-IDDES: Si quieres dinámicas de desprendimiento
→ LES: Overkill para LSB estático, considera si Re > 200k
```

---

## Summary

**El skill proporciona**:
1. ✅ Widget interactivo (validaciones en tiempo real)
2. ✅ Cálculos detallados (τ_w, u_τ, η_K, etc.)
3. ✅ Múltiples exportos (JSON, notas Fluent, logs)
4. ✅ Protocolo GCI automático (RANS)
5. ✅ Debugging completo (ver logs internos)
6. ✅ Comparación rápida modelos
7. ✅ Reproducibilidad total (script Python)

**Diseñado para ser**:
- 🎯 Rápido (cálculos < 1 seg)
- 📊 Visual (gráficos, validaciones en tiempo real)
- 🔍 Transparente (logs internos siempre visibles)
- 🔧 Flexible (ajustes manuales permitidos con warnings)
- 📈 Escalable (agregar modelos, fluidos, criterios)
