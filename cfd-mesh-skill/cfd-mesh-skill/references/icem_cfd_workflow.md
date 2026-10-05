# ICEM CFD: Workflow Generación Malla desde Parámetros

**De**: Skill CFD Mesh Design  
**Para**: Usuario generando malla en ICEM CFD (unstructured/hybrid)

---

## 1. Overview

Script `mesh_calculator.py` exporta `*_icem_notes.txt` con parámetros listos para ingresar en ICEM.

**Flujo**:
1. Ejecutar `mesh_calculator.py` → genera `{case}_icem_notes.txt`
2. Copiar parámetros (Global Size, Surface Size, Inflation, etc.)
3. Ingresar en ICEM UI
4. Generar malla
5. Exportar a Fluent (.cas)

---

## 2. Estructura de Parámetros Exportados

```
{case}_icem_notes.txt contiene:

GLOBAL:
  Base size          → Tamaño far-field
  
LOCAL SURFACES:
  Airfoil surface    → Δx en superficie
  LE curve           → Δx en leading edge (fino)
  Trailing edge      → Δx en TE
  
LOCAL CURVES:
  Airfoil perimeter  → Δx sobre contorno
  Far-field          → Coarse edges
  
INFLATION:
  First height       → Δy (1er nodo)
  # layers           → Número de capas
  Growth ratio       → Expansión (típ. 1.2)
  
DOMINIO:
  Upstream/Downstream/Height → Límites computacionales

ESTIMACIÓN DE NODOS
  Rango total 2D/3D esperado
```

---

## 3. Paso-a-Paso en ICEM

### 3.1 Setup Inicial

```
File > Open > airfoil.iges (o .step)
```

**Verificar**:
- Geometría importada correctamente
- Escala en metros (no mm)
- Airfoil cerrado (no gaps)

### 3.2 Crear Dominio Computacional

**Opción A: Crear box y restar geometría (recomendado)**

```
Geometry > Primitive > Box
  Width (upstream + downstream):  X_upstream + X_downstream
  Height:                         Y_height
  Depth (3D):                     Z_depth (si 3D)
  → Click OK
  
Geometry > Boolean > Subtract
  Tools > Select airfoil
  Shape > Select box
  → Resta airfoil del dominio
```

**Opción B: Usar CAD directo**

Si geometría CAD ya tiene dominio definido:
```
Geometry > Import > (malla CAD con dominio)
```

### 3.3 Asignar Tamaños (Global)

```
ICEM UI → Mesh menu → Global Size

Input: [base_size desde icem_notes.txt]
Ejemplo: 2.0e-02 m
```

Este tamaño afecta **todo el dominio far-field**.

### 3.4 Tamaños Locales en Superficies

```
Geometry > Surfaces > Select

Para cada superficie:
1. Upper surface:
   Properties > Mesh Size > [surface_size]
   Ejemplo: 1.78e-03 m
   
2. Lower surface:
   Ídem
   
3. (Si cilindro: wall surface)
   Ídem
```

### 3.5 Tamaños Locales en Curvas

```
Geometry > Curves > Select

1. Leading Edge (crítico):
   Properties > Mesh Size > [curve_size_le]
   Ejemplo: 1.11e-03 m
   Checkbox: "Mesh along curve" → ON
   
2. Trailing Edge:
   Mesh Size > [delta_x]
   Ejemplo: 2.22e-03 m
   
3. Airfoil perimeter:
   Mesh Size > [delta_x]
   
4. Far-field outer boundary:
   Mesh Size > [base_size × 2]
   (Coarse para eficiencia)
```

### 3.6 Inflation Layers (Boundary Layer)

```
Mesh > Inflation > New Inflation

1. Select surface:
   → Click airfoil wall surface
   
2. Configuration:
   First height (Δy):       2.22e-05 m
   Number of layers:        749
   Growth ratio:            1.2
   
   ✓ Smooth transition      (marcar)
   
3. Apply
```

**Si ICEM alerta "layers too thick"**:
- Opción 1: Aumentar growth_ratio a 1.3
- Opción 2: Reducir # layers a 500–600 (menos resolución)
- Opción 3: Aumentar first height (menos fino)

### 3.7 Refinement Zones (Opcional pero Recomendado)

**Para detectar separación (LSB)**:

```
Mesh > Refinement > New Refinement

1. Type: Box refinement
2. Create box:
   → Ubicación: zona esperada LSB (x/c ≈ 0.3–0.6)
   → Tamaño: Δx × 0.7 (más fino)
   
3. Max distance from surface: Δy × 5
   (Captura gradientes cercanos)

4. Apply
```

**Para wake**:

```
Mesh > Refinement > New Refinement

1. Type: Box refinement
2. Ubicación: downstream del airfoil
3. Size: Δx × 1.5
4. Aplicar
```

---

## 4. Generar Malla

