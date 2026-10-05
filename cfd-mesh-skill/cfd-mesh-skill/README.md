# CFD Mesh Design Skill

**Diseño integral de mallas RANS/DES/LES** con especificación abierta de Δy+, Δx+, Δz+ 
y protocolo GCI automático.

---

## Estructura del Skill

```
cfd-mesh-skill/
├── SKILL.md                              # Definición skill (instrucciones principales)
├── README.md                             # Este archivo
├── scripts/
│   └── mesh_calculator.py                # Motor de cálculo (CLI + batch)
├── references/
│   ├── rans_des_les_criteria.md          # Tablas criterios por modelo
│   ├── gci_protocol.md                   # Protocolo GCI detallado + ejemplos
│   └── fluid_properties.json             # Aire, agua (0-100°C)
└── assets/
    └── [templates Gmsh/journal Fluent, TBD]
```

---

## Uso Rápido

### 1. CLI Batch (Script Python)

```bash
# Caso base: SD8020 Re=61,400 agua
python scripts/mesh_calculator.py \
  --re 61400 \
  --fluid water \
  --char-length 0.1 \
  --model rans-sst \
  --y-plus 0.5 \
  --deltax-plus 50 \
  --deltaz-plus 100 \
  --domain-upstream 5 \
  --domain-downstream 15 \
  --domain-height 10 \
  --output sd8020_mesh

# Output: sd8020_mesh.json, sd8020_mesh_fluent_notes.txt, sd8020_mesh_debug.txt
```

**Parámetros**:

```
Flujo:
  --re INT                Reynolds (basado en L_char)
  --char-length FLOAT    Longitud característica (m)
  --fluid {water|air|custom}
  --T FLOAT              Temperatura (K, afecta viscosidad aire)
  --rho FLOAT            Densidad (custom)
  --mu FLOAT             Viscosidad dinámica (custom)

Malla:
  --model {rans-sst|rans-ke|rans-sa|des-ddes|des-iddes|les-resolved|les-wmles}
  --y-plus FLOAT         y+ objetivo (típ. 0.5 para RANS)
  --deltax-plus FLOAT    Δx+ chordwise (típ. 50–100 RANS, 20–50 DES/LES)
  --deltaz-plus FLOAT    Δz+ spanwise (opcional, típ. 15–30)
  --domain-upstream      Upstream en × L_char (default 5)
  --domain-downstream    Downstream en × L_char (default 15)
  --domain-height        Altura/ancho en × L_char (default 10)
  --n-layers INT         # capas BL (override automático si especificado)

Output:
  --output STRING        Prefix archivos salida (default "mesh_config")
  --debug                Verbose logs internos
```

---

### 2. Widget Interactivo (Uso en Claude)

Cuando invocas el skill en conversación:

```
Necesito diseñar malla CFD para airfoil SD8020 a Re=61,400 en agua.
Quiero RANS-SST, y+ = 0.5, detectar LSB.
```

**Widget muestra**:
1. **Formulario de entrada** (campos pre-rellenados o vacíos)
2. **Validaciones en tiempo real**:
   - ¿y+ viable para modelo seleccionado?
   - ¿Dominio suficiente?
   - Warnings si Δx+ incoherente
3. **Recomendaciones calculadas**:
   - Δy, # capas, Δx (regiones separación vs attached), Δz
   - Gráficos: perfil pared, distribución y+, esquema malla 3D
4. **Botones**:
   - Export JSON (para Gmsh/Salome)
   - Export Python (script reproducible)
   - Ver Logs Internos
   - Copiar Notas Fluent (copiar al portapapeles)

---

## Outputs Generados

### 1. `{prefix}.json`
Config estructurada para Gmsh/Salome/ICEM:
```json
{
  "metadata": {...},
  "flow": {"Re": 61400, "rho": 998, "mu": 0.001002, ...},
  "mesh": {"model": "rans-sst", "y_plus": 0.5, "deltax_plus": 50, ...},
  "specification": {
    "delta_y": 2.22e-5,
    "n_layers": 749,
    "delta_x": 2.22e-3,
    "domain_upstream": 0.5,
    ...
  }
}
```

Script Python puede leer esto y generar malla automáticamente.

