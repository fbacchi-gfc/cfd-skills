#!/usr/bin/env python3
"""
CFD Mesh Design Calculator
RANS/DES/LES aerodynamic mesh generation with GCI protocol

Uso:
  python mesh_calculator.py --re 61400 --fluid water --char-length 0.1 \\
    --model rans-sst --y-plus 0.5 --deltax-plus 50 --deltaz-plus 100 \\
    --domain-upstream 5 --domain-downstream 15 --domain-height 10 \\
    --output mesh_config.json

Debug:
  python mesh_calculator.py ... --debug

Propiedades fluido:
  --fluid water | air | custom --rho 1000 --mu 0.001
"""

import json
import argparse
import math
from dataclasses import dataclass, asdict
from typing import Dict, Optional, Tuple
from datetime import datetime
import sys

# ============================================================================
# PROPIEDADES FLUIDO
# ============================================================================

FLUID_PROPERTIES = {
    "water": {
        "T_ref": 293.15,  # K (20°C)
        "rho": 998.0,      # kg/m³
        "mu": 1.002e-3,    # Pa·s
        "sources": "ISO 20°C",
        "range_T": (273, 313)  # 0–40°C
    },
    "air": {
        "T_ref": 288.15,   # K (15°C)
        "rho": 1.225,
        "mu": 1.789e-5,
        "sources": "ISO 15°C, 101.325 kPa",
        "range_T": (273, 373)  # 0–100°C
    }
}

def get_fluid_properties(fluid: str, T: Optional[float] = None, 
                         rho: Optional[float] = None, 
                         mu: Optional[float] = None) -> Dict:
    """
    Obtiene propiedades de fluido. Si custom, requiere rho y mu.
    T en Kelvin afecta μ de aire (Sutherland).
    """
    if fluid in FLUID_PROPERTIES:
        props = FLUID_PROPERTIES[fluid].copy()
        # Ajuste temperatura aire (Sutherland)
        if fluid == "air" and T is not None:
            T_ref = props["T_ref"]
            mu_ref = props["mu"]
            S = 110.4  # Sutherland constant (K)
            mu_T = mu_ref * ((T / T_ref) ** 1.5) * (T_ref + S) / (T + S)
            props["mu"] = mu_T
            props["T"] = T
        return props
    elif fluid == "custom":
        if rho is None or mu is None:
            raise ValueError("Fluido custom requiere --rho y --mu")
        return {"rho": rho, "mu": mu, "sources": "user-defined"}
    else:
        raise ValueError(f"Fluido desconocido: {fluid}")

# ============================================================================
# CRITERIOS TURBULENCIA
# ============================================================================

TURBULENCE_CRITERIA = {
    "rans-sst": {
        "name": "RANS SST k-ω",
        "y_plus_target": (0.1, 1.0),
        "deltax_plus_separation": (30, 80),      # Región separación
        "deltax_plus_attached": (100, 200),      # Región attached
        "deltaz_plus_2d": None,                  # N/A
        "wall_treatment": "wall-resolved",
        "requires_gci": True,
        "notes": "Integración viscous sublayer; near-wall treatment en Fluent"
    },
    "rans-ke": {
        "name": "RANS k-ε",
        "y_plus_target": (0.1, 5.0),
        "deltax_plus_separation": (50, 150),
        "deltax_plus_attached": (150, 300),
        "deltaz_plus_2d": None,
        "wall_treatment": "wall-resolved",
        "requires_gci": True,
        "notes": "Wall functions a y+~1; revisar convergencia"
    },
    "rans-sa": {
        "name": "RANS Spalart-Allmaras",
        "y_plus_target": (0.5, 2.0),
        "deltax_plus_separation": (40, 100),
        "deltax_plus_attached": (100, 250),
        "deltaz_plus_2d": None,
        "wall_treatment": "wall-resolved",
        "requires_gci": True,
        "notes": "Sensible a malla; validar convergencia y+ < 1"
    },
    "des-ddes": {
        "name": "DES DDES",
        "y_plus_target": (0.1, 1.0),
        "deltax_plus_separation": (50, 100),     # zona transicional
        "deltax_plus_attached": (20, 50),        # LES outer
        "deltaz_plus_2d": (15, 30),
        "wall_treatment": "hybrid-rans-les",
        "requires_gci": False,
        "notes": "Δx+ decrece en outer region; captura vórtices λ"
    },
    "des-iddes": {
        "name": "DES IDDES",
        "y_plus_target": (0.1, 1.0),
        "deltax_plus_separation": (40, 80),
        "deltax_plus_attached": (15, 40),
        "deltaz_plus_2d": (10, 25),
        "wall_treatment": "hybrid-rans-les",
        "requires_gci": False,
        "notes": "Variante mejorada DDES; sensible a ΔLES"
    },
    "les-resolved": {
        "name": "LES wall-resolved",
        "y_plus_target": (0.1, 1.0),
        "deltax_plus_separation": (20, 50),
        "deltax_plus_attached": (30, 60),
        "deltaz_plus_2d": (10, 20),
        "wall_treatment": "resolved",
        "requires_gci": False,
        "notes": "Altísima resolución; validar CFL << 1 para time-stepping"
    },
    "les-wmles": {
        "name": "LES wall-modeled",
        "y_plus_target": (30, 100),
        "deltax_plus_separation": (20, 50),
        "deltax_plus_attached": (50, 100),
        "deltaz_plus_2d": (15, 30),
        "wall_treatment": "wall-modeled",
        "requires_gci": False,
        "notes": "Ahorra nodos pared; usa wall model (WALE, Vreman)"
    }
}

