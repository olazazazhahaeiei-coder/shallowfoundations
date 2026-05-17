import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import math

# ─────────────────────────────────────────────────────────────
#  PAGE CONFIG & CSS
# ─────────────────────────────────────────────────────────────
st.set_page_config(page_title="Shallow Foundation Pro", page_icon="🏗️", layout="wide")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@300;400;500;600;700&family=Share+Tech+Mono&display=swap');
html, body, [class*="css"] { font-family: 'Sarabun', sans-serif !important; }
.main { background-color: #0a0e17; color: #e2e8f0; }
.hero-wrap {
    background: linear-gradient(135deg, #111827 0%, #1a2235 60%, #0d1520 100%);
    border: 1px solid rgba(0,212,255,0.15); border-top: 3px solid #00d4ff;
    border-radius: 14px; padding: 1.5rem 2rem; margin-bottom: 1.5rem;
}
.stat-card {
    background: #111827; border: 1px solid #1e293b; border-radius: 12px;
    padding: 1.1rem 1.3rem; margin-bottom: 1rem; border-top: 3px solid #00d4ff;
}
.stat-value { font-size: 1.8rem; font-family: 'Share Tech Mono', monospace; font-weight: 600; color: #00d4ff; }
.stat-label { font-size: 0.8rem; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.05em; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────
#  IMPORT GROUNDHOG (ถอด Try-Except ออกเพื่อให้โชว์ Error จริง)
# ─────────────────────────────────────────────────────────────
from groundhog.shallowfoundations.capacity import ShallowFoundationCapacityUndrained, ShallowFoundationCapacityDrained

# ─────────────────────────────────────────────────────────────
#  SIDEBAR INPUTS
# ─────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 🏗️ Shallow Foundation Pro")
    st.markdown("<small style='color:#64748b;'>Powered by Groundhog Engine</small>", unsafe_allow_html=True)
    st.divider()

    st.markdown("#### 1. สภาพชั้นดิน (Soil Condition)")
    soil_type = st.radio("ประเภทดิน:", ["Undrained (ดินเหนียว - Clay)", "Drained (ดินทราย - Sand)"])
    
    if "Undrained" in soil_type:
        gamma = st.number_input("Unit Weight, γ (kN/m³)", value=17.0)
        su = st.number_input("Undrained Shear Strength, Su (kPa)", value=50.0)
    else:
        gamma = st.number_input("Effective Unit Weight, γ' (kN/m³)", value=9.0)
        phi = st.number_input("Friction Angle, φ (degrees)", value=32.0)

    st.markdown("#### 2. ขนาดฐานราก (Geometry)")
    shape = st.selectbox("รูปทรงฐานราก:", ["Rectangle (สี่เหลี่ยม)", "Circle (วงกลม)"])
    
    if shape == "Rectangle (สี่เหลี่ยม)":
        B = st.number_input("Width, B (m) - ความกว้าง", value=2.0)
        L = st.number_input("Length, L (m) - ความยาว", value=3.0)
    else:
        D = st.number_input("Diameter, D (m) - เส้นผ่านศูนย์กลาง", value=2.0)
        B = L = D

    Df = st.number_input("Depth, Df (m) - ความลึกฝัง", value=1.0)

    st.markdown("#### 3. น้ำหนักบรรทุก (Applied Loads)")
    V = st.number_input("Vertical Load, V (kN)", value=500.0)
    Mx = st.number_input("Moment Mx (kN-m)", value=50.0, help="ก่อให้เกิดระยะเยื้องศูนย์แกน Y")
    My = st.number_input("Moment My (kN-m)", value=0.0, help="ก่อให้เกิดระยะเยื้องศูนย์แกน X")

    # คำนวณ Eccentricity
    ex = abs(My / V) if V > 0 else 0.0
    ey = abs(Mx / V) if V > 0 else 0.0

# ─────────────────────────────────────────────────────────────
#  CORE CALCULATION (GROUNDHOG)
# ─────────────────────────────────────────────────────────────
# เลือกคลาสคำนวณตามประเภทดิน
if "Undrained" in soil_type:
    calc = ShallowFoundationCapacityUndrained(title="Foundation Analysis")
    if shape == "Rectangle (สี่เหลี่ยม)":
        calc.set_geometry(length=L, width=B)
    else:
        calc.set_geometry(option='circle', diameter=D)
        
    calc.depth = Df
    calc.set_soilparameters_undrained(unit_weight=gamma, su_base=su)
    calc.set_eccentricity(eccentricity_width=ex, eccentricity_length=ey)
    
else:
    calc = ShallowFoundationCapacityDrained(title="Foundation Analysis")
    if shape == "Rectangle (สี่เหลี่ยม)":
        calc.set_geometry(length=L, width=B)
    else:
        calc.set_geometry(option='circle', diameter=D)
        
    calc.depth = Df
    calc.set_soilparameters_drained(effective_unit_weight=gamma, friction_angle=phi, effective_stress_base=0)
    calc.set_eccentricity(eccentricity_width=ex, eccentricity_length=ey)

# รันการคำนวณทั้งหมด
calc.calculate_bearing_capacity()
calc.calculate_sliding_capacity(vertical_load=V)

# คำนวณ Envelope (ต้องมีโหลดแนวตั้ง V ก่อน)
try:
    calc.calculate_envelope()
    env_V = calc.envelope_V_unfactored
    env_H = calc.envelope_H_unfactored
except:
    env_V, env_H = [], []

# ดึงผลลัพธ์
q_ult = calc.net_bearing_pressure # kPa
Q_ult = calc.ultimate_capacity    # kN
H_ult = calc.sliding_full         # kN

q_act = V / ((B - 2*ex) * (L - 2*ey)) if shape == "Rectangle (สี่เหลี่ยม)" else V / (math.pi * (D/2)**2)
fs = Q_ult / V if V > 0 else 999

# ─────────────────────────────────────────────────────────────
#  UI: MAIN DASHBOARD
# ─────────────────────────────────────────────────────────────
st.markdown("""
<div class="hero-wrap">
    <h1 style="margin:0; font-size:1.6rem; color:#fff;">🏗️ Shallow Foundation Analysis</h1>
    <p style="margin:5px 0 0; color:#94a3b8;">โปรแกรมออกแบบฐานรากแผ่ (Bearing Capacity & Sliding) ขับเคลื่อนด้วย Groundhog Engine</p>
</div>
""", unsafe_allow_html=True)

# ── 1. Metrics Summary ──
c1, c2, c3, c4 = st.columns(4)
with c1:
    st.markdown(f'<div class="stat-card"><div class="stat-label">Ultimate Load (Q_ult)</div><div class="stat-value">{Q_ult:,.1f} kN</div></div>', unsafe_allow_html=True)
with c2:
    st.markdown(f'<div class="stat-card"><div class="stat-label">Sliding Capacity (H_ult)</div><div class="stat-value">{H_ult:,.1f} kN</div></div>', unsafe_allow_html=True)
with c3:
    st.markdown(f'<div class="stat-card"><div class="stat-label">Eccentricity (ex, ey)</div><div class="stat-value">{ex:.2f}, {ey:.2f} m</div></div>', unsafe_allow_html=True)
with c4:
    color = "#00e676" if fs >= 2.5 else "#ff3d57"
    st.markdown(f'<div class="stat-card" style="border-top-color:{color};"><div class="stat-label">Factor of Safety (FS)</div><div class="stat-value" style="color:{color};">{fs:.2f}</div></div>', unsafe_allow_html=True)

# ── 2. Visualizations ──
col_chart1, col_chart2 = st.columns(2)

with col_chart1:
    st.markdown("### 📐 Effective Area (พื้นที่รับน้ำหนักยังผล)")
    fig_plan = go.Figure()
    
    if shape == "Rectangle (สี่เหลี่ยม)":
        # ฐานรากเต็ม
        fig_plan.add_shape(type="rect", x0=-B/2, y0=-L/2, x1=B/2, y1=L/2,
                           line=dict(color="#334155", width=2), fillcolor="rgba(255,255,255,0.05)")
        # Effective Area (Meyerhof)
        B_eff = B - 2*ex
        L_eff = L - 2*ey
        # จุดศูนย์กลางพื้นที่ใหม่จะอยู่ที่พิกัดเยื้องศูนย์
        fig_plan.add_shape(type="rect", 
                           x0=ex - B_eff/2, y0=ey - L_eff/2, 
                           x1=ex + B_eff/2, y1=ey + L_eff/2,
                           line=dict(color="#00d4ff", width=2, dash="dash"), fillcolor="rgba(0,212,255,0.2)")
    
    # จุด CG เดิม
    fig_plan.add_trace(go.Scatter(x=[0], y=[0], mode="markers+text", name="CG เดิม",
                                  marker=dict(color="white", symbol="cross", size=10), text=["(0,0)"], textposition="bottom left"))
    # จุด Load กระทำ
    fig_plan.add_trace(go.Scatter(x=[ex], y=[ey], mode="markers+text", name="Load Point",
                                  marker=dict(color="#ff3d57", size=12), text=["Load"], textposition="top right"))
    
    fig_plan.update_layout(template="plotly_dark", plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                           xaxis=dict(title="X (m)", range=[-B, B], scaleanchor="y", scaleratio=1),
                           yaxis=dict(title="Y (m)", range=[-L, L]), height=400, margin=dict(l=20,r=20,t=30,b=20))
    st.plotly_chart(fig_plan, use_container_width=True)

with col_chart2:
    st.markdown("### 📈 Failure Envelope (V-H Interaction)")
    if len(env_V) > 0:
        fig_env = go.Figure()
        # ขอบเขตความปลอดภัย (Envelope)
        fig_env.add_trace(go.Scatter(x=env_V, y=env_H, mode="lines", name="Failure Envelope",
                                     line=dict(color="#00d4ff", width=3), fill="tozeroy", fillcolor="rgba(0,212,255,0.1)"))
        # จุดโหลดปัจจุบัน
        fig_env.add_trace(go.Scatter(x=[V], y=[0], mode="markers", name="Applied Load",
                                     marker=dict(color="#ff3d57", size=14, symbol="star")))
        
        fig_env.update_layout(template="plotly_dark", plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                              xaxis=dict(title="Vertical Load, V (kN)"), yaxis=dict(title="Horizontal Load, H (kN)"),
                              height=400, margin=dict(l=20,r=20,t=30,b=20))
        st.plotly_chart(fig_env, use_container_width=True)
    else:
        st.info("ไม่สามารถวาด Envelope ได้ กรุณาตรวจสอบค่า Input")
