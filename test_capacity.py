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
.detail-box { background: #1e293b; padding: 1rem; border-radius: 8px; border-left: 4px solid #00d4ff; margin-bottom: 1rem;}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────
#  IMPORT GROUNDHOG
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
        phi = None
    else:
        gamma = st.number_input("Effective Unit Weight, γ' (kN/m³)", value=9.0)
        phi = st.number_input("Friction Angle, φ (degrees)", value=32.0)
        su = None

    st.markdown("#### 2. ขนาดฐานราก (Geometry)")
    shape = st.selectbox("รูปทรงฐานราก:", ["Rectangle (สี่เหลี่ยม)", "Circle (วงกลม)"])

    if shape == "Rectangle (สี่เหลี่ยม)":
        B = st.number_input("Width, B (m) - ความกว้าง", value=2.0, min_value=0.1)
        L = st.number_input("Length, L (m) - ความยาว", value=3.0, min_value=0.1)
        D_circ = None
    else:
        D_circ = st.number_input("Diameter, D (m) - เส้นผ่านศูนย์กลาง", value=2.0, min_value=0.1)
        B = D_circ
        L = D_circ

    Df = st.number_input("Depth, Df (m) - ความลึกฝัง", value=1.0, min_value=0.0)

    st.markdown("#### 3. น้ำหนักบรรทุก (Applied Loads)")
    V = st.number_input("Vertical Load, V (kN)", value=500.0, min_value=0.01)
    Mx = st.number_input("Moment Mx (kN-m)", value=50.0)
    My = st.number_input("Moment My (kN-m)", value=0.0)

    st.markdown("#### 4. พารามิเตอร์การทรุดตัว (Settlement)")
    Es = st.number_input("Young's Modulus, Es (MPa)", value=20.0, min_value=0.1)
    nu = st.slider("Poisson's Ratio, ν", min_value=0.1, max_value=0.5, value=0.3)
    tolerable_settlement = st.number_input("Tolerable Settlement (mm)", value=25.0, min_value=1.0)

# ─────────────────────────────────────────────────────────────
#  [FIX 1] คำนวณ Eccentricity และ e_total ก่อน if/else block
#           เพื่อป้องกัน NameError เมื่อ shape = Circle
# ─────────────────────────────────────────────────────────────
ex = abs(My / V) if V > 0 else 0.0
ey = abs(Mx / V) if V > 0 else 0.0
e_total = math.sqrt(ex**2 + ey**2)  # ← define ที่นี่เสมอ ไม่ใช่แค่ใน else block

# ─────────────────────────────────────────────────────────────
#  [FIX 2] คำนวณ Effective Geometry ก่อน แล้วตรวจสอบ B_eff > 0
#           เพื่อป้องกัน negative area / division by zero
# ─────────────────────────────────────────────────────────────
if shape == "Rectangle (สี่เหลี่ยม)":
    B_eff = B - 2 * ex
    L_eff = L - 2 * ey
    Iw = 1.12       # [FIX 5] เปลี่ยนชื่อจาก shape_factor เป็น Iw (Influence Factor)
else:
    B_eff = D_circ - 2 * e_total
    L_eff = B_eff
    Iw = 1.00

# [FIX 2] ตรวจสอบ Effective Area ก่อนดำเนินการต่อ
if B_eff <= 0 or L_eff <= 0:
    st.error(
        f"🚨 **Invalid Effective Geometry:** ระยะเยื้องศูนย์ (eccentricity) มากเกินไป — "
        f"B' = {B_eff:.3f} m, L' = {L_eff:.3f} m\n\n"
        "กรุณาลด Moment หรือเพิ่มขนาดฐานราก แล้วลองใหม่อีกครั้ง"
    )
    st.stop()

if shape == "Rectangle (สี่เหลี่ยม)":
    A_eff = B_eff * L_eff
else:
    A_eff = math.pi * (B_eff / 2) ** 2

# ─────────────────────────────────────────────────────────────
#  CORE CALCULATION (CAPACITY)
# ─────────────────────────────────────────────────────────────
if "Undrained" in soil_type:
    calc = ShallowFoundationCapacityUndrained(title="Foundation Analysis")
    if shape == "Rectangle (สี่เหลี่ยม)":
        calc.set_geometry(length=L, width=B)
    else:
        calc.set_geometry(option='circle', diameter=D_circ)
    calc.depth = Df
    calc.set_soilparameters_undrained(unit_weight=gamma, su_base=su)
    calc.set_eccentricity(eccentricity_width=ex, eccentricity_length=ey)
else:
    calc = ShallowFoundationCapacityDrained(title="Foundation Analysis")
    if shape == "Rectangle (สี่เหลี่ยม)":
        calc.set_geometry(length=L, width=B)
    else:
        calc.set_geometry(option='circle', diameter=D_circ)
    calc.depth = Df
    calc.set_soilparameters_drained(effective_unit_weight=gamma, friction_angle=phi, effective_stress_base=0)
    calc.set_eccentricity(eccentricity_width=ex, eccentricity_length=ey)

calc.calculate_bearing_capacity()
calc.calculate_sliding_capacity(vertical_load=V)

# [FIX 3] ระบุ exception type ให้ชัดเจน แทน bare except
try:
    calc.calculate_envelope()
    env_V = calc.envelope_V_unfactored
    env_H = calc.envelope_H_unfactored
except (AttributeError, ValueError, TypeError) as e:
    env_V, env_H = [], []
    # เก็บ error message ไว้โชว์ใน UI ภายหลัง
    _envelope_err = str(e)
else:
    _envelope_err = None

q_ult = calc.net_bearing_pressure  # kPa
Q_ult = calc.ultimate_capacity     # kN
H_ult = calc.sliding_full          # kN
fs = Q_ult / V if V > 0 else 999

# ─────────────────────────────────────────────────────────────
#  SETTLEMENT CALCULATION
#  [FIX 4] ใช้ Influence Factor Iw และชื่อตัวแปรที่ถูกต้อง
#  สูตร: Se = q × B' × (1 - ν²) / Es × Iw
# ─────────────────────────────────────────────────────────────
q_act = V / A_eff  # หน่วยแรงแบกทานที่เกิดขึ้น (kPa)

Se_m = (q_act * B_eff * (1 - nu**2) / (Es * 1000)) * Iw
Se_mm = Se_m * 1000

# ─────────────────────────────────────────────────────────────
#  UI: MAIN DASHBOARD
# ─────────────────────────────────────────────────────────────
st.markdown("""
<div class="hero-wrap">
    <h1 style="margin:0; font-size:1.6rem; color:#fff;">🏗️ Shallow Foundation Analysis (v3.1)</h1>
    <p style="margin:5px 0 0; color:#94a3b8;">ระบบวิเคราะห์ฐานรากแผ่แบบมืออาชีพ พร้อมรายการคำนวณโดยละเอียด</p>
</div>
""", unsafe_allow_html=True)

# ── 1. Metrics Summary ──
c1, c2, c3, c4 = st.columns(4)
with c1:
    color_fs = "#00e676" if fs >= 2.5 else "#ff3d57"
    st.markdown(f'<div class="stat-card" style="border-top-color:{color_fs};"><div class="stat-label">Factor of Safety (FS)</div><div class="stat-value" style="color:{color_fs};">{fs:.2f}</div></div>', unsafe_allow_html=True)
with c2:
    st.markdown(f'<div class="stat-card"><div class="stat-label">Ultimate Load (Q_ult)</div><div class="stat-value">{Q_ult:,.1f} kN</div></div>', unsafe_allow_html=True)
with c3:
    st.markdown(f'<div class="stat-card"><div class="stat-label">Effective Area (A_eff)</div><div class="stat-value">{A_eff:.2f} m²</div></div>', unsafe_allow_html=True)
with c4:
    color_se = "#00e676" if Se_mm <= tolerable_settlement else "#ff3d57"
    st.markdown(f'<div class="stat-card" style="border-top-color:{color_se};"><div class="stat-label">Elastic Settlement</div><div class="stat-value" style="color:{color_se};">{Se_mm:.1f} mm</div></div>', unsafe_allow_html=True)

# ── 2. Warning Checks ──
check_col1, check_col2 = st.columns(2)
with check_col1:
    if shape == "Rectangle (สี่เหลี่ยม)":
        limit_x, limit_y = B / 6.0, L / 6.0
        if ex > limit_x or ey > limit_y:
            st.error(f"🚨 **Overturning:** ระยะ e เกินขอบเขต B/6 (เกิดแรงดึงใต้ฐาน)")
        else:
            st.success(f"✅ **Overturning Safe:** ไม่เกิดแรงดึงใต้ฐานราก")
    else:
        limit_d = D_circ / 8.0
        if e_total > limit_d:
            st.error(f"🚨 **Overturning:** ระยะเยื้องศูนย์รวมเกิน D/8 (เกิดแรงดึงใต้ฐาน)")
        else:
            st.success(f"✅ **Overturning Safe:** ไม่เกิดแรงดึงใต้ฐานราก")

with check_col2:
    if Se_mm > tolerable_settlement:
        st.error(f"📉 **Settlement Limit:** การทรุดตัว {Se_mm:.1f} mm เกินพิกัดที่ยอมให้")
    else:
        st.success(f"✅ **Settlement Safe:** การทรุดตัวอยู่ในเกณฑ์ปลอดภัย")

# ── 3. DETAILED CALCULATION EXPANDER ──
with st.expander("📑 เปิดดูรายการคำนวณโดยละเอียด (Detailed Calculation Sheet)", expanded=False):
    st.markdown("ข้อมูลด้านล่างคือค่าตัวแปรวิศวกรรมที่โปรแกรมดึงมาจากสมการ สามารถนำไปตรวจสอบทวนกับการคำนวณด้วยมือได้ครับ")

    col_det1, col_det2 = st.columns(2)
    with col_det1:
        # [FIX 2] แสดง label ให้ถูกต้องตาม shape
        if shape == "Rectangle (สี่เหลี่ยม)":
            geom_line1 = f"• ความกว้างจริง (B) = {B:.3f} m"
            geom_line2 = f"• ความยาวจริง (L) = {L:.3f} m"
        else:
            geom_line1 = f"• เส้นผ่านศูนย์กลาง (D) = {D_circ:.3f} m"
            geom_line2 = f"• (B = L = D สำหรับฐานรากวงกลม)"

        st.markdown(
            f"<div class='detail-box'><b>📐 ข้อมูลรูปร่างประสิทธิผล (Effective Geometry)</b><br>"
            f"{geom_line1}<br>"
            f"{geom_line2}<br>"
            f"• ระยะเยื้องศูนย์แกน X (e_x) = {ex:.3f} m<br>"
            f"• ระยะเยื้องศูนย์แกน Y (e_y) = {ey:.3f} m<br>"
            f"• ระยะเยื้องศูนย์รวม (e_total) = {e_total:.3f} m<br>"
            f"• <b>ความกว้างประสิทธิผล (B') = {B_eff:.3f} m</b><br>"
            f"• <b>ความยาวประสิทธิผล (L') = {L_eff:.3f} m</b><br>"
            f"• Influence Factor (Iw) = {Iw:.2f}<br>"
            f"• หน่วยแรงแบกทานที่เกิดขึ้น (q_act) = {q_act:.2f} kPa</div>",
            unsafe_allow_html=True
        )

    with col_det2:
        st.markdown("<b>📊 ตัวคูณกำลังรับน้ำหนัก (Bearing Capacity Factors)</b>")
        # [FIX 3] ระบุ exception type ที่ชัดเจน + แสดง warning message
        try:
            dict_factors = calc.capacity
            clean_factors = {k: v for k, v in dict_factors.items() if isinstance(v, (int, float))}
            df_factors = pd.DataFrame(list(clean_factors.items()), columns=['Parameter (ตัวแปร)', 'Value (ค่าที่คำนวณได้)'])
            st.dataframe(df_factors, use_container_width=True, hide_index=True)
        except (AttributeError, KeyError, TypeError) as e:
            st.warning(f"ไม่สามารถดึงข้อมูลตัวคูณได้: {e}")

st.divider()

# ── 4. Visualizations ──
col_chart1, col_chart2 = st.columns(2)

with col_chart1:
    st.markdown("### 📐 Effective Area (พื้นที่รับน้ำหนักยังผล)")
    fig_plan = go.Figure()

    if shape == "Rectangle (สี่เหลี่ยม)":
        fig_plan.add_shape(type="rect", x0=-B/2, y0=-L/2, x1=B/2, y1=L/2,
                           line=dict(color="#334155", width=2), fillcolor="rgba(255,255,255,0.05)")
        fig_plan.add_shape(type="rect",
                           x0=ex - B_eff/2, y0=ey - L_eff/2,
                           x1=ex + B_eff/2, y1=ey + L_eff/2,
                           line=dict(color="#00d4ff", width=2, dash="dash"), fillcolor="rgba(0,212,255,0.2)")
    else:
        # วาดวงกลมฐานรากจริง และ effective circle
        theta = np.linspace(0, 2 * math.pi, 120)
        fig_plan.add_trace(go.Scatter(
            x=(D_circ / 2) * np.cos(theta), y=(D_circ / 2) * np.sin(theta),
            mode="lines", line=dict(color="#334155", width=2), fill="toself",
            fillcolor="rgba(255,255,255,0.05)", name="Actual"
        ))
        fig_plan.add_trace(go.Scatter(
            x=ex + (B_eff / 2) * np.cos(theta), y=ey + (B_eff / 2) * np.sin(theta),
            mode="lines", line=dict(color="#00d4ff", width=2, dash="dash"),
            fill="toself", fillcolor="rgba(0,212,255,0.2)", name="Effective"
        ))

    fig_plan.add_trace(go.Scatter(x=[0], y=[0], mode="markers+text", name="CG เดิม",
                                  marker=dict(color="white", symbol="cross", size=10),
                                  text=["(0,0)"], textposition="bottom left"))
    fig_plan.add_trace(go.Scatter(x=[ex], y=[ey], mode="markers+text", name="Load Point",
                                  marker=dict(color="#ff3d57", size=12),
                                  text=["Load"], textposition="top right"))

    fig_plan.update_layout(
        template="plotly_dark", plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(title="X (m)", range=[-B, B], scaleanchor="y", scaleratio=1),
        yaxis=dict(title="Y (m)", range=[-L, L]),
        height=400, margin=dict(l=20, r=20, t=30, b=20)
    )
    st.plotly_chart(fig_plan, use_container_width=True)

with col_chart2:
    st.markdown("### 📈 Failure Envelope (V-H Interaction)")
    if len(env_V) > 0:
        fig_env = go.Figure()
        fig_env.add_trace(go.Scatter(x=env_V, y=env_H, mode="lines", name="Failure Envelope",
                                     line=dict(color="#00d4ff", width=3),
                                     fill="tozeroy", fillcolor="rgba(0,212,255,0.1)"))
        fig_env.add_trace(go.Scatter(x=[V], y=[0], mode="markers", name="Applied Load",
                                     marker=dict(color="#ff3d57", size=14, symbol="star")))
        fig_env.update_layout(
            template="plotly_dark", plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
            xaxis=dict(title="Vertical Load, V (kN)"), yaxis=dict(title="Horizontal Load, H (kN)"),
            height=400, margin=dict(l=20, r=20, t=30, b=20)
        )
        st.plotly_chart(fig_env, use_container_width=True)
    else:
        # [FIX 3] แสดง error message ที่ได้จาก exception แทน generic info
        msg = f"ไม่สามารถวาด Envelope ได้: {_envelope_err}" if _envelope_err else "ไม่สามารถวาด Envelope ได้ กรุณาตรวจสอบค่า Input"
        st.warning(msg)
