# RANS / DES / LES: Criterios de Malla Detallados

## Tabla Resumen Rápido

| Modelo | y⁺ Objetivo | Δx⁺ Región Sep. | Δx⁺ Attached | Δz⁺ | Propósito | Complejidad |
|--------|------------|-----------------|--------------|-----|----------|------------|
| **RANS SST** | 0.1–1.0 | 30–80 | 100–200 | N/A | Separación laminar, LSB | Media |
| **RANS k-ε** | 0.1–5.0 | 50–150 | 150–300 | N/A | Flujo general, industrial | Media |
| **RANS SA** | 0.5–2.0 | 40–100 | 100–250 | N/A | Aerodinámica, one-eq | Media |
| **DES DDES** | 0.1–1.0 | 50–100 | 20–50 | 15–30 | Separación transitoria | Alta |
| **DES IDDES** | 0.1–1.0 | 40–80 | 15–40 | 10–25 | Versión mejorada DDES | Alta |
| **LES Resolved** | 0.1–1.0 | 20–50 | 30–60 | 10–20 | Turbulencia de pared | Muy Alta |
| **LES WMLES** | 30–100 | 20–50 | 50–100 | 15–30 | Wall-modeled (ahorra nodos) | Alta |

---

## 1. RANS: Resolución Viscosa

### 1.1 SST k-ω (Recomendado para bajo Re)

**Rango y⁺**:
- Wall-resolved: **y⁺ < 1** (típico 0.5)
- Integra directamente en viscous sublayer
- Si y⁺ > 5, degradación de precisión en separación

**Criterios chordwise (Δx⁺)**:
- **Región de separación** (burbujas LSB, stall): Δx⁺ = 30–80
  - Más fino (~30–50) si LSB esperado
  - Captura vórtices contra-rotantes
- **Flujo attached**: Δx⁺ = 100–200
  - Región far downstream puede ser Δx⁺ = 200–400

**Número de capas boundary layer**:
- Desde y = Δy hasta y ≈ 0.2×L_char
- Ratio inflación ~ 1.2
- Número de capas: `n = log(0.2×L_char / Δy) / log(1.2)`
- Típico: 15–30 capas

**Aplicaciones típicas**:
- Airfoil bajo Re (Re < 200k)
- Laminar-turbulent transition
- Separación laminar (LSB)
- **Tu caso SD8020, NACA0012**: recomendado SST

---

### 1.2 k-ε Estándar / RNG

**Rango y⁺**:
- Mejor a y⁺ ~ 1 (wall functions menos sensibles que SST)
- Puede tolerar y⁺ hasta 5–10 sin degradación severa
- Menos recomendado para y⁺ < 0.1

**Criterios chordwise**:
- Región separación: Δx⁺ = 50–150
- Flujo attached: Δx⁺ = 150–300
- Menos sensible que SST a refinamiento chordwise

**Ventaja/Desventaja**:
- ✓ Robusto, industrial
- ✗ Pobre en separación laminar y transiciones
- ✗ Subestima separación en airfoils

---

### 1.3 Spalart-Allmaras (SA)

**Rango y⁺**:
- Óptimo: y⁺ = 0.5–2.0
- One-equation model: muy sensible a calidad de malla
- Requiere validación convergencia y⁺

**Criterios chordwise**:
- Separación: Δx⁺ = 40–100
- Attached: Δx⁺ = 100–250

**Aplicaciones**:
- Aerodinámica aeronaves
- Menor costo que SST pero más demandante que k-ε

---

## 2. DES: Detached Eddy Simulation (RANS/LES Híbrido)

### 2.1 DDES (Delayed DES)

**y⁺ objetivo**: 0.1–1.0 (igual RANS en pared)

**Estructura de malla**:
```
        ← Outer LES region (Δx⁺ = 20–50, Δz⁺ = 10–30)
    ────────────────────────────
   │ Transición (Δx⁺ = 50–100)   │
   │ (RANS→LES)                  │
   │ Shear layer                 │
    ────────────────────────────
   │ RANS (y⁺ < 1, 10–15 capas)  │
   │ viscous BL                  │
    ────────────────────────────
```

**Criterios**:
- **y⁺**: < 1 en pared
- **Δx⁺ en pared/separación**: 50–100 (aún RANS)
- **Δx⁺ en outer/LES region**: 20–50
- **Δz⁺**: 10–30 (crítico para vórtices longitudinales)

**Aplicaciones**:
- Separación dinámica (movimiento)
- Transiciones RANS→LES
- **Ejemplo**: airfoil en stall dinámico, cilindros, cavidades

---

### 2.2 IDDES (Improved DDES)

Versión mejorada de DDES (Spalart et al. 2006).

**Diferencias vs DDES**:
- Mejor transición RANS→LES
- Menos "Grey Area" (región donde ni RANS ni LES es claro)
- Requiere Δz⁺ ligeramente menor

**Criterios**:
- **y⁺**: < 1
- **Δx⁺ separación**: 40–80
- **Δx⁺ LES**: 15–40
- **Δz⁺**: 10–25 (más fino que DDES)

---

## 3. LES: Large Eddy Simulation

### 3.1 LES Wall-Resolved (WMLES = False)

**Filosofía**: Resolver todas las escalas hasta la pared.