```
Mesh > Mesh Computation

1. Select mesh type:
   ☑ Unstructured (tetrahedra, standard)
   ☐ Hybrid (prism + tet, mejor para BL pero más lento)
   
2. Advanced:
   Growth rate (inflation→far-field): 1.2
   Min angle: 20°
   
3. Compute
   → ICEM genera malla
   → Muestra total de elementos
```

**Validar resultado**:
```
Mesh > Quality > Check
  ✓ Element count: ~85k–150k (2D)
  ✓ Min angle: > 20° (OK)
  ✓ Max aspect ratio: aceptable (~1000 en BL es normal)
```

---

## 5. Boundary Conditions & Exports

### 5.1 Nombrar Boundaries (Importante para Fluent)

```
Mesh > Boundary Conditions

1. Inlet:
   Select surface → Name "inlet"
   
2. Outlet:
   Select surface → Name "outlet"
   
3. Symmetry (top/bottom sides):
   Name "symmetry_top", "symmetry_bottom"
   
4. Wall (airfoil):
   Name "wall"
   
5. (si 3D con periodic):
   Select periodic pair → Name "periodic_1", "periodic_2"
```

### 5.2 Exportar a Fluent

```
File > Export > Fluent Case

Output: case_name.cas
ICEM automáticamente:
  ✓ Exporta malla (grid + elementos)
  ✓ Exporta boundary names
  ✓ Listo para abrir en Fluent
```

---

## 6. Verificación Pre-Fluent

**Checklist antes de importar a Fluent**:

- [ ] Malla generada exitosamente
- [ ] # de nodos esperado (±10%)
- [ ] Calidad elementos OK (ángulos > 20°)
- [ ] Inflation layers presentes (y+)
- [ ] Boundaries nombrados
- [ ] Archivo .cas exportado

**Inspeccionar en ICEM**:
```
Mesh > Display > Show elements
  → Verificar visualmente refinamiento en LE
  → Verificar inflation layers en pared
```

---

## 7. Problemas Comunes & Soluciones

| Problema | Causa | Solución |
|----------|-------|----------|
| "Inflation too thick" | Layers muy grandes | ↑ growth_ratio a 1.3 o ↓ layers |
| "Surface mesh fails" | Tamaño base muy grande | ↓ base_size 50% |
| "Bad elements at LE" | Curve size muy fino | ↑ curve_size_le a Δx |
| "Aspect ratio huge" | Normal en BL | OK si < 10,000 |
| "2D queda muy grueso" | Base size demasiado coarse | ↓ base size × 0.5 |
| "Tarda mucho a generar" | Malla muy fina | ↑ base_size, ↓ layers |

---

## 8. Estimación Rápida de Nodos

**2D**:
```
Far-field: (Upstream + Downstream) × Height / base_size² ÷ 2
BL:        L_char × (sum de inflación) / (Δx × Δy)
Total:     Far-field + BL + Refinements

Típico para Re=61,400, Δx+=50:
  ~85k–150k elementos 2D
```

**3D** (spanwise = 0.05 m, Δz = 3.4e-3 m):
```
Total 3D ≈ Total 2D × (Lz / Δz)
        ≈ 120k × 15 ≈ 1.8M elementos
```

---

## 9. Variantes & Opciones Avanzadas

### Hybrid Mesh (Prism + Tet)

**Ventaja**: Mejor resolución BL, elemento prism alinea con flujo  
**Desventaja**: Más lento a generar

```
Mesh > Mesh Computation
  ☐ Unstructured
  ☑ Hybrid prisms
  
Prism properties:
  ✓ Prism in inflation layers
  Height: Δy
  Layers: # capas
```

### 3D con Periodicidad (Para LSB Dinámico)

```
Geometry > Create periodic BC
  Surface 1: bottom (z=0)
  Surface 2: top (z=Lz)
  
Lz = 0.1×L_char (pequeño para ahorrar nodos)

ICEM automáticamente etiqueta como "periodic_1", "periodic_2"
Fluent: Configure como Periodic-Rotational offset=0
```

### Refinement Adaptativo (Iterativo)

Después de corrida inicial Fluent:

1. Identifica zona de alto error (ej. separación)
2. Regresa a ICEM, agrega refinement zone
3. Re-genera malla, re-ejecuta
4. Valida con GCI si RANS

---

## 10. Integración con Fluent

Una vez exportado `case.cas` desde ICEM:

```
Fluent:
  File > Open > case.cas
  
Automáticamente carga:
  ✓ Malla (elementos, nodos)
  ✓ Boundary types (inlet, outlet, wall, sym)
  
Luego:
  1. Modelos turbulencia (SST, k-ε, LES, etc.)
  2. Materiales (water, air)
  3. Convergencia según fluent_notes.txt
```

---

## Referencias Rápidas

**Documentación**:
- ANSYS ICEM CFD User Guide (online docs)
- `{case}_icem_notes.txt` (parámetros auto-generados)
- `references/rans_des_les_criteria.md` (criterios malla)

**Validación**:
- `{case}_debug.txt` (valores internos calculados)
- ICEM Quality Check (antes de exportar)
- GCI (si RANS, en Fluent post-convergencia)