### 2. `{prefix}_fluent_notes.txt`
Guía paso-a-paso Fluent:
- Parámetros malla (Δy, # capas, Δx, Δz)
- Setup modelos (SST, k-ε, etc.)
- Boundary conditions (inlet U, outlet P, wall)
- Monitoreo y convergencia
- Si RANS: recomendaciones GCI

**Listo para copiar-pegar en workflow**.

### 3. `{prefix}_debug.txt`
Log detallado de cálculos:
```
U_inf = 0.6165 m/s
τ_w = 0.5082 Pa
u_τ = 0.0226 m/s
η_K = 5.64e-5 m
Δy = 2.22e-5 m
y+ = 0.5
Δx/L_char = 2.22%
...
```

Para auditoría y debugging.

---

## Ejemplos de Uso

### Caso 1: NACA0012 RANS-SST con LSB

```bash
python scripts/mesh_calculator.py \
  --re 100000 \
  --fluid air \
  --char-length 1.0 \
  --model rans-sst \
  --y-plus 0.5 \
  --deltax-plus 30 \
  --deltaz-plus 200 \
  --domain-upstream 5 \
  --domain-downstream 20 \
  --domain-height 15 \
  --output naca0012_rans
```

**Interpretación**:
- y+ = 0.5 ✓ (muy resuelto, SST estará contento)
- Δx+ = 30 → región separación muy fina (captura burbujas)
- Δz+ = 200 → 2D (ignorado en 2D, but 3D si necesario)
- Dominio grande (far-field efectivo)

### Caso 2: Placa Plana DES IDDES (3D transitorio)

```bash
python scripts/mesh_calculator.py \
  --re 100000 \
  --fluid water \
  --char-length 0.5 \
  --model des-iddes \
  --y-plus 0.5 \
  --deltax-plus 50 \
  --deltaz-plus 20 \
  --domain-upstream 3 \
  --domain-downstream 10 \
  --domain-height 8 \
  --n-layers 20 \
  --output placa_des
```

**Interpretación**:
- 3D obligatorio (Δz+ especificado)
- y+ = 0.5 en pared (RANS wall layer)
- Δx+ = 50 en pared (transición RANS→LES)
- Δz+ = 20 (captura vórtices longitudinales)
- --n-layers 20 override → exactly 20 capas (vs automático)

### Caso 3: Cilindro LES Wall-Modeled (presupuesto bajo)

```bash
python scripts/mesh_calculator.py \
  --re 3900 \
  --fluid air \
  --char-length 0.1 \
  --model les-wmles \
  --y-plus 50 \
  --deltax-plus 30 \
  --deltaz-plus 15 \
  --domain-upstream 3 \
  --domain-downstream 20 \
  --domain-height 12 \
  --output cilindro_les_wmles
```

**Interpretación**:
- y+ = 50 (wall-modeled, ya no resuelve viscous sublayer)
- Δx+, Δz+ más gruesos que LES wall-resolved
- Ahorra 80% de nodos vs wall-resolved LES
- Wall model (WALE, etc.) maneja esfuerzo pared

---

## Validaciones Internas (Automáticas)

El script valida automáticamente:

1. **y+ coherente con modelo**:
   - RANS: y+ 0.1–5 typical, warning si fuera rango
   - DES: y+ 0.1–1
   - LES wall-resolved: y+ 0.1–1
   - LES wall-modeled: y+ 30–100

2. **Δx+, Δz+ coherentes**:
   - RANS: Δx+ 30–200, no Δz+ (2D typical)
   - DES: Δx+ 20–100, Δz+ 10–30 (3D)
   - LES: Δx+ 20–50, Δz+ 10–20 (altísima resolución)

3. **Dominio suficiente**:
   - Warning si upstream < 3×L_char
   - Warning si downstream < 10×L_char
   - Warning si height < 5×L_char

4. **Escala de Kolmogorov**:
   - LES: Δy << η_K (warning si mayor)
   - RANS/DES: no crítico (no resuelve Kolmogorov)

---

## Protocolo GCI (RANS)

Si modelo = RANS*, el script marca como "requires_gci = True".

**Workflow**:
1. Script genera 3 mallas automáticamente:
   - Coarse: h × 1.5
   - Medium: h (tu especificación)
   - Fine: h / 1.5

2. Usuario ejecuta 3 simulaciones Fluent
3. Recolecta: C_L, C_D, posición separación, etc.
4. Calcula GCI (Roache protocol)
5. Recomendación: ACEPTADO (<5%), REVISAR (5-10%), REFINAR (>10%)

**Exporto automático** (`_fluent_notes.txt`) incluye:
- Parámetros de 3 mallas
- Instrucciones cálculo GCI
- Template Python para automatizar

Ver `references/gci_protocol.md` para detalles completos.

---

## Debug y Ampliación

### Debugging

**Flag `--debug`**:
```bash
python mesh_calculator.py ... --debug
```

Imprime en stdout:
- U_inf, τ_w, u_τ, viscosidad cinemática
- y+, Δy, # capas, Δx, Δz
- Validaciones paso a paso

**Archivo `_debug.txt`**:
Exporto automático con todos los valores intermedios.
Útil para auditoría o reproducibilidad.

### Ampliaciones Futuras

Script está modularizado para permitir:

1. **Nuevos modelos de turbulencia**:
   - Agregar entrada en `TURBULENCE_CRITERIA` dict
   - Definir y+, Δx+, Δz+ ranges

2. **Fluidos adicionales** (aceite, sal, custom):
   - Extender `FLUID_PROPERTIES` dict
   - Usar propiedades dinámicas (tablas/API)

3. **Criterios avanzados**:
   - Escala de Kolmogorov (LES)
   - Número de Larmor (compresible)
   - Shock-capturing (compresible)

4. **Exporto directo Gmsh/Salome**:
   - JSON → script Python Gmsh
   - Generar malla automática

5. **Integración MCP Fluent**:
   - Lectura directa y+ desde simulación
   - GCI cálculo automático post-convergencia

---

## Consideraciones de Uso

### 1. Resolución "Mínima" vs "Ideal"

Script calcula **mínimo viable** para modelo dado. Si recursos limitados:

```
RANS SST: Δy mínimo
DES: Δx+, Δz+ mínimo
LES: Δy, Δx+, Δz+ muy fino → muy costoso
```

**Recomendación**: Empezar con RANS, validar, luego DES si dinámicas importantes.

### 2. Sensibilidad de Modelos

- **RANS**: Sensible a Δx+ (región separación), menos a Δz+ (2D)
- **DES**: Crítico Δz+ y transición RANS→LES layer
- **LES**: Crítico Δy, Δx+, Δz+ uniformes (isotrópico cuanto sea posible)

### 3. Costo Computacional

Aproximadamente:
- RANS: 1× CPU (baseline)
- DES: 5–20× CPU (mayor dominio, 3D)
- LES wall-resolved: 100–1000× CPU (mucho más fino)
- LES wall-modeled: 20–50× CPU (intermedio)

---

## Flujo Típico Completo

```
1. Usuario dice: "Diseña malla para SD8020 LSB a Re=61,400"
   ↓
2. Claude invoca skill
   ↓
3. Skill abre widget (formulario interactivo)
   - Pre-rellena: Re, L_char, fluido, modelo desde contexto
   - Usuario confirma/ajusta valores
   ↓
4. Skill ejecuta mesh_calculator.py
   ↓
5. Genera salida:
   - mesh_config.json (Gmsh/Salome)
   - fluent_notes.txt (workflow Fluent)
   - debug.txt (auditoría)
   ↓
6. Widget muestra recomendaciones + gráficos
   - Δy, # capas, Δx, Δz
   - y+ válido ✓
   - Warnings si aplica
   ↓
7. Usuario descarga JSON / copia Fluent notes
   ↓
8. Usuario crea malla en Gmsh, importa a Fluent
   ↓
9. Fluent: setup BCs, iterate hasta convergencia
   ↓
10. Si RANS: calcular GCI (3 mallas)
    ↓
11. Validar y+, separación, variables de interés
    ↓
12. Post-procesamiento y análisis
```

---

## Notas Finales

- **Logs internos siempre disponibles**: Ver `_debug.txt` para auditoría
- **Modular y extensible**: Fácil agregar modelos, fluidos, criterios
- **Validaciones automáticas**: No saldrá del "rango físico"
- **Reproducible**: JSON + script permiten regenerar exactamente

¡Listo para usar! 🚀

---

## Contacto / Soporte

Skill creado en colaboración con Fdk (CFD researcher, bajo Reynolds).
Casos base: SD8020 LSB, NACA0012, placa plana GCI.

Para preguntas, extensiones, o reporte de bugs:
- Revisar logs internos (`_debug.txt`)
- Consultar referencias (`rans_des_les_criteria.md`, `gci_protocol.md`)
- Proponer ampliaciones modulares manteniendo estructura actual
