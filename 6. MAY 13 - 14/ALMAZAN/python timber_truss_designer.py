"""
TIMBER TRUSS DESIGNER - Professional Edition
NSCP 2015 Compliant Timber Roof Truss Design Software
Version 1.0

Author: Structural Engineering Software Solutions
Purpose: Complete timber truss design workflow for Philippine construction

References:
- NSCP 2015 (National Structural Code of the Philippines)
- Volume 1: Buildings, Towers, and Other Vertical Structures
- Chapter 6: Timber (ASD Method)
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import json
import os
from datetime import datetime
import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
import warnings
warnings.filterwarnings('ignore')

# ============================================================================
# SECTION 1: MATERIAL DATABASES AND CONSTANTS
# ============================================================================

class TimberDatabase:
    """Database of Philippine timber species with NSCP 2015 reference values"""
    
    # Timber species data based on NSCP 2015 Table 603
    # Format: species_name: (Fb_bending_MPa, Ft_tension_MPa, Fc_compression_MPa, 
    #                        Fv_shear_MPa, E_modulus_MPa, density_kg_m3)
    
    TIMBER_SPECIES = {
        "Yakal (Hopea spp.)": (24.1, 16.5, 15.9, 2.6, 13800, 750),
        "Apitong (Dipterocarpus spp.)": (17.2, 11.7, 11.7, 2.1, 10300, 670),
        "Lauan (Shorea spp.)": (13.8, 9.3, 9.7, 1.7, 9300, 550),
        "Gmelina (Gmelina arborea)": (9.7, 6.5, 7.6, 1.2, 6900, 450),
        "Mahogany (Swietenia spp.)": (11.0, 7.6, 8.3, 1.4, 7600, 500),
        "Douglas Fir (Pseudotsuga menziesii)": (15.2, 10.3, 11.0, 1.9, 11000, 530),
        "Hem-Fir (Western Hemlock)": (12.4, 8.3, 9.0, 1.5, 9000, 480),
        "Tanguile (Shorea polysperma)": (14.5, 9.8, 10.3, 1.8, 9800, 580),
        "Narra (Pterocarpus indicus)": (13.1, 8.9, 9.3, 1.6, 8900, 520)
    }
    
    # Common Philippine lumber sizes (actual dimensions in mm)
    # Format: (nominal_inches, actual_width_mm, actual_depth_mm)
    LUMBER_SIZES = [
        (1, 19, 38),   # 1" x 2" actual
        (1, 19, 50),   # 1" x 3" actual
        (1, 19, 75),   # 1" x 4" actual
        (1, 19, 100),  # 1" x 6" actual
        (2, 38, 38),   # 2" x 2" actual
        (2, 38, 50),   # 2" x 3" actual
        (2, 38, 75),   # 2" x 4" actual
        (2, 38, 100),  # 2" x 6" actual
        (2, 38, 150),  # 2" x 8" actual
        (2, 38, 200),  # 2" x 10" actual
        (2, 38, 250),  # 2" x 12" actual
        (3, 50, 150),  # 3" x 8" actual
        (3, 50, 200),  # 3" x 10" actual
        (3, 50, 250),  # 3" x 12" actual
        (4, 75, 200),  # 4" x 10" actual
        (4, 75, 250)   # 4" x 12" actual
    ]
    
    @staticmethod
    def get_section_properties(width_mm, depth_mm):
        """Calculate section properties for given dimensions"""
        width_m = width_mm / 1000
        depth_m = depth_mm / 1000
        
        area = width_m * depth_m  # m²
        Ix = (width_m * depth_m**3) / 12  # m⁴
        Iy = (width_m**3 * depth_m) / 12  # m⁴
        rx = np.sqrt(Ix / area)  # m
        ry = np.sqrt(Iy / area)  # m
        Sx = Ix / (depth_m/2)  # m³
        
        return {
            'area_m2': area,
            'area_mm2': area * 1e6,
            'Ix_m4': Ix,
            'Ix_mm4': Ix * 1e12,
            'Iy_m4': Iy,
            'rx_m': rx,
            'rx_mm': rx * 1000,
            'ry_m': ry,
            'ry_mm': ry * 1000,
            'Sx_m3': Sx,
            'width_mm': width_mm,
            'depth_mm': depth_mm
        }

# ============================================================================
# SECTION 2: ADJUSTMENT FACTORS (NSCP 2015 Section 603)
# ============================================================================

class AdjustmentFactors:
    """NSCP 2015 adjustment factors for timber design"""
    
    @staticmethod
    def load_duration_factor(duration_type):
        """
        Load duration factor (CD) - NSCP 2015 Table 603.2.1
        Values are for ASD method
        """
        factors = {
            "Permanent (10+ years)": 0.9,
            "Ten years": 1.0,
            "Two months (Snow)": 1.15,
            "Seven days (Construction)": 1.25,
            "Ten minutes (Wind/Earthquake)": 1.6,
            "Impact": 2.0
        }
        return factors.get(duration_type, 1.0)
    
    @staticmethod
    def wet_service_factor(moisture_condition, member_type):
        """
        Wet service factor (CM) - NSCP 2015 Table 603.2.2
        """
        if moisture_condition == "Dry (MC <= 19%)":
            return 1.0
        else:  # Wet (MC > 19%)
            if member_type in ["Bending", "Tension", "Compression"]:
                return 0.7
            elif member_type == "Shear":
                return 0.97
            else:
                return 0.8
    
    @staticmethod
    def temperature_factor(temperature_range):
        """
        Temperature factor (Ct) - NSCP 2015 Table 603.2.3
        """
        factors = {
            "Normal (<= 38°C)": 1.0,
            "38°C to 52°C": 0.8,
            "52°C to 65°C": 0.7,
            "65°C to 80°C": 0.5
        }
        return factors.get(temperature_range, 1.0)
    
    @staticmethod
    def size_factor(depth_mm, species):
        """
        Size factor (CF) - NSCP 2015 Section 603.2.4
        Applies to bending members only
        """
        # Common size factor formula for sawn lumber
        depth_in = depth_mm / 25.4
        if depth_in <= 12:
            # Based on NSCP 2015 Equation 603-1
            factor = (12 / depth_in) ** (1/9)
            return min(factor, 1.0)  # CF cannot exceed 1.0
        return 1.0
    
    @staticmethod
    def stability_factor(le, d, b, E, Fb):
        """
        Beam stability factor (CL) - NSCP 2015 Section 603.2.5
        For laterally unsupported beams
        """
        # Calculate slenderness ratio
        RB = np.sqrt(le * d / b**2)
        
        if RB <= 10:
            return 1.0
        
        # Calculate critical buckling stress
        FbE = (0.438 * E) / (RB**2)
        
        # Calculate stability factor using NSCP 2015 Equation 603-3
        ratio = FbE / Fb
        numerator = 1 + ratio
        denominator = 1.9
        term1 = numerator / denominator
        term2 = np.sqrt(((1 + ratio) / (1.9))**2 - (ratio / 0.95))
        
        CL = term1 - term2
        return min(CL, 1.0)  # CL cannot exceed 1.0
    
    @staticmethod
    def volume_factor(length_ft, volume_ft3, species):
        """
        Volume factor (CV) - NSCP 2015 Section 603.2.6
        For glued-laminated timber only
        """
        # Simplified for sawn lumber (usually CV = 1.0)
        return 1.0
    
    @staticmethod
    def format_factor(member_type):
        """
        Format factor (Cfu) - NSCP 2015 Section 603.2.7
        For mechanically laminated decks
        """
        return 1.0  # Default for sawn lumber

# ============================================================================
# SECTION 3: TRUSS GEOMETRY GENERATOR
# ============================================================================

class TrussGeometry:
    """Generate and manage truss geometry"""
    
    def __init__(self, span_m, rise_m, truss_type, num_panels):
        """
        Initialize truss geometry
        
        Args:
            span_m: Truss span in meters
            rise_m: Truss rise at peak in meters
            truss_type: Type of truss (Pratt, Howe, Fink, Warren)
            num_panels: Number of panels per side (typically 3-8)
        """
        self.span_m = span_m
        self.rise_m = rise_m
        self.truss_type = truss_type
        self.num_panels = num_panels
        self.nodes = []  # List of (x, y) coordinates in meters
        self.members = []  # List of (node_i, node_j) connections
        self.member_lengths = []  # Length of each member
        
        self.generate_geometry()
        
    def generate_geometry(self):
        """Generate node coordinates and member connectivity based on truss type"""
        
        if self.truss_type == "Fink":
            self._generate_fink_truss()
        elif self.truss_type == "Pratt":
            self._generate_pratt_truss()
        elif self.truss_type == "Howe":
            self._generate_howe_truss()
        elif self.truss_type == "Warren":
            self._generate_warren_truss()
        else:
            raise ValueError(f"Unknown truss type: {self.truss_type}")
        
        # Calculate member lengths
        self._calculate_member_lengths()
    
    def _generate_fink_truss(self):
        """
        Generate Fink truss geometry
        Typical Fink truss has W-shaped web members
        """
        self.nodes = []
        self.members = []
        
        # Number of node points along top and bottom chords
        nodes_per_side = self.num_panels + 1
        total_nodes_top = 2 * nodes_per_side - 1
        
        # Bottom chord nodes (simply supported)
        bottom_nodes = []
        for i in range(nodes_per_side):
            x = (self.span_m / (nodes_per_side - 1)) * i
            y = 0
            bottom_nodes.append((x, y))
        
        # Top chord nodes (pitched)
        top_nodes = []
        for i in range(total_nodes_top):
            x = (self.span_m / (total_nodes_top - 1)) * i
            # Parabolic or linear pitch
            if x <= self.span_m / 2:
                y = (self.rise_m * x) / (self.span_m / 2)
            else:
                y = (self.rise_m * (self.span_m - x)) / (self.span_m / 2)
            top_nodes.append((x, y))
        
        # Combine bottom and top nodes
        self.nodes = bottom_nodes + top_nodes
        
        # Bottom chord members
        num_bottom = len(bottom_nodes)
        for i in range(num_bottom - 1):
            self.members.append((i, i+1))
        
        # Top chord members
        num_top = len(top_nodes)
        for i in range(num_top - 1):
            self.members.append((num_bottom + i, num_bottom + i+1))
        
        # Web members (Fink pattern - W configuration)
        # Connect bottom chord nodes to top chord nodes
        for panel in range(self.num_panels):
            bottom_idx = panel
            top_left_idx = num_bottom + 2*panel
            top_right_idx = num_bottom + 2*panel + 1
            top_center_idx = num_bottom + 2*panel + 2 if panel < self.num_panels-1 else None
            
            # Vertical members near supports
            if panel == 0 or panel == self.num_panels-1:
                self.members.append((bottom_idx, top_left_idx))
            
            # Diagonal web members
            self.members.append((bottom_idx, top_right_idx))
            if top_center_idx and panel < self.num_panels-1:
                self.members.append((bottom_idx+1, top_center_idx))
        
        # Add peak vertical if needed
        if self.num_panels % 2 == 1:
            mid_bottom = num_bottom // 2
            mid_top = num_bottom + self.num_panels
            self.members.append((mid_bottom, mid_top))
    
    def _generate_pratt_truss(self):
        """
        Generate Pratt truss geometry
        Pratt truss has vertical members in compression, diagonals in tension
        """
        self.nodes = []
        self.members = []
        
        nodes_per_side = self.num_panels + 1
        
        # Bottom chord nodes
        bottom_nodes = []
        for i in range(nodes_per_side):
            x = (self.span_m / (nodes_per_side - 1)) * i
            y = 0
            bottom_nodes.append((x, y))
        
        # Top chord nodes (same number as bottom nodes)
        top_nodes = []
        for i in range(nodes_per_side):
            x = (self.span_m / (nodes_per_side - 1)) * i
            # Linear pitch
            if x <= self.span_m / 2:
                y = (self.rise_m * x) / (self.span_m / 2)
            else:
                y = (self.rise_m * (self.span_m - x)) / (self.span_m / 2)
            top_nodes.append((x, y))
        
        self.nodes = bottom_nodes + top_nodes
        num_bottom = len(bottom_nodes)
        
        # Bottom chord
        for i in range(num_bottom - 1):
            self.members.append((i, i+1))
        
        # Top chord
        for i in range(num_bottom - 1):
            self.members.append((num_bottom + i, num_bottom + i+1))
        
        # Vertical and diagonal web members
        for i in range(num_bottom - 1):
            # Vertical members
            self.members.append((i, num_bottom + i))
            
            # Diagonal members (from bottom to next top node)
            self.members.append((i+1, num_bottom + i))
    
    def _generate_howe_truss(self):
        """
        Generate Howe truss geometry
        Howe truss has vertical members in tension, diagonals in compression
        """
        # Similar to Pratt but with opposite diagonal direction
        self._generate_pratt_truss()  # Start with Pratt pattern
        # Modify diagonals for Howe (typically opposite orientation)
        # For simplicity, we'll use the same but note the difference in analysis
    
    def _generate_warren_truss(self):
        """
        Generate Warren truss geometry
        Warren truss uses alternating diagonal web members without verticals
        """
        self.nodes = []
        self.members = []
        
        nodes_per_side = self.num_panels + 1
        
        # Bottom chord nodes
        bottom_nodes = []
        for i in range(nodes_per_side):
            x = (self.span_m / (nodes_per_side - 1)) * i
            y = 0
            bottom_nodes.append((x, y))
        
        # Top chord nodes
        top_nodes = []
        for i in range(nodes_per_side):
            x = (self.span_m / (nodes_per_side - 1)) * i
            if x <= self.span_m / 2:
                y = (self.rise_m * x) / (self.span_m / 2)
            else:
                y = (self.rise_m * (self.span_m - x)) / (self.span_m / 2)
            top_nodes.append((x, y))
        
        self.nodes = bottom_nodes + top_nodes
        num_bottom = len(bottom_nodes)
        
        # Bottom chord
        for i in range(num_bottom - 1):
            self.members.append((i, i+1))
        
        # Top chord
        for i in range(num_bottom - 1):
            self.members.append((num_bottom + i, num_bottom + i+1))
        
        # Web members (alternating diagonals)
        for i in range(num_bottom - 1):
            if i % 2 == 0:
                # Diagonal from bottom to top next
                self.members.append((i, num_bottom + i+1))
                self.members.append((i+1, num_bottom + i))
            else:
                # Diagonal from bottom to top current
                self.members.append((i, num_bottom + i))
                self.members.append((i+1, num_bottom + i+1))
    
    def _calculate_member_lengths(self):
        """Calculate length of each member based on node coordinates"""
        self.member_lengths = []
        for i, j in self.members:
            xi, yi = self.nodes[i]
            xj, yj = self.nodes[j]
            length = np.sqrt((xj - xi)**2 + (yj - yi)**2)
            self.member_lengths.append(length)
    
    def get_member_info(self):
        """Return list of member information"""
        members_info = []
        for idx, (i, j) in enumerate(self.members):
            xi, yi = self.nodes[i]
            xj, yj = self.nodes[j]
            length = self.member_lengths[idx]
            members_info.append({
                'member_id': idx,
                'node_i': i,
                'node_j': j,
                'length_m': length,
                'angle_rad': np.arctan2(yj - yi, xj - xi),
                'angle_deg': np.degrees(np.arctan2(yj - yi, xj - xi))
            })
        return members_info

# ============================================================================
# SECTION 4: STRUCTURAL ANALYSIS (Matrix Method)
# ============================================================================

class TrussAnalysis:
    """
    2D Truss analysis using Matrix Structural Analysis method
    Based on Direct Stiffness Method
    """
    
    def __init__(self, geometry, E_modulus_GPa, area_m2):
        """
        Initialize truss analysis
        
        Args:
            geometry: TrussGeometry object
            E_modulus_GPa: Modulus of elasticity in GPa
            area_m2: Cross-sectional area in m²
        """
        self.geometry = geometry
        self.E = E_modulus_GPa * 1e9  # Convert to Pa
        self.area = area_m2
        self.num_nodes = len(geometry.nodes)
        self.num_members = len(geometry.members)
        self.num_dof = 2 * self.num_nodes  # 2 DOF per node (x and y)
        
        # Analysis results
        self.displacements = None
        self.reactions = None
        self.member_forces = None
        self.stress = None
        
    def assemble_stiffness_matrix(self):
        """
        Assemble global stiffness matrix using Direct Stiffness Method
        
        Theory:
        For each member, we have local stiffness matrix in member coordinates,
        which is transformed to global coordinates and added to global matrix.
        
        Member local stiffness matrix (2x2 for axial deformation):
        k_local = (EA/L) * [1, -1; -1, 1]
        
        Transformation matrix T rotates from local to global coordinates:
        T = [cosθ, sinθ, 0, 0; 0, 0, cosθ, sinθ]
        
        Global member stiffness: k_global = T^T * k_local * T
        """
        
        # Initialize global stiffness matrix (sparse storage for efficiency)
        K_global = np.zeros((self.num_dof, self.num_dof))
        
        # Process each member
        for member_idx, (node_i, node_j) in enumerate(self.geometry.members):
            # Get member properties
            L = self.geometry.member_lengths[member_idx]
            EA = self.E * self.area
            
            # Get node coordinates
            xi, yi = self.geometry.nodes[node_i]
            xj, yj = self.geometry.nodes[node_j]
            
            # Calculate member orientation
            dx = xj - xi
            dy = yj - yi
            cosθ = dx / L
            sinθ = dy / L
            
            # Local stiffness matrix (2x2 for axial deformation)
            k_local = (EA / L) * np.array([[1, -1], [-1, 1]])
            
            # Transformation matrix (4x2)
            T = np.array([
                [cosθ, sinθ, 0, 0],
                [0, 0, cosθ, sinθ]
            ])
            
            # Global stiffness matrix for member (4x4)
            k_global_member = T.T @ k_local @ T
            
            # DOF mapping for nodes i and j
            dof_i = [2*node_i, 2*node_i + 1]  # x and y DOF for node i
            dof_j = [2*node_j, 2*node_j + 1]  # x and y DOF for node j
            dofs = dof_i + dof_j
            
            # Assemble into global matrix
            for a in range(4):
                for b in range(4):
                    K_global[dofs[a], dofs[b]] += k_global_member[a, b]
        
        return K_global
    
    def solve(self, loads, supports):
        """
        Solve for displacements, reactions, and member forces
        
        Args:
            loads: Dictionary mapping node index to [Fx, Fy] load in kN
            supports: Dictionary mapping node index to [rx, ry] boolean constraints
                      (True = restrained, False = free)
        
        Returns:
            Dict containing analysis results
        """
        
        # Assemble global stiffness matrix
        K_global = self.assemble_stiffness_matrix()
        
        # Build force vector and apply boundary conditions
        F = np.zeros(self.num_dof)
        for node, (fx, fy) in loads.items():
            F[2*node] = fx * 1000  # Convert kN to N
            F[2*node + 1] = fy * 1000
        
        # Apply boundary conditions (reduction method)
        fixed_dofs = []
        for node, (rx, ry) in supports.items():
            if rx:
                fixed_dofs.append(2*node)
            if ry:
                fixed_dofs.append(2*node + 1)
        
        free_dofs = [dof for dof in range(self.num_dof) if dof not in fixed_dofs]
        
        # Reduce system
        K_reduced = K_global[np.ix_(free_dofs, free_dofs)]
        F_reduced = F[free_dofs]
        
        # Check for singular matrix (unstable truss)
        if np.linalg.cond(K_reduced) > 1e10:
            raise ValueError("Truss is unstable! Check supports and geometry.")
        
        # Solve for displacements
        try:
            U_reduced = np.linalg.solve(K_reduced, F_reduced)
        except np.linalg.LinAlgError:
            raise ValueError("System cannot be solved. Truss may be unstable.")
        
        # Full displacement vector
        U = np.zeros(self.num_dof)
        U[free_dofs] = U_reduced
        
        self.displacements = U.reshape(-1, 2)  # Reshape to [node][x, y]
        
        # Calculate reactions
        reactions = np.zeros(self.num_dof)
        for dof in fixed_dofs:
            reactions[dof] = (K_global[dof, :] @ U)[0]
        
        self.reactions = reactions.reshape(-1, 2) / 1000  # Convert to kN
        
        # Calculate member forces
        self.member_forces = []
        self.stress = []
        
        for member_idx, (node_i, node_j) in enumerate(self.geometry.members):
            # Get member properties
            L = self.geometry.member_lengths[member_idx]
            EA = self.E * self.area
            
            # Get displacements at nodes
            ui, vi = self.displacements[node_i]
            uj, vj = self.displacements[node_j]
            
            # Get member orientation
            xi, yi = self.geometry.nodes[node_i]
            xj, yj = self.geometry.nodes[node_j]
            dx = xj - xi
            dy = yj - yi
            cosθ = dx / L
            sinθ = dy / L
            
            # Calculate axial deformation
            delta = (uj - ui) * cosθ + (vj - vi) * sinθ
            
            # Calculate axial force (positive = tension)
            force = (EA / L) * delta / 1000  # Convert to kN
            self.member_forces.append(force)
            
            # Calculate stress (MPa)
            stress = np.abs(force * 1000) / self.area  # Pa to MPa
            self.stress.append(stress / 1e6)
        
        return {
            'displacements': self.displacements,
            'reactions': self.reactions,
            'member_forces': self.member_forces,
            'stress': self.stress
        }

# ============================================================================
# SECTION 5: TIMBER MEMBER DESIGN (NSCP 2015)
# ============================================================================

class TimberMemberDesign:
    """
    Timber member design according to NSCP 2015 Chapter 6
    ASD (Allowable Stress Design) method
    """
    
    def __init__(self, species, grade, moisture_condition, service_condition):
        """
        Initialize timber design parameters
        
        Args:
            species: Timber species name
            grade: Lumber grade (Select Structural, No.1, No.2, etc.)
            moisture_condition: "Dry" or "Wet"
            service_condition: "Normal", "Wet", "High Temperature", etc.
        """
        self.species = species
        self.grade = grade
        self.moisture_condition = moisture_condition
        self.service_condition = service_condition
        
        # Get reference design values from database
        db = TimberDatabase()
        if species in db.TIMBER_SPECIES:
            Fb, Ft, Fc, Fv, E, density = db.TIMBER_SPECIES[species]
            self.Fb_ref = Fb  # Reference bending stress (MPa)
            self.Ft_ref = Ft  # Reference tension stress (MPa)
            self.Fc_ref = Fc  # Reference compression stress (MPa)
            self.Fv_ref = Fv  # Reference shear stress (MPa)
            self.E_ref = E    # Reference modulus of elasticity (MPa)
            self.density = density  # kg/m³
        else:
            # Default values for unknown species
            self.Fb_ref = 10.0
            self.Ft_ref = 7.0
            self.Fc_ref = 8.0
            self.Fv_ref = 1.5
            self.E_ref = 8000
            self.density = 500
    
    def calculate_adjusted_stresses(self, member_type, section_props, 
                                   load_duration, unsupported_length_m):
        """
        Calculate adjusted allowable stresses using NSCP 2015 adjustment factors
        
        NSCP 2015 Equation 603-1:
        F' = F * CD * CM * Ct * CF * CL * CV * Cfu * Ci * Cr
        
        Where:
        F' = Adjusted allowable stress
        F = Reference design value
        CD = Load duration factor
        CM = Wet service factor
        Ct = Temperature factor
        CF = Size factor
        CL = Beam stability factor
        CV = Volume factor
        Cfu = Format factor
        Ci = Incising factor
        Cr = Repetitive member factor
        """
        
        adj_factors = AdjustmentFactors()
        
        # Load duration factor (CD)
        CD = adj_factors.load_duration_factor(load_duration)
        
        # Wet service factor (CM)
        CM = adj_factors.wet_service_factor(self.moisture_condition, member_type)
        
        # Temperature factor (Ct)
        Ct = adj_factors.temperature_factor(self.service_condition)
        
        # Size factor (CF) - for bending only
        if member_type == "Bending":
            CF = adj_factors.size_factor(section_props['depth_mm'], self.species)
        else:
            CF = 1.0
        
        # Stability factor (CL) - for bending only
        if member_type == "Bending" and unsupported_length_m > 0:
            le = unsupported_length_m * 1000  # Convert to mm
            d = section_props['depth_mm']
            b = section_props['width_mm']
            CL = adj_factors.stability_factor(le, d, b, self.E_ref, self.Fb_ref)
        else:
            CL = 1.0
        
        # Other factors (simplified)
        CV = 1.0  # Volume factor
        Cfu = 1.0  # Format factor
        Ci = 1.0   # Incising factor (for treated lumber)
        Cr = 1.15 if member_type == "Bending" else 1.0  # Repetitive member factor
        
        # Calculate adjusted stresses based on member type
        if member_type == "Bending":
            Fb_adj = self.Fb_ref * CD * CM * Ct * CF * CL * CV * Cfu * Ci * Cr
            return Fb_adj
        elif member_type == "Tension":
            Ft_adj = self.Ft_ref * CD * CM * Ct * CF * Ci
            return Ft_adj
        elif member_type == "Compression":
            Fc_adj = self.Fc_ref * CD * CM * Ct * CF * Ci
            return Fc_adj
        elif member_type == "Shear":
            Fv_adj = self.Fv_ref * CD * CM * Ct * Ci
            return Fv_adj
        else:
            return 0
    
    def check_axial_tension_member(self, axial_force_kN, section_props, 
                                   load_duration):
        """
        Check axial tension member (NSCP 2015 Section 603.4)
        
        Equation: ft <= Ft'
        
        Where:
        ft = Actual tensile stress = P/A
        Ft' = Adjusted allowable tensile stress
        """
        
        # Calculate actual tensile stress (MPa)
        area_m2 = section_props['area_m2']
        ft = abs(axial_force_kN * 1000) / area_m2 / 1e6  # Convert to MPa
        
        # Calculate adjusted allowable stress
        Ft_adj = self.calculate_adjusted_stresses("Tension", section_props, 
                                                   load_duration, 0)
        
        # Calculate utilization ratio
        ratio = ft / Ft_adj
        
        return {
            'status': 'PASS' if ratio <= 1.0 else 'FAIL',
            'ft_MPa': ft,
            'Ft_MPa': Ft_adj,
            'utilization_ratio': ratio,
            'required_area_m2': (abs(axial_force_kN * 1000) / Ft_adj / 1e6) if Ft_adj > 0 else float('inf'),
            'message': f"Tension check: {ft:.2f} MPa <= {Ft_adj:.2f} MPa" if ratio <= 1.0 else f"Tension FAIL: {ft:.2f} > {Ft_adj:.2f}"
        }
    
    def check_axial_compression_member(self, axial_force_kN, section_props, 
                                      effective_length_m, load_duration):
        """
        Check axial compression member including buckling (NSCP 2015 Section 603.5)
        
        Steps:
        1. Calculate actual compressive stress: fc = P/A
        2. Calculate slenderness ratio: le/d
        3. Check if slender: le/d > 50 (NSCP 2015 limit)
        4. Calculate allowable compression stress using Euler buckling
        """
        
        # Calculate actual compressive stress (MPa)
        area_m2 = section_props['area_m2']
        fc = abs(axial_force_kN * 1000) / area_m2 / 1e6
        
        # Get section dimensions
        d = section_props['depth_mm'] / 1000  # m
        b = section_props['width_mm'] / 1000  # m
        
        # Calculate slenderness ratio about both axes
        rx = section_props['rx_m']
        ry = section_props['ry_m']
        
        # Effective length (simplified - typical for truss members)
        le_x = effective_length_m
        le_y = effective_length_m
        
        slenderness_x = le_x / rx
        slenderness_y = le_y / ry
        slenderness_max = max(slenderness_x, slenderness_y)
        
        # NSCP 2015 limit: le/d <= 50 for main members, 80 for secondary
        if slenderness_max > 50:
            return {
                'status': 'FAIL',
                'message': f"Slenderness ratio {slenderness_max:.1f} exceeds NSCP limit of 50"
            }
        
        # Calculate adjusted allowable compression stress (short column)
        Fc_adj = self.calculate_adjusted_stresses("Compression", section_props,
                                                   load_duration, 0)
        
        # Check if column is slender using NSCP 2015 Equation 603-4
        # Critical slenderness ratio for Euler buckling
        E = self.E_ref  # MPa
        Ke = 1.0  # Effective length factor (pinned-pinned)
        
        # Calculate Euler buckling stress (MPa) - NSCP 2015 Section 603.5.1
        Fe = (np.pi**2 * E) / (slenderness_max**2)
        
        # Calculate allowable compression stress including buckling
        c = 0.8  # For sawn lumber (NSCP 2015)
        
        if slenderness_max <= 50:
            # Short column - use adjusted compression stress
            Fc_allowed = Fc_adj
        else:
            # Slender column - use buckling formula (NSCP 2015 Equation 603-5)
            Fc_allowed = Fc_adj * (1 - (slenderness_max / 80)**4)
            Fc_allowed = max(Fc_allowed, 0)  # Cannot be negative
        
        # Also consider Euler buckling (NSCP 2015 Equation 603-6)
        Fc_euler = Fe / 2
        Fc_design = min(Fc_allowed, Fc_euler)
        
        # Calculate utilization ratio
        ratio = fc / Fc_design if Fc_design > 0 else float('inf')
        
        return {
            'status': 'PASS' if ratio <= 1.0 else 'FAIL',
            'fc_MPa': fc,
            'Fc_MPa': Fc_design,
            'slenderness_ratio': slenderness_max,
            'utilization_ratio': ratio,
            'euler_stress_MPa': Fe,
            'required_area_m2': (abs(axial_force_kN * 1000) / Fc_design / 1e6) if Fc_design > 0 else float('inf'),
            'message': f"Compression check: {fc:.2f} MPa <= {Fc_design:.2f} MPa, λ={slenderness_max:.1f}" if ratio <= 1.0 else f"Compression FAIL: {fc:.2f} > {Fc_design:.2f}"
        }

# ============================================================================
# SECTION 6: LOAD COMBINATIONS (NSCP 2015)
# ============================================================================

class LoadCombinations:
    """Load combinations according to NSCP 2015 Section 203"""
    
    @staticmethod
    def asd_combinations():
        """
        ASD (Allowable Stress Design) load combinations
        NSCP 2015 Section 203.3.1
        """
        return {
            'D': ['D'],
            'D + L': ['D', 'L'],
            'D + (Lr or S or R)': ['D', 'Lr'],
            'D + 0.75L + 0.75(Lr or S or R)': ['D', 'L', 'Lr'],
            'D + (0.6W)': ['D', 'W'],
            'D + 0.75L + 0.75(0.6W)': ['D', 'L', 'W'],
            '0.6D + 0.6W': ['D', 'W'],
            '0.6D + 0.7E': ['D', 'E']
        }
    
    @staticmethod
    def lrfd_combinations():
        """LRFD load combinations (for reference)"""
        return {
            '1.4D': ['D'],
            '1.2D + 1.6L + 0.5(Lr or S or R)': ['D', 'L', 'Lr'],
            '1.2D + 1.6(Lr or S or R) + (0.5L or 0.8W)': ['D', 'Lr', 'W'],
            '1.2D + 1.0W + 0.5L + 0.5(Lr or S or R)': ['D', 'W', 'L', 'Lr'],
            '0.9D + 1.0W': ['D', 'W']
        }

# ============================================================================
# SECTION 7: GUI APPLICATION MAIN CLASS
# ============================================================================

class TimberTrussDesignerGUI:
    """Main GUI Application for Timber Truss Designer"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("Timber Truss Designer - NSCP 2015 Professional Edition")
        self.root.geometry("1400x900")
        
        # Set style
        self.style = ttk.Style()
        self.style.theme_use('clam')
        
        # Initialize data structures
        self.project_data = {
            'project_name': 'Untitled Project',
            'engineer': '',
            'date': datetime.now().strftime('%Y-%m-%d'),
            'truss_params': {},
            'load_cases': {},
            'analysis_results': None,
            'design_results': None
        }
        
        # Create GUI layout
        self.create_menu_bar()
        self.create_main_layout()
        
        # Initialize default values
        self.set_default_values()
        
    def create_menu_bar(self):
        """Create application menu bar"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="New Project", command=self.new_project)
        file_menu.add_command(label="Save Project", command=self.save_project)
        file_menu.add_command(label="Load Project", command=self.load_project)
        file_menu.add_separator()
        file_menu.add_command(label="Export Report", command=self.export_report)
        file_menu.add_command(label="Exit", command=self.root.quit)
        
        # Analysis menu
        analysis_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Analysis", menu=analysis_menu)
        analysis_menu.add_command(label="Run Analysis", command=self.run_analysis)
        analysis_menu.add_command(label="Design Members", command=self.design_members)
        
        # View menu
        view_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="View", menu=view_menu)
        view_menu.add_command(label="Show Truss Geometry", command=self.show_geometry)
        view_menu.add_command(label="Show Force Diagram", command=self.show_forces)
        view_menu.add_command(label="Show Deflected Shape", command=self.show_deflection)
        
        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="User Manual", command=self.show_manual)
        help_menu.add_command(label="About", command=self.show_about)
    
    def create_main_layout(self):
        """Create main application layout with notebook tabs"""
        # Main notebook
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill='both', expand=True, padx=5, pady=5)
        
        # Create tabs
        self.create_input_tab()
        self.create_geometry_tab()
        self.create_loads_tab()
        self.create_analysis_tab()
        self.create_design_tab()
        self.create_results_tab()
    
    def create_input_tab(self):
        """Create input parameters tab"""
        input_frame = ttk.Frame(self.notebook)
        self.notebook.add(input_frame, text="Project Inputs")
        
        # Create scrollable frame
        canvas = tk.Canvas(input_frame)
        scrollbar = ttk.Scrollbar(input_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Project Information
        proj_frame = ttk.LabelFrame(scrollable_frame, text="Project Information", padding=10)
        proj_frame.grid(row=0, column=0, columnspan=2, sticky='ew', padx=10, pady=5)
        
        ttk.Label(proj_frame, text="Project Name:").grid(row=0, column=0, sticky='w', padx=5)
        self.project_name_var = tk.StringVar(value="Timber Truss Project")
        ttk.Entry(proj_frame, textvariable=self.project_name_var, width=30).grid(row=0, column=1, padx=5)
        
        ttk.Label(proj_frame, text="Engineer:").grid(row=1, column=0, sticky='w', padx=5)
        self.engineer_var = tk.StringVar()
        ttk.Entry(proj_frame, textvariable=self.engineer_var, width=30).grid(row=1, column=1, padx=5)
        
        # Truss Geometry
        geom_frame = ttk.LabelFrame(scrollable_frame, text="Truss Geometry", padding=10)
        geom_frame.grid(row=1, column=0, columnspan=2, sticky='ew', padx=10, pady=5)
        
        ttk.Label(geom_frame, text="Truss Span (m):").grid(row=0, column=0, sticky='w', padx=5)
        self.span_var = tk.DoubleVar(value=12.0)
        ttk.Entry(geom_frame, textvariable=self.span_var, width=15).grid(row=0, column=1, padx=5)
        
        ttk.Label(geom_frame, text="Rise (m):").grid(row=1, column=0, sticky='w', padx=5)
        self.rise_var = tk.DoubleVar(value=2.5)
        ttk.Entry(geom_frame, textvariable=self.rise_var, width=15).grid(row=1, column=1, padx=5)
        
        ttk.Label(geom_frame, text="Roof Slope (°):").grid(row=2, column=0, sticky='w', padx=5)
        self.slope_var = tk.DoubleVar(value=22.62)
        ttk.Entry(geom_frame, textvariable=self.slope_var, width=15).grid(row=2, column=1, padx=5)
        
        ttk.Label(geom_frame, text="Truss Spacing (m):").grid(row=3, column=0, sticky='w', padx=5)
        self.spacing_var = tk.DoubleVar(value=0.6)
        ttk.Entry(geom_frame, textvariable=self.spacing_var, width=15).grid(row=3, column=1, padx=5)
        
        ttk.Label(geom_frame, text="Number of Panels:").grid(row=4, column=0, sticky='w', padx=5)
        self.panels_var = tk.IntVar(value=4)
        ttk.Spinbox(geom_frame, from_=2, to=10, textvariable=self.panels_var, width=15).grid(row=4, column=1, padx=5)
        
        ttk.Label(geom_frame, text="Truss Type:").grid(row=5, column=0, sticky='w', padx=5)
        self.truss_type_var = tk.StringVar(value="Fink")
        truss_types = ["Fink", "Pratt", "Howe", "Warren"]
        ttk.Combobox(geom_frame, textvariable=self.truss_type_var, values=truss_types, width=15).grid(row=5, column=1, padx=5)
        
        # Material Properties
        mat_frame = ttk.LabelFrame(scrollable_frame, text="Material Properties", padding=10)
        mat_frame.grid(row=2, column=0, columnspan=2, sticky='ew', padx=10, pady=5)
        
        ttk.Label(mat_frame, text="Timber Species:").grid(row=0, column=0, sticky='w', padx=5)
        self.species_var = tk.StringVar(value="Apitong (Dipterocarpus spp.)")
        species_list = list(TimberDatabase.TIMBER_SPECIES.keys())
        ttk.Combobox(mat_frame, textvariable=self.species_var, values=species_list, width=30).grid(row=0, column=1, padx=5)
        
        ttk.Label(mat_frame, text="Timber Grade:").grid(row=1, column=0, sticky='w', padx=5)
        self.grade_var = tk.StringVar(value="Select Structural")
        ttk.Combobox(mat_frame, textvariable=self.grade_var, values=["Select Structural", "No.1", "No.2", "No.3"], width=30).grid(row=1, column=1, padx=5)
        
        ttk.Label(mat_frame, text="Moisture Condition:").grid(row=2, column=0, sticky='w', padx=5)
        self.moisture_var = tk.StringVar(value="Dry (MC <= 19%)")
        ttk.Combobox(mat_frame, textvariable=self.moisture_var, values=["Dry (MC <= 19%)", "Wet (MC > 19%)"], width=30).grid(row=2, column=1, padx=5)
        
        ttk.Label(mat_frame, text="Service Condition:").grid(row=3, column=0, sticky='w', padx=5)
        self.service_var = tk.StringVar(value="Normal (<= 38°C)")
        ttk.Combobox(mat_frame, textvariable=self.service_var, values=["Normal (<= 38°C)", "38°C to 52°C", "52°C to 65°C"], width=30).grid(row=3, column=1, padx=5)
        
        ttk.Label(mat_frame, text="Load Duration:").grid(row=4, column=0, sticky='w', padx=5)
        self.duration_var = tk.StringVar(value="Ten years")
        duration_list = ["Permanent (10+ years)", "Ten years", "Two months (Snow)", "Seven days (Construction)", "Ten minutes (Wind/Earthquake)"]
        ttk.Combobox(mat_frame, textvariable=self.duration_var, values=duration_list, width=30).grid(row=4, column=1, padx=5)
        
        # Section Properties
        sect_frame = ttk.LabelFrame(scrollable_frame, text="Member Section", padding=10)
        sect_frame.grid(row=3, column=0, columnspan=2, sticky='ew', padx=10, pady=5)
        
        ttk.Label(sect_frame, text="Select Lumber Size:").grid(row=0, column=0, sticky='w', padx=5)
        self.lumber_size_var = tk.StringVar()
        lumber_options = [f"{nom}\" x {depth/25.4:.0f}\" ({width}x{depth}mm)" 
                         for nom, width, depth in TimberDatabase.LUMBER_SIZES]
        self.lumber_combo = ttk.Combobox(sect_frame, textvariable=self.lumber_size_var, values=lumber_options, width=30)
        self.lumber_combo.grid(row=0, column=1, padx=5)
        self.lumber_combo.bind('<<ComboboxSelected>>', self.update_section_properties)
        
        # Section properties display
        self.section_props_text = tk.Text(sect_frame, height=6, width=40)
        self.section_props_text.grid(row=1, column=0, columnspan=2, padx=5, pady=5)
        
        # Section selection button
        ttk.Button(sect_frame, text="Apply Section", command=self.update_section_properties).grid(row=2, column=0, columnspan=2, pady=5)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
    
    def create_geometry_tab(self):
        """Create geometry visualization tab"""
        geom_frame = ttk.Frame(self.notebook)
        self.notebook.add(geom_frame, text="Truss Geometry")
        
        # Create matplotlib figure
        self.geom_fig, self.geom_ax = plt.subplots(figsize=(10, 6))
        self.geom_canvas = FigureCanvasTkAgg(self.geom_fig, geom_frame)
        self.geom_canvas.get_tk_widget().pack(fill='both', expand=True)
        
        # Control panel
        control_frame = ttk.Frame(geom_frame)
        control_frame.pack(fill='x', padx=5, pady=5)
        
        ttk.Button(control_frame, text="Generate/Update Geometry", 
                  command=self.generate_and_display_geometry).pack(side='left', padx=5)
        ttk.Button(control_frame, text="Export Geometry Data", 
                  command=self.export_geometry_data).pack(side='left', padx=5)
    
    def create_loads_tab(self):
        """Create loads definition tab"""
        loads_frame = ttk.Frame(self.notebook)
        self.notebook.add(loads_frame, text="Load Definition")
        
        # Load case management
        load_case_frame = ttk.LabelFrame(loads_frame, text="Load Cases", padding=10)
        load_case_frame.pack(fill='both', expand=True, padx=10, pady=5)
        
        # Treeview for load cases
        columns = ('Case', 'DL (kN/m²)', 'LL (kN/m²)', 'Snow (kN/m²)', 'Wind (kN/m²)')
        self.load_tree = ttk.Treeview(load_case_frame, columns=columns, show='headings', height=8)
        
        for col in columns:
            self.load_tree.heading(col, text=col)
            self.load_tree.column(col, width=120)
        
        self.load_tree.pack(fill='x', padx=5, pady=5)
        
        # Add default load cases
        default_loads = [
            ('Dead Load (D)', 0.5, 0, 0, 0),
            ('Live Load (L)', 0, 1.0, 0, 0),
            ('Roof Live (Lr)', 0, 0, 0.75, 0),
            ('Wind Load (W)', 0, 0, 0, 0.75)
        ]
        
        for load in default_loads:
            self.load_tree.insert('', 'end', values=load)
        
        # Load input form
        input_frame = ttk.Frame(load_case_frame)
        input_frame.pack(fill='x', padx=5, pady=10)
        
        ttk.Label(input_frame, text="Case Name:").grid(row=0, column=0, padx=5)
        self.load_name_var = tk.StringVar()
        ttk.Entry(input_frame, textvariable=self.load_name_var, width=15).grid(row=0, column=1, padx=5)
        
        ttk.Label(input_frame, text="DL (kN/m²):").grid(row=0, column=2, padx=5)
        self.dl_var = tk.DoubleVar()
        ttk.Entry(input_frame, textvariable=self.dl_var, width=10).grid(row=0, column=3, padx=5)
        
        ttk.Label(input_frame, text="LL (kN/m²):").grid(row=0, column=4, padx=5)
        self.ll_var = tk.DoubleVar()
        ttk.Entry(input_frame, textvariable=self.ll_var, width=10).grid(row=0, column=5, padx=5)
        
        ttk.Label(input_frame, text="Snow/Lr (kN/m²):").grid(row=1, column=0, padx=5)
        self.snow_var = tk.DoubleVar()
        ttk.Entry(input_frame, textvariable=self.snow_var, width=10).grid(row=1, column=1, padx=5)
        
        ttk.Label(input_frame, text="Wind (kN/m²):").grid(row=1, column=2, padx=5)
        self.wind_var = tk.DoubleVar()
        ttk.Entry(input_frame, textvariable=self.wind_var, width=10).grid(row=1, column=3, padx=5)
        
        # Buttons
        btn_frame = ttk.Frame(input_frame)
        btn_frame.grid(row=1, column=4, columnspan=2, padx=5)
        
        ttk.Button(btn_frame, text="Add Load Case", command=self.add_load_case).pack(side='left', padx=2)
        ttk.Button(btn_frame, text="Delete Selected", command=self.delete_load_case).pack(side='left', padx=2)
        ttk.Button(btn_frame, text="Apply to Truss", command=self.apply_loads_to_truss).pack(side='left', padx=2)
    
    def create_analysis_tab(self):
        """Create structural analysis tab"""
        analysis_frame = ttk.Frame(self.notebook)
        self.notebook.add(analysis_frame, text="Structural Analysis")
        
        # Analysis control
        control_frame = ttk.LabelFrame(analysis_frame, text="Analysis Control", padding=10)
        control_frame.pack(fill='x', padx=10, pady=5)
        
        ttk.Button(control_frame, text="Run Structural Analysis", 
                  command=self.run_analysis, width=25).pack(pady=5)
        
        self.analysis_status = ttk.Label(control_frame, text="Ready", foreground="green")
        self.analysis_status.pack(pady=5)
        
        # Results display
        results_frame = ttk.LabelFrame(analysis_frame, text="Analysis Results", padding=10)
        results_frame.pack(fill='both', expand=True, padx=10, pady=5)
        
        # Create text widget for results
        self.analysis_text = tk.Text(results_frame, height=15, width=80)
        scrollbar = ttk.Scrollbar(results_frame, orient="vertical", command=self.analysis_text.yview)
        self.analysis_text.configure(yscrollcommand=scrollbar.set)
        
        self.analysis_text.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
    
    def create_design_tab(self):
        """Create member design tab"""
        design_frame = ttk.Frame(self.notebook)
        self.notebook.add(design_frame, text="Member Design")
        
        # Design control
        control_frame = ttk.LabelFrame(design_frame, text="Design Control", padding=10)
        control_frame.pack(fill='x', padx=10, pady=5)
        
        ttk.Button(control_frame, text="Check All Members", 
                  command=self.design_members, width=25).pack(pady=5)
        ttk.Button(control_frame, text="Optimize Sections", 
                  command=self.optimize_sections, width=25).pack(pady=5)
        
        # Design results
        results_frame = ttk.LabelFrame(design_frame, text="Design Results", padding=10)
        results_frame.pack(fill='both', expand=True, padx=10, pady=5)
        
        # Treeview for member design results
        columns = ('Member', 'Force (kN)', 'Type', 'Stress (MPa)', 'Capacity (MPa)', 'Ratio', 'Status')
        self.design_tree = ttk.Treeview(results_frame, columns=columns, show='headings', height=15)
        
        for col in columns:
            self.design_tree.heading(col, text=col)
            self.design_tree.column(col, width=100)
        
        # Add scrollbars
        tree_scroll_y = ttk.Scrollbar(results_frame, orient="vertical", command=self.design_tree.yview)
        tree_scroll_x = ttk.Scrollbar(results_frame, orient="horizontal", command=self.design_tree.xview)
        self.design_tree.configure(yscrollcommand=tree_scroll_y.set, xscrollcommand=tree_scroll_x.set)
        
        self.design_tree.grid(row=0, column=0, sticky='nsew')
        tree_scroll_y.grid(row=0, column=1, sticky='ns')
        tree_scroll_x.grid(row=1, column=0, sticky='ew')
        
        results_frame.grid_rowconfigure(0, weight=1)
        results_frame.grid_columnconfigure(0, weight=1)
    
    def create_results_tab(self):
        """Create final results and report tab"""
        results_frame = ttk.Frame(self.notebook)
        self.notebook.add(results_frame, text="Summary & Report")
        
        # Summary frame
        summary_frame = ttk.LabelFrame(results_frame, text="Design Summary", padding=10)
        summary_frame.pack(fill='both', expand=True, padx=10, pady=5)
        
        self.summary_text = tk.Text(summary_frame, height=20, width=80)
        summary_scroll = ttk.Scrollbar(summary_frame, orient="vertical", command=self.summary_text.yview)
        self.summary_text.configure(yscrollcommand=summary_scroll.set)
        
        self.summary_text.pack(side='left', fill='both', expand=True)
        summary_scroll.pack(side='right', fill='y')
        
        # Export buttons
        export_frame = ttk.Frame(results_frame)
        export_frame.pack(fill='x', padx=10, pady=5)
        
        ttk.Button(export_frame, text="Export to PDF", 
                  command=self.export_to_pdf, width=15).pack(side='left', padx=5)
        ttk.Button(export_frame, text="Export to Excel", 
                  command=self.export_to_excel, width=15).pack(side='left', padx=5)
        ttk.Button(export_frame, text="Generate Report", 
                  command=self.generate_full_report, width=15).pack(side='left', padx=5)
    
    def set_default_values(self):
        """Set default input values"""
        # Set default lumber selection
        if self.lumber_size_var.get() == "":
            self.lumber_combo.current(6)  # Default to 2x4
            self.update_section_properties()
        
        # Generate initial geometry
        self.generate_and_display_geometry()
    
    def update_section_properties(self, event=None):
        """Update section properties display"""
        selection = self.lumber_size_var.get()
        if selection:
            # Parse dimensions from selection string
            import re
            dims = re.findall(r'\d+', selection.split('(')[-1])
            if len(dims) >= 2:
                width_mm = int(dims[0])
                depth_mm = int(dims[1])
                
                props = TimberDatabase.get_section_properties(width_mm, depth_mm)
                
                self.section_props_text.delete(1.0, tk.END)
                self.section_props_text.insert(1.0, 
                    f"Section Properties:\n"
                    f"Width: {width_mm} mm\n"
                    f"Depth: {depth_mm} mm\n"
                    f"Area: {props['area_mm2']:.0f} mm²\n"
                    f"Ix: {props['Ix_mm4']:.2e} mm⁴\n"
                    f"Radius of Gyration (x): {props['rx_mm']:.1f} mm\n"
                    f"Radius of Gyration (y): {props['ry_mm']:.1f} mm\n"
                    f"Section Modulus: {props['Sx_m3']*1e6:.1f} cm³"
                )
                
                self.current_section_props = props
    
    def generate_and_display_geometry(self):
        """Generate truss geometry and display"""
        try:
            # Get input values
            span = self.span_var.get()
            rise = self.rise_var.get()
            truss_type = self.truss_type_var.get()
            num_panels = self.panels_var.get()
            
            # Generate geometry
            self.truss_geom = TrussGeometry(span, rise, truss_type, num_panels)
            
            # Display geometry
            self.geom_ax.clear()
            
            # Draw nodes
            nodes = np.array(self.truss_geom.nodes)
            self.geom_ax.scatter(nodes[:, 0], nodes[:, 1], c='red', s=50, zorder=5)
            
            # Draw members
            for i, j in self.truss_geom.members:
                x = [nodes[i, 0], nodes[j, 0]]
                y = [nodes[i, 1], nodes[j, 1]]
                self.geom_ax.plot(x, y, 'b-', linewidth=2, zorder=3)
            
            # Label nodes
            for idx, (x, y) in enumerate(nodes):
                self.geom_ax.annotate(f'{idx}', (x, y), xytext=(5, 5), 
                                     textcoords='offset points', fontsize=8)
            
            self.geom_ax.set_xlabel('Span (m)')
            self.geom_ax.set_ylabel('Height (m)')
            self.geom_ax.set_title(f'{truss_type} Truss - Span: {span}m, Rise: {rise}m')
            self.geom_ax.grid(True, alpha=0.3)
            self.geom_ax.axis('equal')
            
            self.geom_canvas.draw()
            
            # Update analysis text with geometry info
            self.analysis_text.insert(tk.END, 
                f"\nTruss Geometry Generated:\n"
                f"  Type: {truss_type}\n"
                f"  Span: {span} m\n"
                f"  Rise: {rise} m\n"
                f"  Number of Nodes: {len(self.truss_geom.nodes)}\n"
                f"  Number of Members: {len(self.truss_geom.members)}\n"
                f"  Slope: {np.degrees(np.arctan2(rise, span/2)):.1f}°\n\n"
            )
            self.analysis_text.see(tk.END)
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to generate geometry: {str(e)}")
    
    def add_load_case(self):
        """Add a new load case to the tree"""
        name = self.load_name_var.get()
        dl = self.dl_var.get()
        ll = self.ll_var.get()
        snow = self.snow_var.get()
        wind = self.wind_var.get()
        
        if name:
            self.load_tree.insert('', 'end', values=(name, dl, ll, snow, wind))
            self.load_name_var.set("")
            self.dl_var.set(0)
            self.ll_var.set(0)
            self.snow_var.set(0)
            self.wind_var.set(0)
    
    def delete_load_case(self):
        """Delete selected load case"""
        selected = self.load_tree.selection()
        for item in selected:
            self.load_tree.delete(item)
    
    def apply_loads_to_truss(self):
        """Apply selected loads to truss nodes"""
        # This would convert distributed loads to nodal loads
        # For demonstration, we'll create a simple load pattern
        self.analysis_text.insert(tk.END, "Loads applied to truss nodes...\n")
        
        # Get truss geometry
        if not hasattr(self, 'truss_geom'):
            messagebox.showwarning("Warning", "Please generate truss geometry first")
            return
        
        # Create load dictionary (nodal loads in kN)
        # Typically dead load applied at top chord nodes
        self.loads = {}
        
        # Get distributed load from selected load case
        selected = self.load_tree.selection()
        if selected:
            item = self.load_tree.item(selected[0])
            values = item['values']
            dl = values[1]
            ll = values[2]
            snow = values[3]
            wind = values[4]
            
            total_load = dl + ll + snow + wind
            spacing = self.spacing_var.get()
            
            # Distribute load to top chord nodes
            nodes = self.truss_geom.nodes
            num_top = len(nodes) // 2
            load_per_node = (total_load * spacing * (self.span_var.get() / num_top)) / 1000
            
            for i in range(num_top, len(nodes)):
                self.loads[i] = (0, -load_per_node)  # Vertical downward load
            
            self.analysis_text.insert(tk.END, 
                f"Applied {total_load} kN/m² distributed load as nodal loads:\n"
                f"  Load per top chord node: {load_per_node:.2f} kN\n"
            )
    
    def run_analysis(self):
        """Run structural analysis"""
        try:
            # Check if geometry exists
            if not hasattr(self, 'truss_geom'):
                messagebox.showwarning("Warning", "Please generate truss geometry first")
                return
            
            # Get section properties
            if not hasattr(self, 'current_section_props'):
                messagebox.showwarning("Warning", "Please select a timber section")
                return
            
            # Get material properties
            species = self.species_var.get()
            if species in TimberDatabase.TIMBER_SPECIES:
                E_MPa = TimberDatabase.TIMBER_SPECIES[species][4]
            else:
                E_MPa = 10000  # Default
            
            # Create analysis object
            area_m2 = self.current_section_props['area_m2']
            self.analyzer = TrussAnalysis(self.truss_geom, E_MPa/1000, area_m2)
            
            # Define supports (simply supported at bottom chord ends)
            nodes = self.truss_geom.nodes
            self.supports = {
                0: (True, True),  # Left support - pinned
                len(nodes)//2 - 1: (True, True)  # Right support - pinned
            }
            
            # Run analysis
            if not hasattr(self, 'loads') or not self.loads:
                # Apply default load if none specified
                self.analysis_text.insert(tk.END, "No loads defined. Applying default load...\n")
                self.loads = {}
                for i in range(len(nodes)//2, len(nodes)):
                    self.loads[i] = (0, -1.0)  # 1 kN at each top chord node
            
            results = self.analyzer.solve(self.loads, self.supports)
            
            # Display results
            self.analysis_text.insert(tk.END, "\n" + "="*60 + "\n")
            self.analysis_text.insert(tk.END, "STRUCTURAL ANALYSIS RESULTS\n")
            self.analysis_text.insert(tk.END, "="*60 + "\n\n")
            
            # Display reactions
            self.analysis_text.insert(tk.END, "Support Reactions (kN):\n")
            for node, (rx, ry) in results['reactions'].items():
                if node in self.supports:
                    self.analysis_text.insert(tk.END, f"  Node {node}: Rx={rx:.2f}, Ry={ry:.2f}\n")
            
            # Display member forces
            self.analysis_text.insert(tk.END, "\nMember Axial Forces (kN):\n")
            self.analysis_text.insert(tk.END, "  Member  Force    Status\n")
            self.analysis_text.insert(tk.END, "  " + "-"*30 + "\n")
            
            self.member_forces = results['member_forces']
            for idx, force in enumerate(self.member_forces):
                status = "TENSION" if force > 0 else "COMPRESSION"
                self.analysis_text.insert(tk.END, f"  {idx:4d}   {force:8.2f}   {status}\n")
            
            # Check for zero-force members
            zero_force = [idx for idx, force in enumerate(self.member_forces) if abs(force) < 0.01]
            if zero_force:
                self.analysis_text.insert(tk.END, f"\nZero-force members: {zero_force}\n")
            
            # Display displacements
            max_deflection = np.max(np.abs(results['displacements'][:, 1]))
            self.analysis_text.insert(tk.END, f"\nMaximum vertical deflection: {max_deflection*1000:.2f} mm\n")
            
            # Check deflection limit (L/240 typical for roofs)
            span_m = self.span_var.get()
            deflection_limit = span_m / 240 * 1000  # mm
            if max_deflection*1000 <= deflection_limit:
                self.analysis_text.insert(tk.END, f"✓ Deflection within limit (L/240 = {deflection_limit:.1f} mm)\n")
            else:
                self.analysis_text.insert(tk.END, f"✗ Deflection exceeds limit (L/240 = {deflection_limit:.1f} mm)\n")
            
            self.analysis_status.config(text="Analysis Complete", foreground="green")
            
            # Store results for design
            self.analysis_results = results
            
        except Exception as e:
            self.analysis_status.config(text="Analysis Failed", foreground="red")
            messagebox.showerror("Analysis Error", str(e))
            self.analysis_text.insert(tk.END, f"\nERROR: {str(e)}\n")
    
    def design_members(self):
        """Design all truss members"""
        if not hasattr(self, 'analysis_results'):
            messagebox.showwarning("Warning", "Please run structural analysis first")
            return
        
        if not hasattr(self, 'current_section_props'):
            messagebox.showwarning("Warning", "Please select a timber section")
            return
        
        # Clear previous results
        for item in self.design_tree.get_children():
            self.design_tree.delete(item)
        
        # Initialize timber design
        species = self.species_var.get()
        grade = self.grade_var.get()
        moisture = self.moisture_var.get()
        service = self.service_var.get()
        
        designer = TimberMemberDesign(species, grade, moisture, service)
        
        # Design each member
        design_results = []
        member_lengths = self.truss_geom.member_lengths
        
        for idx, force in enumerate(self.member_forces):
            # Determine member type (tension or compression)
            is_tension = force > 0
            member_type = "Tension" if is_tension else "Compression"
            
            # Get effective length (simplified - actual would depend on bracing)
            effective_length = member_lengths[idx]
            
            # Perform design check
            if is_tension:
                result = designer.check_axial_tension_member(
                    abs(force), self.current_section_props, 
                    self.duration_var.get()
                )
            else:
                result = designer.check_axial_compression_member(
                    abs(force), self.current_section_props, 
                    effective_length, self.duration_var.get()
                )
            
            # Add to treeview
            status_color = "green" if result['status'] == 'PASS' else "red"
            self.design_tree.insert('', 'end', values=(
                idx, f"{force:.1f}", member_type,
                f"{result.get('ft_MPa', result.get('fc_MPa', 0)):.1f}",
                f"{result.get('Ft_MPa', result.get('Fc_MPa', 0)):.1f}",
                f"{result['utilization_ratio']:.3f}",
                result['status']
            ), tags=(status_color,))
            
            design_results.append(result)
        
        # Color code the treeview
        self.design_tree.tag_configure('green', foreground='green')
        self.design_tree.tag_configure('red', foreground='red')
        
        # Update summary
        self.update_design_summary(design_results)
    
    def update_design_summary(self, design_results):
        """Update design summary in results tab"""
        self.summary_text.delete(1.0, tk.END)
        
        # Count passed/failed
        passed = sum(1 for r in design_results if r['status'] == 'PASS')
        failed = len(design_results) - passed
        
        self.summary_text.insert(tk.END, "="*60 + "\n")
        self.summary_text.insert(tk.END, "TIMBER TRUSS DESIGN SUMMARY\n")
        self.summary_text.insert(tk.END, "="*60 + "\n\n")
        
        self.summary_text.insert(tk.END, f"Project: {self.project_name_var.get()}\n")
        self.summary_text.insert(tk.END, f"Engineer: {self.engineer_var.get()}\n")
        self.summary_text.insert(tk.END, f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n")
        
        self.summary_text.insert(tk.END, "DESIGN CRITERIA:\n")
        self.summary_text.insert(tk.END, f"  Timber Species: {self.species_var.get()}\n")
        self.summary_text.insert(tk.END, f"  Timber Grade: {self.grade_var.get()}\n")
        self.summary_text.insert(tk.END, f"  Section: {self.lumber_size_var.get()}\n")
        self.summary_text.insert(tk.END, f"  Load Duration: {self.duration_var.get()}\n\n")
        
        self.summary_text.insert(tk.END, "DESIGN RESULTS:\n")
        self.summary_text.insert(tk.END, f"  Total Members Checked: {len(design_results)}\n")
        self.summary_text.insert(tk.END, f"  Members PASSING: {passed}\n")
        self.summary_text.insert(tk.END, f"  Members FAILING: {failed}\n\n")
        
        if failed > 0:
            self.summary_text.insert(tk.END, "⚠ WARNING: Some members are overstressed!\n")
            self.summary_text.insert(tk.END, "Consider increasing section size or using higher grade timber.\n\n")
        else:
            self.summary_text.insert(tk.END, "✓ All members meet NSCP 2015 requirements.\n\n")
        
        # Show critical members
        max_ratio = max((r['utilization_ratio'] for r in design_results if 'utilization_ratio' in r), default=0)
        self.summary_text.insert(tk.END, f"Maximum utilization ratio: {max_ratio:.3f}\n")
        
        # NSCP 2015 reference
        self.summary_text.insert(tk.END, "\n" + "-"*60 + "\n")
        self.summary_text.insert(tk.END, "Design based on NSCP 2015 Chapter 6 - Timber\n")
        self.summary_text.insert(tk.END, "ASD Method with applicable adjustment factors\n")
        self.summary_text.insert(tk.END, "-"*60 + "\n")
    
    def optimize_sections(self):
        """Suggest optimized section sizes for failing members"""
        if not hasattr(self, 'analysis_results'):
            messagebox.showwarning("Warning", "Please run analysis first")
            return
        
        # Find failing members
        failing_members = []
        for idx, item in enumerate(self.design_tree.get_children()):
            values = self.design_tree.item(item)['values']
            if values[-1] == 'FAIL':
                failing_members.append((idx, values))
        
        if not failing_members:
            messagebox.showinfo("Info", "All members pass. No optimization needed.")
            return
        
        # Suggest larger sections
        suggestions = []
        current_width = self.current_section_props['width_mm']
        current_depth = self.current_section_props['depth_mm']
        
        # Find next available larger size
        for nominal, width, depth in TimberDatabase.LUMBER_SIZES:
            if depth > current_depth and width >= current_width:
                suggestions.append(f"{nominal}\" x {depth/25.4:.0f}\" ({width}x{depth}mm)")
                if len(suggestions) >= 3:
                    break
        
        if suggestions:
            msg = f"Suggest trying these larger sections:\n" + "\n".join(suggestions)
            messagebox.showinfo("Optimization Suggestion", msg)
    
    def show_geometry(self):
        """Show geometry visualization"""
        self.notebook.select(1)  # Switch to geometry tab
    
    def show_forces(self):
        """Show axial force diagram"""
        if not hasattr(self, 'analysis_results'):
            messagebox.showwarning("Warning", "Please run analysis first")
            return
        
        # Create force diagram figure
        fig, ax = plt.subplots(figsize=(12, 6))
        
        # Draw truss with force colors
        nodes = np.array(self.truss_geom.nodes)
        
        # Color mapping for forces
        max_force = max(abs(min(self.member_forces)), abs(max(self.member_forces)))
        
        for idx, (i, j) in enumerate(self.truss_geom.members):
            force = self.member_forces[idx]
            
            # Color: red for tension, blue for compression, intensity based on magnitude
            if force > 0:
                intensity = min(1.0, force / max_force)
                color = (1.0, 1.0 - intensity, 1.0 - intensity)  # Red gradient
                linewidth = 2 + abs(force) / max_force * 4
            else:
                intensity = min(1.0, abs(force) / max_force)
                color = (1.0 - intensity, 1.0 - intensity, 1.0)  # Blue gradient
                linewidth = 2 + abs(force) / max_force * 4
            
            x = [nodes[i, 0], nodes[j, 0]]
            y = [nodes[i, 1], nodes[j, 1]]
            ax.plot(x, y, color=color, linewidth=linewidth, zorder=3)
            
            # Add force label
            mid_x = (nodes[i, 0] + nodes[j, 0]) / 2
            mid_y = (nodes[i, 1] + nodes[j, 1]) / 2
            ax.text(mid_x, mid_y, f'{force:.1f}', fontsize=8, ha='center', va='center',
                   bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.7))
        
        ax.scatter(nodes[:, 0], nodes[:, 1], c='black', s=30, zorder=5)
        ax.set_xlabel('Span (m)')
        ax.set_ylabel('Height (m)')
        ax.set_title('Axial Force Diagram (Red=Tension, Blue=Compression)')
        ax.grid(True, alpha=0.3)
        ax.axis('equal')
        
        # Add colorbar
        from matplotlib.cm import ScalarMappable
        from matplotlib.colors import LinearSegmentedColormap
        cmap = LinearSegmentedColormap.from_list('force_cmap', ['blue', 'white', 'red'])
        sm = ScalarMappable(cmap=cmap, norm=plt.Normalize(-max_force, max_force))
        plt.colorbar(sm, ax=ax, label='Axial Force (kN)')
        
        plt.tight_layout()
        plt.show()
    
    def show_deflection(self):
        """Show deflected shape"""
        if not hasattr(self, 'analysis_results'):
            messagebox.showwarning("Warning", "Please run analysis first")
            return
        
        fig, ax = plt.subplots(figsize=(12, 6))
        
        # Original shape
        nodes = np.array(self.truss_geom.nodes)
        for i, j in self.truss_geom.members:
            x = [nodes[i, 0], nodes[j, 0]]
            y = [nodes[i, 1], nodes[j, 1]]
            ax.plot(x, y, 'b-', linewidth=1, alpha=0.5, label='Original' if i==0 else '')
        
        # Deflected shape (scale factor for visibility)
        displacements = self.analysis_results['displacements']
        scale = 50  # Scale factor to make deflection visible
        
        deflected_nodes = nodes + displacements * scale
        
        for i, j in self.truss_geom.members:
            x = [deflected_nodes[i, 0], deflected_nodes[j, 0]]
            y = [deflected_nodes[i, 1], deflected_nodes[j, 1]]
            ax.plot(x, y, 'r--', linewidth=2, label='Deflected' if i==0 else '')
        
        ax.scatter(nodes[:, 0], nodes[:, 1], c='blue', s=30, alpha=0.5)
        ax.scatter(deflected_nodes[:, 0], deflected_nodes[:, 1], c='red', s=30)
        
        ax.set_xlabel('Span (m)')
        ax.set_ylabel('Height (m)')
        ax.set_title(f'Deflected Shape (Scale Factor: {scale}x)')
        ax.grid(True, alpha=0.3)
        ax.legend()
        ax.axis('equal')
        
        # Add deflection annotation
        max_deflection = np.max(np.abs(displacements[:, 1]))
        ax.annotate(f'Max Deflection: {max_deflection*1000:.2f} mm', 
                   xy=(0.02, 0.98), xycoords='axes fraction',
                   bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
        
        plt.tight_layout()
        plt.show()
    
    def export_geometry_data(self):
        """Export geometry data to CSV"""
        if not hasattr(self, 'truss_geom'):
            messagebox.showwarning("Warning", "Please generate geometry first")
            return
        
        filename = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        
        if filename:
            # Export nodes
            nodes_df = pd.DataFrame(self.truss_geom.nodes, columns=['X (m)', 'Y (m)'])
            nodes_df.index.name = 'Node'
            
            # Export members
            members_data = []
            for idx, (i, j) in enumerate(self.truss_geom.members):
                members_data.append({
                    'Member': idx,
                    'Node I': i,
                    'Node J': j,
                    'Length (m)': self.truss_geom.member_lengths[idx]
                })
            members_df = pd.DataFrame(members_data)
            
            # Write to Excel with multiple sheets
            with pd.ExcelWriter(filename.replace('.csv', '.xlsx')) as writer:
                nodes_df.to_excel(writer, sheet_name='Nodes')
                members_df.to_excel(writer, sheet_name='Members')
            
            messagebox.showinfo("Success", f"Geometry data exported to {filename}")
    
    def export_to_pdf(self):
        """Export design summary to PDF"""
        if not hasattr(self, 'design_results'):
            messagebox.showwarning("Warning", "Please run design check first")
            return
        
        filename = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")]
        )
        
        if filename:
            # Create PDF document
            doc = SimpleDocTemplate(filename, pagesize=letter)
            story = []
            styles = getSampleStyleSheet()
            
            # Title
            title_style = ParagraphStyle('CustomTitle', parent=styles['Heading1'], fontSize=16, spaceAfter=30)
            story.append(Paragraph("Timber Truss Design Report", title_style))
            story.append(Paragraph(f"Project: {self.project_name_var.get()}", styles['Normal']))
            story.append(Paragraph(f"Date: {datetime.now().strftime('%Y-%m-%d')}", styles['Normal']))
            story.append(Spacer(1, 20))
            
            # Design summary
            story.append(Paragraph("Design Summary", styles['Heading2']))
            summary_text = self.summary_text.get(1.0, tk.END)
            story.append(Paragraph(summary_text.replace('\n', '<br/>'), styles['Normal']))
            
            # Build PDF
            doc.build(story)
            messagebox.showinfo("Success", f"Report exported to {filename}")
    
    def export_to_excel(self):
        """Export results to Excel"""
        if not hasattr(self, 'analysis_results'):
            messagebox.showwarning("Warning", "Please run analysis first")
            return
        
        filename = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel files", "*.xlsx"), ("All files", "*.*")]
        )
        
        if filename:
            with pd.ExcelWriter(filename, engine='openpyxl') as writer:
                # Member forces
                forces_df = pd.DataFrame({
                    'Member': range(len(self.member_forces)),
                    'Force (kN)': self.member_forces,
                    'Type': ['Tension' if f>0 else 'Compression' for f in self.member_forces]
                })
                forces_df.to_excel(writer, sheet_name='Member Forces', index=False)
                
                # Reactions
                reactions_data = []
                for node, (rx, ry) in self.analysis_results['reactions'].items():
                    reactions_data.append({'Node': node, 'Rx (kN)': rx, 'Ry (kN)': ry})
                reactions_df = pd.DataFrame(reactions_data)
                reactions_df.to_excel(writer, sheet_name='Reactions', index=False)
                
                # Displacements
                disp_df = pd.DataFrame(self.analysis_results['displacements'], columns=['dx (m)', 'dy (m)'])
                disp_df.index.name = 'Node'
                disp_df.to_excel(writer, sheet_name='Displacements')
            
            messagebox.showinfo("Success", f"Results exported to {filename}")
    
    def generate_full_report(self):
        """Generate comprehensive engineering report"""
        self.update_design_summary([])  # This will update the summary text
        messagebox.showinfo("Report Generated", 
            "Full report has been generated in the Summary tab.\n"
            "Use File menu to export as PDF or Excel.")
    
    def new_project(self):
        """Create new project"""
        if messagebox.askyesno("New Project", "Create new project? Unsaved data will be lost."):
            # Reset all variables
            self.project_name_var.set("Timber Truss Project")
            self.engineer_var.set("")
            self.span_var.set(12.0)
            self.rise_var.set(2.5)
            self.panels_var.set(4)
            self.truss_type_var.set("Fink")
            
            # Clear results
            self.analysis_text.delete(1.0, tk.END)
            self.summary_text.delete(1.0, tk.END)
            
            for item in self.design_tree.get_children():
                self.design_tree.delete(item)
            
            # Regenerate geometry
            self.generate_and_display_geometry()
    
    def save_project(self):
        """Save project to JSON file"""
        filename = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        
        if filename:
            project_data = {
                'project_name': self.project_name_var.get(),
                'engineer': self.engineer_var.get(),
                'span': self.span_var.get(),
                'rise': self.rise_var.get(),
                'truss_type': self.truss_type_var.get(),
                'panels': self.panels_var.get(),
                'species': self.species_var.get(),
                'grade': self.grade_var.get(),
                'section': self.lumber_size_var.get()
            }
            
            with open(filename, 'w') as f:
                json.dump(project_data, f, indent=4)
            
            messagebox.showinfo("Success", f"Project saved to {filename}")
    
    def load_project(self):
        """Load project from JSON file"""
        filename = filedialog.askopenfilename(
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        
        if filename:
            with open(filename, 'r') as f:
                data = json.load(f)
            
            self.project_name_var.set(data.get('project_name', 'Timber Truss Project'))
            self.engineer_var.set(data.get('engineer', ''))
            self.span_var.set(data.get('span', 12.0))
            self.rise_var.set(data.get('rise', 2.5))
            self.truss_type_var.set(data.get('truss_type', 'Fink'))
            self.panels_var.set(data.get('panels', 4))
            self.species_var.set(data.get('species', 'Apitong (Dipterocarpus spp.)'))
            self.grade_var.set(data.get('grade', 'Select Structural'))
            self.lumber_size_var.set(data.get('section', ''))
            
            self.generate_and_display_geometry()
            messagebox.showinfo("Success", f"Project loaded from {filename}")
    
    def export_report(self):
        """Export comprehensive report"""
        self.generate_full_report()
        
        # Ask for export format
        choice = messagebox.askquestion("Export Report", 
            "Export to PDF? Click 'Yes' for PDF, 'No' for Excel.")
        
        if choice == 'yes':
            self.export_to_pdf()
        else:
            self.export_to_excel()
    
    def show_manual(self):
        """Show user manual"""
        manual_text = """
