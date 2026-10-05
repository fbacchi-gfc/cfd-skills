# Grid Convergence Index (GCI): Protocolo Detallado

**Ref**: Roache, P. J. "Verification and Validation in Computational Science and Engineering." (2009)

---

## 1. Concepto GCI

**Problema**: ¿Qué tan refinada es mi malla?

**Solución**: Ejecutar 3 mallas (gruesa, media, fina) y comparar convergencia.

**Métrica GCI**:
```
GCI_ij = F_s |ε_ij| / (r^p - 1) × 100%

donde:
  ε_ij = φ_i - φ_j    (diferencia entre soluciones)
  r = h_coarse/h_fine (factor refinamiento)
  p = orden precisión  (~2 para RANS 2nd order)
  F_s = 1.25          (factor seguridad)
```

**Interpretación**:
- **GCI < 5%**: Malla convergida, usar media
- **5% < GCI < 10%**: Aceptable, revisar sensibilidad
- **GCI > 10%**: Refinar (usar fina o modificar Δx/Δy)

---

## 2. Workflow: 3 Mallas

### 2.1 Generar Mallas

Usar factor de refinamiento `r = 1.5` (recomendado):

```
Malla Gruesa (coarse):
  h_coarse = h_medium × r
  Δy_coarse = Δy_medium × 1.5
  Δx_coarse = Δx_medium × 1.5
  # capas_coarse = # capas_medium / 1.5

Malla Media (medium):  [REFERENCIA]
  h_medium = tu especificación original
  Δy_medium, Δx_medium, # capas

Malla Fina (fine):
  h_fine = h_medium / r
  Δy_fine = Δy_medium / 1.5
  Δx_fine = Δx_medium / 1.5
  # capas_fine = # capas_medium × 1.5
```

**Ejemplo SD8020**:
```
Malla Media (referencia):
  Δy = 7.15e-5 m
  Δx = 7.15e-3 m
  # capas = 18

Malla Gruesa (r=1.5):
  Δy_c = 7.15e-5 × 1.5 = 1.07e-4 m
  Δx_c = 7.15e-3 × 1.5 = 1.07e-2 m
  # capas_c = 18 / 1.5 = 12

Malla Fina (r=1.5):
  Δy_f = 7.15e-5 / 1.5 = 4.77e-5 m
  Δx_f = 7.15e-3 / 1.5 = 4.77e-3 m
  # capas_f = 18 × 1.5 = 27
```

---

### 2.2 Ejecutar Simulaciones

Para cada malla (coarse, medium, fine):

1. **Setup Fluent**:
   - Importar malla
   - Configurar modelo turbulencia (RANS SST, etc.)
   - BCs: Inlet (U), outlet (P=0), wall (no-slip)
   - Modelos: viscous, standard gravity
   
2. **Inicialización**:
   ```
   Fluent > Initialization
   - Velocity: 0
   - Pressure: 0
   - Turbulent kinetic energy, omega: default
   ```

3. **Iteración**:
   - Residual target: < 1e-6 (continuidad, momentum)
   - Monitorear variable de interés:
     * C_L (lift coefficient)
     * C_D (drag coefficient)
     * Posición separación (x_sep)
     * Esfuerzo pared máximo (τ_w,max)
   - Iterate hasta convergencia (var. < 0.1% en 100 iteraciones)

4. **Recolectar datos**:
   ```
   φ_coarse, φ_medium, φ_fine
   
   Ejemplo (C_L):
   C_L,coarse = 0.8234
   C_L,medium = 0.8418
   C_L,fine   = 0.8501
   ```

---

## 3. Cálculo GCI

### 3.1 Paso 1: Diferenciales

```
ε_32 = φ_medium - φ_coarse  (medium vs fine? no, vs coarse)
ε_21 = φ_fine - φ_medium
```

**Ejemplo**:
```
ε_32 = 0.8418 - 0.8234 = 0.0184
ε_21 = 0.8501 - 0.8418 = 0.0083
```