# ============================================================================
# DATACLASSES
# ============================================================================

@dataclass
class FlowParams:
    """Parámetros de flujo y geometría"""
    Re: float
    L_char: float
    rho: float
    mu: float
    fluid_name: str
    T: Optional[float] = None

@dataclass
class MeshParams:
    """Parámetros de malla objetivo"""
    model: str
    y_plus: float
    deltax_plus: float
    deltaz_plus: Optional[float] = None
    domain_upstream: float = 5
    domain_downstream: float = 15
    domain_height: float = 10
    n_layers_bl: Optional[int] = None  # Si no Δy, # de capas

@dataclass
class MeshSpec:
    """Especificación calculada de malla"""
    y_plus_actual: float
    delta_y: float
    delta_x_plus: float
    delta_x: float
    delta_z_plus: Optional[float]
    delta_z: Optional[float]
    n_layers: int
    domain_upstream: float
    domain_downstream: float
    domain_height: float
    # Valores intermedios
    tau_wall: float
    u_friction: float
    kolmogorov_scale: float
    theta: float  # momentum thickness
    H: float     # shape factor
    reynolds_theta: float
    warnings: list

# ============================================================================
# CÁLCULO DE ESFUERZO DE PARED (Blausius para placa plana)
# ============================================================================

def skin_friction_coefficient(Re_L: float, model: str = "blasius") -> float:
    """
    C_f a partir de Re_L (basado en longitud característica).
    Blausius: para flujo laminar, Re < 5×10^5
    Schoenherr: transicional/turbulento, Re > 5×10^5
    """
    if model == "blasius":
        return 0.664 / math.sqrt(Re_L)
    elif model == "schoenherr":
        return 0.427 / (math.log(Re_L) - 0.407) ** 2
    else:
        # Promedio para rango medio
        return 0.027 / (Re_L ** 0.14)

def wall_shear_stress(U_inf: float, rho: float, Re_L: float) -> float:
    """τ_w = 0.5 · C_f · ρ · U_inf²"""
    C_f = skin_friction_coefficient(Re_L)
    return 0.5 * C_f * rho * (U_inf ** 2)

def friction_velocity(tau_w: float, rho: float) -> float:
    """u_τ = √(τ_w / ρ)"""
    return math.sqrt(tau_w / rho)

# ============================================================================
# DIMENSIONAMIENTO MALLA
# ============================================================================