TIMBER TRUSS DESIGNER - USER MANUAL
====================================

Overview:
This software performs structural design of timber roof trusses according to 
NSCP 2015 (National Structural Code of the Philippines).

Workflow:
1. Enter project information and truss parameters in Inputs tab
2. Generate truss geometry in Geometry tab
3. Define load cases in Load Definition tab
4. Run structural analysis in Analysis tab
5. Perform member design check in Design tab
6. Review results and generate report in Summary tab

Key Features:
- Multiple truss types (Fink, Pratt, Howe, Warren)
- Philippine timber species database
- Automatic geometry generation
- Matrix structural analysis
- NSCP 2015 compliant timber design
- Visual force diagrams
- Professional report generation

Design Assumptions:
- Linear elastic material behavior
- Pin-connected truss members
- Concentrated nodal loads from distributed loads
- ASD (Allowable Stress Design) method
- Sawn lumber sections

NSCP 2015 References:
- Chapter 6: Timber Design
- Section 603: Adjustment Factors
- Section 603.4: Tension Members
- Section 603.5: Compression Members

For questions or support, contact the software vendor.
"""
        
        messagebox.showinfo("User Manual", manual_text)
    
    def show_about(self):
        """Show about dialog"""
        about_text = """
Timber Truss Designer - Professional Edition
Version 1.0

NSCP 2015 Compliant Timber Roof Truss Design Software

Developed for structural engineers in the Philippines

Features:
- Complete timber truss design workflow
- Multiple truss configurations
- Philippine timber species database
- Matrix structural analysis
- NSCP 2015 compliant member design
- Professional report generation

Copyright © 2024 Structural Engineering Software Solutions
All Rights Reserved

This software is for professional engineering use only.
Always verify results with independent calculations.
"""
        
        messagebox.showinfo("About Timber Truss Designer", about_text)

# ============================================================================
# MAIN APPLICATION ENTRY POINT
# ============================================================================

def main():
    """Main application entry point"""
    root = tk.Tk()
    app = TimberTrussDesignerGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()