### 3.2 Paso 2: Orden de Precisión (p)

```
p_est = ln((r32^p - 1) / (r21^p - 1)) / ln(r32 / r21)

donde r32 = h_coarse / h_medium = 1.5
      r21 = h_medium / h_fine = 1.5
```

Si r32 ≈ r21 ≈ 1.5:
```
p_est = ln((1.5^p - 1) / (1.5^p - 1)) / ln(1) → indeterminado

Usar p = 2.0 por defecto (RANS 2nd order)
```

### 3.3 Paso 3: GCI

```
GCI_21 = (F_s × |ε_21|) / (r^p - 1) × 100%
GCI_32 = (F_s × |ε_32|) / (r^p - 1) × 100%

F_s = 1.25 (factor seguridad recomendado)
r = 1.5
p = 2.0
```

**Ejemplo**:
```
GCI_21 = (1.25 × 0.0083) / (1.5^2 - 1) × 100%
       = (0.01038) / 1.25 × 100%
       = 0.83%  ← EXCELENTE (< 5%)

GCI_32 = (1.25 × 0.0184) / 1.25 × 100%
       = 1.47%  ← EXCELENTE
```

---

## 4. Validación Asintótica

Si GCI_21 / r^p ≈ GCI_32:
- Malla está en **rango asintótico** (convergencia cuadrática)
- Extrapolación confiable

```
φ_extrapolated = φ_fine + ε_21 / (r^p - 1)
                = 0.8501 + 0.0083 / 1.25
                = 0.8567
```

---

## 5. Recomendaciones

| GCI_21 | Decisión | Acción |
|--------|----------|--------|
| < 5% | ✓ ACEPTADO | Usar malla media, documentar |
| 5–10% | ⚠ REVISAR | Aceptable si variable no-crítica; usar fina si crítica |
| > 10% | ✗ RECHAZAR | Refinar: usar fina, incrementar Δx+, revisar dominio |

---

## 6. Workflow Iterativo

Si GCI > 10% en iteración N:

```
Iteración N:
├─ Malla Media (N)   → C_L,med(N) = 0.8418
├─ GCI(N) = 1.47%    → ACEPTADO
└─ Resultado: φ ≈ 0.8567 ± 0.0125

Iteración N+1 (si necesario refinar):
├─ Generar 3 mallas con Δy, Δx más finos
├─ Nueva Media(N+1) con h = h(N) / 1.3
├─ Ejecutar & comparar
└─ Calcular GCI(N+1)
```

---

## 7. Notas Implementación

### 7.1 Monitoreo en Fluent

**Crear función personalizada y+ en pared**:

```scheme
; En FLUENT journal script
(define monitor-yplus
  (lambda ()
    (cx-create-local-function
      "YPlus"
      (cx-model-function 'y+)
      '())))
```

Luego monitorear en cada iteración:
```
Fluent > Monitors > Create > Function
Name: yplus_avg
Function: Average(YPlus)@wall
Plot Yes
Report 100 iterations
```

### 7.2 Automatización Python

Script template para batch:

```python
import subprocess
import json

meshes = {
    "coarse": {"Δy": 1.07e-4, "Δx": 1.07e-2},
    "medium": {"Δy": 7.15e-5, "Δx": 7.15e-3},
    "fine":   {"Δy": 4.77e-5, "Δx": 4.77e-3},
}

results = {}

for mesh_type, params in meshes.items():
    # 1. Generar malla Gmsh
    # 2. Importar a Fluent (script journal)
    # 3. Iterar hasta convergencia
    # 4. Leer C_L, C_D, etc.
    
    results[mesh_type] = {
        "C_L": 0.8234,  # leer de Fluent output
        "tau_w_max": 2.45,
    }

# Calcular GCI
phi_c = results["coarse"]["C_L"]
phi_m = results["medium"]["C_L"]
phi_f = results["fine"]["C_L"]

epsilon_32 = phi_m - phi_c
epsilon_21 = phi_f - phi_m
r = 1.5
p = 2.0
F_s = 1.25

gci_21 = (F_s * abs(epsilon_21)) / (r**p - 1) * 100
gci_32 = (F_s * abs(epsilon_32)) / (r**p - 1) * 100

print(f"GCI_21 = {gci_21:.2f}%")
print(f"GCI_32 = {gci_32:.2f}%")
print(f"Recomendación: {'ACEPTADO' if gci_21 < 5 else 'REVISAR' if gci_21 < 10 else 'REFINAR'}")
```