def calculate_mesh_spec(flow: FlowParams, mesh: MeshParams, debug: bool = False) -> MeshSpec:
    """
    Calcula especificación de malla.
    
    Entrada:
      flow: Re, L_char, propiedades fluido
      mesh: y+, Δx+, Δz+ objetivo, modelo turbulencia
    
    Salida:
      MeshSpec con Δy, Δx, Δz, validaciones
    """
    
    # Velocidad característica U_inf
    U_inf = (flow.mu * flow.Re) / (flow.rho * flow.L_char)
    
    if debug:
        print(f"\n[DEBUG] Parámetros iniciales:")
        print(f"  Re = {flow.Re}, L_char = {flow.L_char} m")
        print(f"  U_inf = {U_inf:.4f} m/s")
        print(f"  ρ = {flow.rho} kg/m³, μ = {flow.mu} Pa·s")
    
    # Esfuerzo de pared
    tau_w = wall_shear_stress(U_inf, flow.rho, flow.Re)
    u_tau = friction_velocity(tau_w, flow.rho)
    
    if debug:
        print(f"\n[DEBUG] Fricción pared:")
        print(f"  τ_w = {tau_w:.4e} Pa")
        print(f"  u_τ = {u_tau:.4f} m/s")
    
    # Viscosidad cinemática ν
    nu = flow.mu / flow.rho
    
    # Escala de Kolmogorov (LES)
    eta_K = (nu ** 3 / 0.1) ** 0.25  # ε ~ 0.1 m²/s³ (estimado)
    
    # Momentum thickness θ (Blausius)
    theta = 0.664 * (nu * flow.L_char / U_inf) ** 0.5
    H = 2.59  # factor de forma (Blaulius, flujo laminar)
    Re_theta = flow.rho * U_inf * theta / flow.mu
    
    if debug:
        print(f"\n[DEBUG] Escala de turbulencia:")
        print(f"  η_K (Kolmogorov) = {eta_K:.4e} m")
        print(f"  θ (momentum thickness) = {theta:.4e} m")
        print(f"  H (shape factor) = {H:.2f}")
        print(f"  Re_θ = {Re_theta:.1f}")
    
    # Dimensionamiento del primer nodo (y+)
    delta_y = (mesh.y_plus * flow.mu) / (flow.rho * u_tau)
    y_plus_actual = (flow.rho * u_tau * delta_y) / flow.mu
    
    # Número de capas para cubrir BL (~0.2 L_char)
    BL_thickness = 0.2 * flow.L_char
    n_layers = max(15, int(BL_thickness / delta_y / 1.2))  # ratio ~1.2
    if mesh.n_layers_bl:
        n_layers = mesh.n_layers_bl
    
    # Dimensionamiento chordwise (Δx+)
    delta_x = (mesh.deltax_plus * flow.mu) / (flow.rho * u_tau)
    delta_x_plus_actual = (flow.rho * u_tau * delta_x) / flow.mu
    
    # Dimensionamiento spanwise (Δz+) si aplica
    delta_z = None
    delta_z_plus_actual = None
    if mesh.deltaz_plus:
        delta_z = (mesh.deltaz_plus * flow.mu) / (flow.rho * u_tau)
        delta_z_plus_actual = (flow.rho * u_tau * delta_z) / flow.mu
    
    # Validaciones y warnings
    warnings = []
    turb_data = TURBULENCE_CRITERIA.get(mesh.model, {})
    y_plus_range = turb_data.get("y_plus_target", (0.1, 5.0))
    
    if y_plus_actual > y_plus_range[1]:
        warnings.append(f"y+ = {y_plus_actual:.2f} > {y_plus_range[1]} (modelo {mesh.model})")
    if y_plus_actual < y_plus_range[0]:
        warnings.append(f"y+ = {y_plus_actual:.2f} < {y_plus_range[0]} (muy resuelto, muy fine)")
    
    if debug:
        print(f"\n[DEBUG] Dimensionamiento malla:")
        print(f"  Δy (1er nodo) = {delta_y:.4e} m")
        print(f"  y+ real = {y_plus_actual:.4f} (objetivo {mesh.y_plus})")
        print(f"  # capas BL = {n_layers}")
        print(f"  Δx (objetivo Δx+ = {mesh.deltax_plus}) = {delta_x:.4e} m")
        if mesh.deltaz_plus:
            print(f"  Δz (objetivo Δz+ = {mesh.deltaz_plus}) = {delta_z:.4e} m")
    
    spec = MeshSpec(
        y_plus_actual=y_plus_actual,
        delta_y=delta_y,
        delta_x_plus=mesh.deltax_plus,
        delta_x=delta_x,
        delta_z_plus=mesh.deltaz_plus,
        delta_z=delta_z,
        n_layers=n_layers,
        domain_upstream=mesh.domain_upstream * flow.L_char,
        domain_downstream=mesh.domain_downstream * flow.L_char,
        domain_height=mesh.domain_height * flow.L_char,
        tau_wall=tau_w,
        u_friction=u_tau,
        kolmogorov_scale=eta_K,
        theta=theta,
        H=H,
        reynolds_theta=Re_theta,
        warnings=warnings
    )
    
    return spec

# ============================================================================
# PROTOCOLO GCI (RANS)
# ============================================================================

class GCIProtocol:
    """
    Grid Convergence Index (Roache, AIAA J.)
    3-malla protocol: gruesa, media (referencia), fina
    """
    
    def __init__(self, mesh_spec: MeshSpec, debug: bool = False):
        self.mesh_ref = mesh_spec
        self.debug = debug
        self.r = 1.5  # factor refinamiento (típico)
        
    def generate_three_meshes(self) -> Dict:
        """Genera especificaciones de 3 mallas"""
        # Malla gruesa: factor 1/r
        scale_coarse = 1 / self.r
        
        # Malla fina: factor r
        scale_fine = self.r
        
        meshes = {
            "coarse": self._scale_mesh(self.mesh_ref, scale_coarse),
            "medium": self.mesh_ref,
            "fine": self._scale_mesh(self.mesh_ref, scale_fine),
        }
        
        return meshes
    
    def _scale_mesh(self, spec: MeshSpec, factor: float) -> Dict:
        """Escala malla por factor"""
        return {
            "delta_y": spec.delta_y * factor,
            "delta_x": spec.delta_x * factor,
            "delta_z": spec.delta_z * factor if spec.delta_z else None,
            "n_layers": int(spec.n_layers / factor) if factor > 1 else spec.n_layers,
        }
    
    def estimate_gci(self, phi_fine: float, phi_medium: float, phi_coarse: float, 
                     p: float = 2.0) -> Dict:
        """
        Estima GCI (Roache).
        
        φ: variable monitoreada (ej. C_L, posición separación)
        p: orden de precisión del esquema (~2 para RANS 2nd order)
        """
        
        r21 = (self.mesh_ref["delta_y"] * self.r) / self.mesh_ref["delta_y"]  # r medium→fine
        r32 = (self.mesh_ref["delta_y"]) / (self.mesh_ref["delta_y"] / self.r)  # r coarse→medium
        
        # Extrapolación Richardson
        epsilon_32 = phi_medium - phi_coarse
        epsilon_21 = phi_fine - phi_medium
        
        if abs(epsilon_32) < 1e-14:
            p_est = 0
        else:
            p_est = math.log((r32 ** p - 1) / (r21 ** p - 1)) / math.log(r32 / r21)
            p_est = max(1.0, min(p_est, 4.0))  # clip a rango físico
        
        # GCI
        fs = 1.25  # factor seguridad
        gci21 = fs * abs(epsilon_21) / (r21 ** p_est - 1) * 100
        gci32 = fs * abs(epsilon_32) / (r32 ** p_est - 1) * 100
        
        return {
            "p_estimated": p_est,
            "epsilon_21": epsilon_21,
            "epsilon_32": epsilon_32,
            "gci21": gci21,
            "gci32": gci32,
            "asymptotic": gci21 / (r21 ** p_est),
            "recommendation": "ACEPTADO" if gci21 < 5 else ("REVISAR" if gci21 < 10 else "REFINAR"),
        }

