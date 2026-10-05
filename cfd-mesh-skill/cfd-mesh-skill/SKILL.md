---
name: cfd-mesh-design
description: |
  Diseño de mallas CFD con especificación abierta de Δx+, Δy+, Δz+ para RANS/DES/LES. 
  Genera recomendaciones de refinamiento, valida y+ e integra protocolo GCI para RANS.
  Usa este skill cuando necesites planificar mallas: ingresa Re, tipo de fluido, modelo de turbulencia 
  y tus valores target de resolución → obtiene recomendaciones de y+, espesor de capas límite, tamaño de dominio, 
  espaciamiento en espacio homogéneo, validaciones y protocolo GCI. Exporta config Python, notas de integración Fluent.
compatibility: Python 3.8+, numpy, requests (opcional para propiedades dinámicas)
---

# CFD Mesh Design: RANS/DES/LES

Herramienta integral para diseño de mallas en aerodinámica de bajo Reynolds. Cálculo de espaciamiento 
basado en criterios físicos (fricción de pared, escala de Kolmogorov, separación), validación de calidad 
y protocolo GCI para RANS.

## Flujo de Uso

### Modo Interactivo (Widget)
1. Ingresa **parámetros base**: Re, fluido, longitud característica, dominio
2. Define **modelo de turbulencia** y **valores y+ / Δy / Δx+, Δz+ objetivo**
3. Widget genera: recomendaciones, validaciones, gráficos, export Python
4. Revisa logs internos (fricción de pared, escala de Kolmogorov, etc.)

### Modo Batch (Script Python)
```bash
python mesh_calculator.py \
  --re 100000 --fluid water --char-length 0.1 \
  --model rans-sst --y-plus 0.5 --deltax-plus 50 --deltaz-plus 50 \
  --domain-upstream 5 --domain-downstream 15 --domain-height 10 \
  --output mesh_config.json
```

Genera: 
- `mesh_config.json`: especificación completa
- `gci_protocol.txt`: reporte GCI (si RANS)
- `fluent_notes.txt`: pasos de integración Fluent UDF/journal
- `debug_log.txt`: valores internos (τ_w, u_τ, η_K, etc.)

---

## Parámetros de Entrada

### Flujo y Geometría
| Parámetro | Unidades | Ejemplo | Notas |
|-----------|----------|---------|-------|
| Re | - | 61400 | Basado en L_char |
| L_char (longitud característica) | m | 0.1 | cuerda airfoil, diámetro cilindro, etc. |
| Fluido | - | water, air, custom | Custom: ρ (kg/m³), μ (Pa·s) |
| T (temperatura, si aplica) | K | 293 | Para calcular μ dinámico de aire |
| Domain upstream | L_char | 5 | Distancia entrada→geometría |
| Domain downstream | L_char | 15 | Distancia geometría→salida |
| Domain height/width | L_char | 10 | Altura y ancho túnel/dominio |

### Turbulencia y Resolución

| Parámetro | Modelos | Rango Típico | Qué Significa |
|-----------|---------|--------------|---------------|
| **y⁺ (adimensional pared)** | RANS | 0.1–5 (wall-resolved) | Resolución en viscous sublayer |
| **Δy (1er nodo)** | RANS | - | Alternativa: # nodos normales a pared |
| **# nodos pared→0.2y** | RANS | 15–30 | Captura gradientes viscosos |
| **Δx⁺ (downstream)** | RANS/DES/LES | 50–200 (RANS), 50–100 (DES), 20–50 (LES) | Espaciamiento chordwise |
| **Δz⁺ (spanwise)** | RANS/DES/LES | 100–300 (DES), 10–30 (LES) | Resolución vórtices streamwise |

Parámetro **Δy⁺** (adimensional fricción):
- **u_τ = √(τ_w / ρ)** — velocidad de fricción
- **Δy⁺ = (ρ u_τ Δy) / μ**

---

## Modelos de Turbulencia: Criterios por Modelo

Lee `references/rans_des_les_criteria.md` para detalles. Resumen:

### RANS (SST, k-ε, SA)
- **y⁺ < 1**: wall-resolved (integración viscous sublayer)
- **Δx⁺ ≈ 50–200**: región de separación más fina (~50)
- **Δz⁺ ≈ 100–300**: 2D si no requiere, 3D si hay spanwise dynamics
- **GCI**: obligatorio (ver abajo)

### DES (DDES, IDDES)
- **y⁺ < 1** en pared (zona RANS)
- **Δx⁺ ≈ 50–100**: zona transicional
- **Δx⁺ ≈ 20–50**: LES outer region
- **Δz⁺ ≈ 10–30**: captura vórtices tipo Λ

### LES (dinámico, Vreman, Smag)
- **y⁺ < 1** (wall-resolved) o **30–100** (WMLES)
- **Δx⁺ ≈ 20–50**, **Δz⁺ ≈ 10–30**: criterio Moin & Mahesh
- **Δy⁺ uniforme** en LES outer region: típ. 50–100

---

## Protocolo GCI (RANS)

Si selecciona **RANS**, el skill genera automáticamente:

1. **Tres mallas**: gruesa (r=1.5), media, fina (r=1.5)
2. **Cálculo GCI** sobre variable monitorizada (C_L, separación, τ_w)
3. **Factor de seguridad** y **incertidumbre** en extrapolación
4. **Recomendación**: si GCI < 5%, malla media aceptada; si > 10%, refinar