**y⁺ objetivo**: < 1 (típico 0.1–0.5)
- Mayor resolución pared que RANS/DES
- Captura buffer layer y log-layer

**Criterios chordwise/spanwise** (Moin & Mahesh, 1998):
- **Δx⁺ ≈ 30–100** (separación ~20–40, attached ~50–100)
- **Δz⁺ ≈ 10–20** (crítico: vórtices streak)
- **Δy⁺ uniforme outer region**: 50–100 (después BL)

**Número de puntos pared→y+=100**:
- Típico: 20–50 puntos (mucho más que RANS/DES)

**Aplicaciones**:
- Transiciones laminares
- Shock-boundary layer interaction
- Flujos complejos con separación dinámica
- **Complejidad**: Muy alta (tiempo CPU 100–1000× RANS)

---

### 3.2 LES Wall-Modeled (WMLES)

**Filosofía**: Usar wall model en lugar de resolver hasta pared.

**y⁺ objetivo**: 30–100 (mucho más grueso)
- Ahorra 70–90% de nodos vs wall-resolved
- Compensa con modelo empírico en pared

**Criterios**:
- **Δx⁺ ≈ 20–50** (pared), luego 50–100 (outer)
- **Δz⁺ ≈ 15–30**
- **Δy outer region**: 50–150 (menos resuelto que wall-resolved)

**Modelos de pared típicos**:
- Werner-Wengle
- WALE (Wall-Adapting Local Eddy-viscosity)
- Vreman

**Ventaja/Desventaja**:
- ✓ 5–10× menos nodos que wall-resolved
- ✓ Tiempo CPU más manejable
- ✗ Menos preciso en transiciones y separación laminar
- ✗ Requiere validación contra experimento

**Aplicaciones**:
- Casos industriales donde wall-resolved prohibitivo
- Flujos de alto Re (Re > 10^6)

---

## 4. Ejemplo Numérico: SD8020 Re=61,400

**Datos**:
- L_char = 0.1 m (cuerda)
- ρ = 998 kg/m³ (water 20°C)
- μ = 1.002e-3 Pa·s
- U_inf ≈ 0.615 m/s
- τ_w ≈ 0.0486 Pa (Blausius)
- u_τ ≈ 0.00698 m/s

### 4.1 RANS SST

**Objetivo**: Capturar LSB, separación laminar

```
y+ = 0.5:
  Δy = (0.5 × 1.002e-3) / (998 × 0.00698) = 7.15e-5 m = 71.5 μm

Δx+ = 50:
  Δx = (50 × 1.002e-3) / (998 × 0.00698) = 7.15e-3 m = 7.15 mm

# capas BL (hasta 0.2L = 0.02 m):
  n = log(0.02 / 7.15e-5) / log(1.2) = 18
```

**Config JSON**:
```json
{
  "model": "rans-sst",
  "y_plus": 0.5,
  "delta_y_m": 7.15e-5,
  "n_layers": 18,
  "delta_x_separation": 7.15e-3,
  "delta_x_attached": 1.4e-2,
  "domain": {
    "upstream": 0.5,
    "downstream": 1.5,
    "height": 1.0
  }
}
```

---

### 4.2 DES IDDES

**Objetivo**: Dinámicas de separación, transiciones

```
y+ = 0.5 (igual RANS):
  Δy = 7.15e-5 m

Δx+ (pared/separación) = 60:
  Δx_sep = 8.6e-3 m

Δx+ (LES outer) = 30:
  Δx_les = 4.3e-3 m

Δz+ = 15:
  Δz = (15 × 1.002e-3) / (998 × 0.00698) = 2.14e-3 m
  → Lz (spanwise domain): ~0.05 m (24×Δz típico)
```

**Notas**:
- 3D obligatorio (spanwise)
- ~50% más nodos que RANS en chordwise
- Δz crítico para vórtices contra-rotantes

---

### 4.3 LES Wall-Resolved

```
y+ = 0.5:
  Δy = 7.15e-5 m

Δx+ = 25 (más fino para LES):
  Δx = 3.6e-3 m

Δy+ (outer region) = 50:
  Δy_outer = 7.15e-4 m
  → ~15 puntos desde y+=0.5 a y+=50

Δz+ = 12:
  Δz = 1.71e-3 m

# nodos pared: 50–100
# nodos chordwise: 200–400 (0.1 m domain / 3.6e-3 m)
# nodos spanwise: 30–60 (0.05 m / 1.71e-3 m)
Total: 5–10M nodos (10–100× RANS)
```

---

## 5. Resumen Decisión

**Usa RANS-SST si**:
- Re < 200k, bajo costo computacional
- Interés en separación laminar (LSB)
- GCI validation es requerido

**Usa DES-IDDES si**:
- Dinámicas de separación transitoria
- Transiciones RANS→LES
- Presupuesto computacional medio

**Usa LES si**:
- Altísima precisión requerida
- Transiciones laminares complejas
- Presupuesto computacional alto

---

## Referencias

- Menter, F. R., et al. "Two-equation eddy-viscosity turbulence models for engineering applications." AIAA J. 32.8 (1994)
- Spalart, P. R., et al. "A new version of the detached-eddy simulation code DESOIL." Bull. Eur. Assoc. Comput. Methods Appl. Sci. Eng. (2006)
- Moin, P., & Mahesh, K. "Direct numerical simulation: a tool in turbulence research." Annual review (1998)