# ============================================================================
# GENERADORES DE OUTPUT
# ============================================================================

def generate_json_config(flow: FlowParams, mesh: MeshParams, spec: MeshSpec) -> Dict:
    """Genera config JSON para Gmsh/Salome"""
    return {
        "metadata": {
            "timestamp": datetime.now().isoformat(),
            "model": mesh.model,
            "Re": flow.Re,
            "fluid": flow.fluid_name,
            "L_char": flow.L_char,
        },
        "flow": asdict(flow),
        "mesh": asdict(mesh),
        "specification": asdict(spec),
    }

def generate_icem_notes(flow: FlowParams, mesh: MeshParams, spec: MeshSpec) -> str:
    """Genera notas de dimensionado para ICEM CFD"""
    
    # Tamaño base del dominio
    domain_size = spec.domain_height
    base_size = domain_size / 50  # ~50 elementos en altura (typical far-field)
    
    # Tamaño en superficie del airfoil
    surface_size = spec.delta_x * 0.8  # Ligeramente más fino
    
    # Tamaño en curva (leading/trailing edge)
    curve_size_le = spec.delta_x * 0.5  # Leading edge más fino
    
    # Parámetros inflación ICEM
    inflation_height = spec.delta_y
    n_inflation = spec.n_layers
    growth_ratio = 1.2
    
    # Cálculo más conservador de estimación (no usar n_layers que es altísimo)
    bl_elements_chordwise = max(30, int(flow.L_char / spec.delta_x))
    total_2d_est = int(85000 * (mesh.deltax_plus / 50))
    
    notes = f"""
================================================================================
DIMENSIONADO DE MALLA PARA ICEM CFD
================================================================================

Generado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Caso: Re = {flow.Re:.0f}, L_char = {flow.L_char:.4f} m, {flow.fluid_name}
Modelo: {mesh.model.upper()}

PARÁMETROS GLOBALES
================================================================================

1. BASE SIZE (Global)
   
   Dominio height/width: {spec.domain_height:.4f} m
   Recomendado base size: {base_size:.4e} m
   
   En ICEM UI:
   → Geometry > Global Size > Input: {base_size:.4e}
   
   Este tamaño se aplica a todo el dominio far-field.
   Se refinará localmente en geometría y BL.

================================================================================

2. LOCAL SIZES - SURFACE (Geometría Airfoil/Cilindro)
   
   Superficie principal (upper/lower):
   └─ Size: {surface_size:.4e} m
   
   Leading edge (zona crítica):
   └─ Size: {curve_size_le:.4e} m
   
   Trailing edge:
   └─ Size: {spec.delta_x:.4e} m
   
   Workflow en ICEM:
   1. Select surface (Upper, Lower)
      → Properties > Mesh Size > {surface_size:.4e}
   
   2. Select curve (Leading edge)
      → Properties > Mesh Size > {curve_size_le:.4e}
      → Check "Mesh along curve" si es necesario

================================================================================

3. LOCAL SIZES - CURVES (Contornos)
   
   Airfoil perimeter:
   └─ Curve size: {spec.delta_x:.4e} m
      (Δx+ = {mesh.deltax_plus}, chordwise)
   
   Far-field outer boundary:
   └─ Curve size: {base_size * 2:.4e} m
      (Coarse para far-field)
   
   En ICEM:
   → Curves > Select curve > Properties > Size > {spec.delta_x:.4e}

================================================================================

4. INFLATION LAYERS (Boundary Layer)
   
   First layer height (Δy):     {spec.delta_y:.4e} m
   Number of layers:             {spec.n_layers}
   Growth ratio:                 {growth_ratio}
   
   Total BL thickness:           {spec.delta_y * ((growth_ratio ** spec.n_layers - 1) / (growth_ratio - 1)):.4e} m
   Target y+ (pared):            {spec.y_plus_actual:.4f}
   
   En ICEM UI (Inflation Setup):
   1. Select surface (airfoil wall)
   2. Inflation > New inflation
      ├─ First height: {spec.delta_y:.4e} m
      ├─ Number of layers: {spec.n_layers}
      └─ Growth ratio: {growth_ratio}
   
   3. Smooth transition
      └─ Si ICEM alerta "layers too big", aumentar growth ratio a 1.3

================================================================================

5. REFINEMENT ZONES (Regiones especiales)
   
   A. Separación laminar (LSB region)
      └─ Si esperado LSB en x/c ≈ 0.3–0.6:
         ├─ Crear box refinement
         ├─ Size: {spec.delta_x * 0.7:.4e} m
         └─ Max distance from surface: {spec.delta_y * 5:.4e} m
   
   B. Wake behind airfoil
      └─ Box refinement (downstream)
         ├─ Size: {spec.delta_x * 1.5:.4e} m
         └─ Extent: x/c = [1.0, 15×L_char]

================================================================================

6. PARÁMETROS DE MALLA GLOBAL (ICEM Advanced)
   
   Mesh type:                   Unstructured / Hybrid (si quieres prisms en BL)
   Element type:                Tetrahedral (std) o Prism + Tet (mejor)
   
   Si Hybrid (Prism + Tet):
   ├─ Prism in inflation layers: ON
   ├─ Prism height: {spec.delta_y:.4e} m
   └─ Prism layers: {spec.n_layers}
   
   Quality:
   ├─ Min angle: 20° (default)
   └─ Growth rate: 1.2 (en transición BL→far-field)

================================================================================

7. DOMINIO Y BOUNDARIES
   
   Inlet (upstream):      {spec.domain_upstream:.4f} m
   Outlet (downstream):   {spec.domain_downstream:.4f} m
   Height (top/bottom):   ±{spec.domain_height/2:.4f} m
   
   En ICEM:
   1. Create domain box (Geometry > Primitive > Box)
      └─ Dimensions: {spec.domain_upstream + spec.domain_downstream:.4f} × {spec.domain_height:.4f} × [si 3D: {spec.delta_z if spec.delta_z else 'N/A'} m]
   
   2. Boolean subtract airfoil from domain
      → Geometry > Boolean > Subtract
   
   3. Assign boundary names:
      ├─ Inlet: "inlet"
      ├─ Outlet: "outlet"
      ├─ Walls (sides): "sym_top", "sym_bottom"
      └─ Airfoil: "wall"

================================================================================

8. DIMENSIONADO 3D (si Δz+ especificado)
   
   Spanwise domain size:     {spec.delta_z if spec.delta_z else 'N/A (2D case)'} m
   Spanwise spacing (Δz):    {spec.delta_z if spec.delta_z else 'N/A'} m
   
   Si 3D:
   └─ Periodic BC (recomendado si LSB dinámico):
      ├─ Create periodic pair
      ├─ Lz = 0.1×L_char (pequeño para ahorrar nodos)
      └─ En Fluent: Periodic-Rotational con offset 0

================================================================================

WORKFLOW RECOMENDADO EN ICEM
================================================================================

1. Importar geometría
   → File > Open > airfoil.iges/step

2. Crear dominio
   → Geometry > Primitive > Box (parámetros arriba)
   → Boolean Subtract airfoil del dominio

3. Asignar tamaños
   → Mesh > Global Size: {base_size:.4e} m
   → Surfaces > Select airfoil > Size: {surface_size:.4e} m
   → Curves > Leading edge > Size: {curve_size_le:.4e} m

4. Inflation layers
   → Surface > Select airfoil wall
   → Inflation > New
      ├─ First height: {spec.delta_y:.4e} m
      ├─ Layers: {spec.n_layers}
      └─ Ratio: {growth_ratio}

5. Generar malla
   → Mesh > Mesh > Compute
   → Verificar element count (~{total_2d_est} nodos 2D esperado)

6. Validar calidad
   → Mesh > Quality > Check
   → Min angle: debe ser > 20°
   → Max aspect ratio en BL: OK (~1000 es aceptable)

7. Exportar a Fluent
   → File > Export > Fluent Case (.cas)
   → ICEM automáticamente exporta malla + boundary names

================================================================================

ESTIMACIÓN DE NODOS
================================================================================

Basado en geometría 2D y parámetros:

FAR-FIELD elements:
  Domain area: {spec.domain_upstream + spec.domain_downstream:.2f} × {spec.domain_height:.2f} m²
  ÷ base_size²: ~{int((spec.domain_upstream + spec.domain_downstream) * spec.domain_height / (base_size**2) * 0.5)} elementos

BOUNDARY LAYER elements:
  Chordwise: ~{bl_elements_chordwise} elementos
  Normal (inflation): {spec.n_layers} capas
  ≈ {int(bl_elements_chordwise * 30)} elementos BL

REFINEMENT zones (LSB, wake):
  ~{int(bl_elements_chordwise * 50)} elementos

TOTAL ESTIMADO (2D): {total_2d_est} nodos ±20%

Si 3D: ×(Lz / Δz) = ×{int(spec.domain_height / (spec.delta_z if spec.delta_z else 0.01))} layers
       ~{int(total_2d_est * (spec.domain_height / (spec.delta_z if spec.delta_z else 0.01)))} nodos total

================================================================================

TROUBLESHOOTING EN ICEM
================================================================================

⚠ "Inflation layers too thick"
   → Reducir n_layers (de {spec.n_layers} a {int(spec.n_layers * 0.7)})
   → O aumentar growth_ratio de {growth_ratio} a 1.3

⚠ "Surface mesh cannot be created"
   → Base size demasiado grande relativo a geometría
   → Reducir base size a {base_size * 0.5:.4e} m

⚠ "Bad quality elements near leading edge"
   → Curve size en LE muy pequeño
   → Aumentar de {curve_size_le:.4e} a {spec.delta_x:.4e} m
   → O usar "Smooth transition" en inflation

================================================================================

PARÁMETROS PARA COPIAR-PEGAR
================================================================================

Global Size:              {base_size:.4e}
Surface (airfoil):        {surface_size:.4e}
Curve (LE):               {curve_size_le:.4e}
Curve (airfoil):          {spec.delta_x:.4e}
Curve (farfield):         {base_size * 2:.4e}

Inflation:
  First height:           {spec.delta_y:.4e}
  Layers:                 {spec.n_layers}
  Growth ratio:           {growth_ratio}

Dominio:
  Upstream:               {spec.domain_upstream:.4f} m
  Downstream:             {spec.domain_downstream:.4f} m
  Height:                 {spec.domain_height:.4f} m

================================================================================
"""
    
    return notes