Detalles en `references/gci_protocol.md` + exporta JSON listo para workflow Fluent.

---

## Output del Skill

### 1. Widget Interactivo
- Formulario: Re, fluido, modelo, Δy+, Δx+, Δz+, dominio
- **Validaciones en tiempo real**:
  - ¿y+ viable? (chequea τ_w contra viscosidad)
  - ¿Δx+, Δz+ consistentes con modelo?
  - ¿Dominio suficiente? (warning si upstream < 3×L)
- **Gráficos**:
  - Perfil de velocidad + capas límite
  - Distribución y+ a lo largo de pared
  - Malla 3D esquemática (cross-section)
- **Botones**: Export JSON, Export ICEM Notes, Export Fluent Notes, Ver logs

### 2. Script Python (mesh_calculator.py)
Ejecutable standalone; maneja:
- Propiedades de fluidos (aire 0–100°C, agua 0–40°C, custom)
- Cálculo de τ_w, u_τ, η_K (escala de Kolmogorov)
- Validaciones dimensionales
- Generación de config JSON para Gmsh/Salome/ICEM
- **Exporto ICEM CFD**: parámetros dimensionado (Global Size, Surface/Curve sizes, Inflation)
- **Exporto Fluent**: setup BCs, turbulencia, monitoreo
- GCI (3 mallas + reporte)
- Logs detallados

### 3. Exportos

| Archivo | Contenido | Para Quién |
|---------|-----------|-----------|
| `{prefix}.json` | y+, Δy, Δx+, layers, dominio, τ_w, u_τ | Script Gmsh, Salome, ICEM |
| `{prefix}_icem_notes.txt` | **Base size, Surface/Curve sizes, Inflation layers, refinement zones** | **Usuario ICEM CFD** |
| `{prefix}_fluent_notes.txt` | Setup turbulencia, BCs, monitoreo, convergencia | Usuario Fluent |
| `{prefix}_gci_protocol.txt` | 3 mallas, GCI, incertidumbre, recomendaciones | Documentación RANS |
| `{prefix}_debug.txt` | τ_w, u_τ, η_K, Re_θ, θ, H, validaciones | Auditoría y debugging |

---

## Integración con FLUENT

Ver `fluent_notes.txt` generado automáticamente. Resumen:

1. **UDF Hooks** (opcional):
   ```c
   // Monitor y_plus en tiempo real
   // Ejecutable en FLUENT UI con custom field function
   ```
   
2. **Journal Script**:
   ```scheme
   ;; Set up mesh, BCs, modelos turbulencia
   ;; lee mesh_config.json → aplica inflation layers, dominio, boundary conditions
   ```

3. **Post-Processing**:
   - Monitor τ_w, y+ en paredes
   - Validar GCI convergencia (si refinas iterativamente)

**Nota**: Requisitos Fluent específicos (versión, módulos) anotados en generación.

---

## Estructura Interna del Skill

```
cfd-mesh-skill/
├── SKILL.md (este archivo)
├── scripts/
│   ├── mesh_calculator.py          # motor principal
│   └── gci_utils.py                # cálculos GCI modularizados
├── references/
│   ├── rans_des_les_criteria.md    # tablas criterios por modelo
│   ├── gci_protocol.md             # detalles protocolo GCI
│   └── fluid_properties.json       # air, water 0-100°C
└── assets/
    └── fluent_template_journal.jou # template vacío para Fluent
```

---

## Notas de Debugging y Ampliación

### Debugging
- **Script**:  `python mesh_calculator.py --debug`  genera logs verbosos
- **Widget**: botón "Ver Logs Internos" muestra cada cálculo
- **Exporto** `debug_log.txt`: valores intermedios (τ_w, u_τ, y+, Re_τ, etc.)

### Ampliación Futura
1. **Integración MPC a Fluent** (UI Fluent → json → journal automático)
2. **Criterio de malla adaptiva** (refina automáticamente si error estimado > umbral)
3. **Soporte multi-body** (geometrías complejas, múltiples regiones)
4. **Validación contra base de datos experimental** (LSB en airfoil, etc.)
5. **Export Gmsh Python API** (en lugar de JSON, script gmsh directo)

Dejar código estructurado y modular para estas extensiones.

---

## Ejemplo Rápido

**Input**:
- Re = 61,400 (SD8020, 0.1 m cuerda, agua 20°C)
- Modelo: RANS-SST
- Objetivo: y+ = 0.5, detectar LSB
- Dominio: 5 cuerda upstream, 15 downstream, 10 altura

**Output** (widget + script):
- y⁺ recomendado: 0.47 ✓ (viable)
- Δy 1er nodo: 2.1 × 10⁻⁵ m
- # nodos pared→0.2y: 18 recomendado
- Δx⁺ región separación: 40 (más fino)
- Δx⁺ far-field: 150
- Δz⁺ (2D): N/A
- GCI convergence: factor = 1.3, recomendación "malla media OK, refinar bordes si LSB indefinido"
- Fluent notas: "Active near-wall treatment en SST, inflation 18 capas, tamaño base ~0.002 m"

---

## Contacto / Extensiones

El skill está diseñado para dejar visible **cada paso**: fórmulas, valores intermedios, decisiones. 
Si algo falla o necesitas variantes (geometrías curvas, efectos de compresibilidad), 
los logs + exports permiten auditoría y ajuste rápido.