---

## 8. Ejemplo Completo: SD8020

**Caso de estudio**:
- Re = 61,400
- ρ = 998 kg/m³
- L_char = 0.1 m
- Modelo: RANS SST
- Variable: C_L (coeficiente de sustentación)

### 8.1 Mallas Generadas

```
Malla Gruesa:
  Δy_c = 1.07e-4 m
  Δx_c = 1.07e-2 m
  # capas = 12
  Total nodos: ~45k

Malla Media (referencia):
  Δy_m = 7.15e-5 m
  Δx_m = 7.15e-3 m
  # capas = 18
  Total nodos: ~85k

Malla Fina:
  Δy_f = 4.77e-5 m
  Δx_f = 4.77e-3 m
  # capas = 27
  Total nodos: ~180k
```

### 8.2 Resultados Simulación

```
Iteración en Fluent: 2000 (residuales < 1e-6, C_L converged)

C_L,coarse = 1.2345
C_L,medium = 1.2687
C_L,fine   = 1.2801

Posición separación (x_sep/c):
sep,coarse = 0.245
sep,medium = 0.218
sep,fine   = 0.208
```

### 8.3 Cálculo GCI (para C_L)

```
ε_32 = 1.2687 - 1.2345 = 0.0342
ε_21 = 1.2801 - 1.2687 = 0.0114

r = 1.5, p = 2.0, F_s = 1.25

GCI_21 = (1.25 × 0.0114) / (1.5² - 1) × 100%
       = (0.01425) / 1.25 × 100%
       = 1.14%  ✓ ACEPTADO

GCI_32 = (1.25 × 0.0342) / 1.25 × 100%
       = 2.74%  ✓ ACEPTADO

Extrapolación:
φ_∞ = 1.2801 + 0.0114 / (1.5² - 1)
    = 1.2801 + 0.00912
    = 1.2892 ± 0.016
```

### 8.4 Reporte Final

```
╔═════════════════════════════════════════════════╗
║       GRID CONVERGENCE ANALYSIS (GCI)           ║
╚═════════════════════════════════════════════════╝

Variable: C_L
Refinement factor: r = 1.5
Scheme order: p = 2.0

Results:
  Coarse:   C_L = 1.2345
  Medium:   C_L = 1.2687  (REFERENCIA)
  Fine:     C_L = 1.2801

Convergence:
  ε_32 (coarse-medium) = 0.0342
  ε_21 (medium-fine)   = 0.0114
  Ratio ε_21/ε_32      = 0.333 ≈ r^(-2) = 0.444 ✓

GCI Analysis:
  GCI_32 = 2.74%
  GCI_21 = 1.14%
  GCI_21 / r^p = 0.61%  ← Asintótico

RECOMENDACIÓN: ✓ MALLA MEDIA ACEPTADA
  - Usar solución medium para producción
  - Incertidumbre estimada: ±1.14%
  - Valor recomendado: 1.289 ± 0.015

─────────────────────────────────────────────────
```

---

## Referencias

- Roache, P. J. "Quantification of Uncertainty in Computational Fluid Dynamics." Annual Review (2007)
- AIAA G-077-1998: "Guide for the Verification and Validation of Computational Fluid Dynamics Simulations"