def generate_fluent_notes(flow: FlowParams, mesh: MeshParams, spec: MeshSpec, gci: Optional[Dict] = None) -> str:
    """Genera notas de integración Fluent"""
    turb_info = TURBULENCE_CRITERIA.get(mesh.model, {})
    
    notes = f"""
================================================================================
INTEGRACIÓN FLUENT: {mesh.model.upper()}
================================================================================

Generado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Caso: Re = {flow.Re:.0f}, L_char = {flow.L_char:.4f} m, {flow.fluid_name}

PARÁMETROS MALLA
================================================================================
Δy (1er nodo):        {spec.delta_y:.4e} m
y+:                   {spec.y_plus_actual:.4f} (objetivo {mesh.y_plus})
# capas BL:           {spec.n_layers}
Δx (chordwise):       {spec.delta_x:.4e} m  (Δx+ = {mesh.deltax_plus})
"""
    
    if spec.delta_z:
        notes += f"Δz (spanwise):        {spec.delta_z:.4e} m  (Δz+ = {mesh.deltaz_plus})\n"
    
    notes += f"""
Dominio
--------
Upstream:             {spec.domain_upstream:.4f} m ({mesh.domain_upstream:.1f}×L_char)
Downstream:           {spec.domain_downstream:.4f} m ({mesh.domain_downstream:.1f}×L_char)
Altura/Ancho:         {spec.domain_height:.4f} m ({mesh.domain_height:.1f}×L_char)

CONFIGURACIÓN FLUENT
================================================================================

1. MALLA
   - Importar malla desde Gmsh/Salome/ICEM
   - Verificar inflation layers:
     * First height: {spec.delta_y:.4e} m
     * Growth ratio: 1.2 (típico)
     * Número de capas: {spec.n_layers}
   
   - Verificar tamaño de dominio (upstream/downstream/altura)

2. MODELOS
   - Modelo turbulencia:       {turb_info.get('name', mesh.model)}
   - Wall treatment:           {turb_info.get('wall_treatment', 'N/A')}
   - Notas:                    {turb_info.get('notes', '')}

3. CONDICIONES DE CONTORNO
   - Inlet (upstream):    Velocity inlet, U = {flow.mu * flow.Re / (flow.rho * flow.L_char):.4f} m/s
   - Outlet (downstream): Pressure outlet, P_gauge = 0
   - Pared (geometría):   No-slip
   - Far-field (lateral): Symmetry o Slip wall

4. MONITOREO
   - Wall y+ (monitors): Crear función personalizada para y+ en pared
   - Validar y+ < {turb_info.get('y_plus_target', (1,))[1]} ({mesh.model})
   - Monitorear Residuales: continuidad, x/y/z momentum < 1e-6

5. CRITERIO CONVERGENCIA
   - Residuales (ver arriba)
   - Monitores de interés (C_L, separación, τ_w) < 1% variación en 100 iteraciones
"""
    
    if gci:
        notes += f"""
PROTOCOLO GCI (RANS)
================================================================================
Factor refinamiento r:        {gci.get('r', 1.5)}
Orden precisión estimado p:   {gci.get('p_estimated', '~2')}

Mallas generadas:
  - Gruesa (coarse):   Δy×{1/gci.get('r', 1.5)}, n_layers×{1/gci.get('r', 1.5)}
  - Media (medium):    Δy = {spec.delta_y:.4e} m (REFERENCIA)
  - Fina (fine):       Δy×{gci.get('r', 1.5)}, n_layers×{gci.get('r', 1.5)}

GCI convergence (si media referencia):
  - GCI_21 (medium→fine):  {gci.get('gci21', 'N/A')}%
  - Recomendación:        {gci.get('recommendation', 'N/A')}

Interpretación:
  - GCI < 5%:  Malla convergida, usar media
  - 5% < GCI < 10%:  Aceptable, revisar separación si crítica
  - GCI > 10%:  Refinar (usar fina, replantear Δx+/Δz+)
"""
    
    notes += f"""
WARNINGS
================================================================================
"""
    if spec.warnings:
        for w in spec.warnings:
            notes += f"  ⚠ {w}\n"
    else:
        notes += "  ✓ Sin warnings\n"
    
    notes += """
PRÓXIMOS PASOS
================================================================================
1. Exportar malla desde Gmsh/Salome con parámetros arriba
2. Importar a Fluent
3. Configurar modelos y BCs según sección CONFIGURACIÓN FLUENT
4. Inicializar (y+ = 0, velocidades = 0)
5. Iterar hasta convergencia
6. Post-procesamiento: validar y+, τ_w, separación
7. Si GCI > 10%, refinar con parámetro "fina" y repetir

================================================================================
"""
    
    return notes

def generate_debug_log(flow: FlowParams, mesh: MeshParams, spec: MeshSpec) -> str:
    """Log detallado de cálculos internos"""
    
    U_inf = (flow.mu * flow.Re) / (flow.rho * flow.L_char)
    
    log = f"""
================================================================================
DEBUG LOG: CFD MESH DESIGN
================================================================================

Timestamp: {datetime.now().isoformat()}

ENTRADA
----------------
Re:                {flow.Re}
L_char:            {flow.L_char} m
Fluido:            {flow.fluid_name}
ρ:                 {flow.rho} kg/m³
μ:                 {flow.mu:.4e} Pa·s
Modelo:            {mesh.model}
Objetivo y+:       {mesh.y_plus}
Objetivo Δx+:      {mesh.deltax_plus}
Objetivo Δz+:      {mesh.deltaz_plus}

CÁLCULOS INTERNOS
----------------
U_inf:             {U_inf:.6f} m/s
τ_w:               {spec.tau_wall:.6e} Pa
u_τ:               {spec.u_friction:.6f} m/s
ν (cinemática):    {flow.mu/flow.rho:.6e} m²/s
η_K (Kolmogorov):  {spec.kolmogorov_scale:.6e} m
θ (momentum):      {spec.theta:.6e} m
H (shape factor):  {spec.H:.4f}
Re_θ:              {spec.reynolds_theta:.1f}

RESULTADO MALLA
----------------
Δy (1er nodo):     {spec.delta_y:.6e} m
y+ real:           {spec.y_plus_actual:.6f}
Δy / η_K:          {spec.delta_y / spec.kolmogorov_scale:.2f}
# capas BL:        {spec.n_layers}

Δx:                {spec.delta_x:.6e} m
Δx+ real:          {spec.delta_x_plus:.6f}
Δx / L_char:       {spec.delta_x / flow.L_char * 100:.4f}%

"""
    
    if spec.delta_z:
        log += f"Δz:                {spec.delta_z:.6e} m\n"
        log += f"Δz+ real:          {spec.delta_z_plus:.6f}\n"
    
    log += f"""
DOMINIO
----------------
Upstream:          {spec.domain_upstream:.6f} m ({spec.domain_upstream/flow.L_char:.1f}×L)
Downstream:        {spec.domain_downstream:.6f} m ({spec.domain_downstream/flow.L_char:.1f}×L)
Height/Width:      {spec.domain_height:.6f} m ({spec.domain_height/flow.L_char:.1f}×L)

VALIDACIONES
----------------
"""
    
    if spec.warnings:
        for w in spec.warnings:
            log += f"⚠ {w}\n"
    else:
        log += "✓ Sin warnings críticos\n"
    
    return log

# ============================================================================
# MAIN
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="CFD Mesh Design Calculator (RANS/DES/LES)"
    )
    
    # Flujo
    parser.add_argument("--re", type=float, required=True, help="Reynolds number")
    parser.add_argument("--char-length", type=float, required=True, help="Characteristic length (m)")
    parser.add_argument("--fluid", type=str, default="water", 
                       help="Fluid: water, air, custom")
    parser.add_argument("--rho", type=float, help="Density (custom fluid, kg/m³)")
    parser.add_argument("--mu", type=float, help="Dynamic viscosity (custom fluid, Pa·s)")
    parser.add_argument("--T", type=float, help="Temperature (K), affects air viscosity")
    
    # Malla
    parser.add_argument("--model", type=str, required=True,
                       help="Turbulence model: rans-sst, rans-ke, rans-sa, des-ddes, des-iddes, les-resolved, les-wmles")
    parser.add_argument("--y-plus", type=float, required=True, help="Target y+ (adimensional wall)")
    parser.add_argument("--deltax-plus", type=float, required=True, help="Target Δx+ (chordwise)")
    parser.add_argument("--deltaz-plus", type=float, help="Target Δz+ (spanwise)")
    parser.add_argument("--domain-upstream", type=float, default=5, help="Upstream (×L_char)")
    parser.add_argument("--domain-downstream", type=float, default=15, help="Downstream (×L_char)")
    parser.add_argument("--domain-height", type=float, default=10, help="Height/width (×L_char)")
    parser.add_argument("--n-layers", type=int, help="# BL layers (overrides y+ calc)")
    
    # Output
    parser.add_argument("--output", type=str, default="mesh_config",
                       help="Output prefix (generates .json, .txt files)")
    parser.add_argument("--debug", action="store_true", help="Verbose debugging")
    
    args = parser.parse_args()
    
    # Validar modelo
    if args.model not in TURBULENCE_CRITERIA:
        print(f"Error: Modelo desconocido '{args.model}'")
        print(f"Disponibles: {', '.join(TURBULENCE_CRITERIA.keys())}")
        sys.exit(1)
    
    # Obtener propiedades fluido
    fluid_props = get_fluid_properties(args.fluid, T=args.T, rho=args.rho, mu=args.mu)
    
    if args.debug:
        print(f"[DEBUG] Propiedades {args.fluid}:")
        print(f"  ρ = {fluid_props['rho']} kg/m³")
        print(f"  μ = {fluid_props['mu']:.4e} Pa·s")
    
    # Crear objetos
    flow = FlowParams(
        Re=args.re,
        L_char=args.char_length,
        rho=fluid_props["rho"],
        mu=fluid_props["mu"],
        fluid_name=args.fluid,
        T=args.T
    )
    
    mesh = MeshParams(
        model=args.model,
        y_plus=args.y_plus,
        deltax_plus=args.deltax_plus,
        deltaz_plus=args.deltaz_plus,
        domain_upstream=args.domain_upstream,
        domain_downstream=args.domain_downstream,
        domain_height=args.domain_height,
        n_layers_bl=args.n_layers
    )
    
    # Calcular especificación
    print("[*] Calculando especificación de malla...")
    spec = calculate_mesh_spec(flow, mesh, debug=args.debug)
    
    print(f"\n✓ y+ = {spec.y_plus_actual:.4f}")
    print(f"✓ Δy = {spec.delta_y:.4e} m")
    print(f"✓ # capas = {spec.n_layers}")
    print(f"✓ Δx = {spec.delta_x:.4e} m")
    
    if spec.delta_z:
        print(f"✓ Δz = {spec.delta_z:.4e} m")
    
    if spec.warnings:
        print("\n⚠ Warnings:")
        for w in spec.warnings:
            print(f"  - {w}")
    
    # GCI si RANS
    turb_data = TURBULENCE_CRITERIA[args.model]
    gci_result = None
    if turb_data["requires_gci"]:
        print("\n[*] Generando protocolo GCI (3 mallas)...")
        gci = GCIProtocol(spec, debug=args.debug)
        three_meshes = gci.generate_three_meshes()
        print("✓ Mallas gruesa, media, fina generadas")
        print("  (Especificar variable monitoreada para calcular GCI real)")
    
    # Generar exports
    print(f"\n[*] Generando exports con prefix '{args.output}'...")
    
    # JSON
    config = generate_json_config(flow, mesh, spec)
    with open(f"{args.output}.json", "w") as f:
        json.dump(config, f, indent=2)
    print(f"✓ {args.output}.json")
    
    # ICEM notes
    icem_notes = generate_icem_notes(flow, mesh, spec)
    with open(f"{args.output}_icem_notes.txt", "w") as f:
        f.write(icem_notes)
    print(f"✓ {args.output}_icem_notes.txt")
    
    # Fluent notes
    fluent_notes = generate_fluent_notes(flow, mesh, spec, gci_result)
    with open(f"{args.output}_fluent_notes.txt", "w") as f:
        f.write(fluent_notes)
    print(f"✓ {args.output}_fluent_notes.txt")
    
    # Debug log
    debug_log = generate_debug_log(flow, mesh, spec)
    with open(f"{args.output}_debug.txt", "w") as f:
        f.write(debug_log)
    print(f"✓ {args.output}_debug.txt")
    
    print("\n✓ Completado.")

if __name__ == "__main__":
    main()
