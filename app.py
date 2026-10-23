import io
import hashlib
import sqlite3
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors

# -----------------------------------------------------------------------------
# PAGE CONFIG & CUSTOM CSS
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Omaha Baseball Analytics",
    page_icon="⚾",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800;900&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}

.stApp {
    background-color: #F8FAFC;
}

/* Dark Slate Sidebar Background */
[data-testid="stSidebar"] {
    background-color: #0F172A !important;
}

/* Sidebar Labels & Section Headers (Light on Dark Background) */
[data-testid="stSidebar"] label p,
[data-testid="stSidebar"] .sidebar-section-title {
    color: #F8FAFC !important;
    font-weight: 700 !important;
}

/* Selectbox Controls (Hitter Profile & Date Range) - Dark Font on Light Box */
[data-testid="stSidebar"] div[data-baseweb="select"] > div {
    background-color: #FFFFFF !important;
    border: 1px solid #CBD5E1 !important;
    border-radius: 8px !important;
}
[data-testid="stSidebar"] div[data-baseweb="select"] *,
[data-testid="stSidebar"] div[data-baseweb="select"] span,
[data-testid="stSidebar"] div[data-baseweb="select"] input {
    color: #0F172A !important;
    font-weight: 700 !important;
}
[data-testid="stSidebar"] div[data-baseweb="select"] svg {
    fill: #0F172A !important;
}

/* Open Dropdown Menu Options - Dark Font on White Background */
div[data-baseweb="popover"] *,
ul[data-testid="stSelectboxVirtualDropdown"] *,
li[role="option"] * {
    color: #0F172A !important;
    font-weight: 600 !important;
}
ul[data-testid="stSelectboxVirtualDropdown"] {
    background-color: #FFFFFF !important;
}

/* Reset Database Button - Dark Font on Light Box */
[data-testid="stSidebar"] .stButton > button {
    background-color: #FFFFFF !important;
    color: #0F172A !important;
    border: 2px solid #D71920 !important;
    border-radius: 8px !important;
    font-weight: 800 !important;
    padding: 0.5rem 1rem !important;
    width: 100% !important;
}
[data-testid="stSidebar"] .stButton > button p,
[data-testid="stSidebar"] .stButton > button span {
    color: #0F172A !important;
    font-weight: 800 !important;
}
[data-testid="stSidebar"] .stButton > button:hover {
    background-color: #FEE2E2 !important;
    border-color: #B91C1C !important;
}

/* File Uploader Box */
[data-testid="stSidebar"] [data-testid="stFileUploader"] section {
    background-color: #1E293B !important;
    border: 2px dashed #D71920 !important;
    border-radius: 8px !important;
}
[data-testid="stSidebar"] [data-testid="stFileUploader"] section small,
[data-testid="stSidebar"] [data-testid="stFileUploader"] section span {
    color: #E2E8F0 !important;
}
[data-testid="stSidebar"] [data-testid="stFileUploader"] button {
    background-color: #FFFFFF !important;
    color: #0F172A !important;
    border: 1px solid #CBD5E1 !important;
    font-weight: 800 !important;
}
[data-testid="stSidebar"] [data-testid="stFileUploader"] button * {
    color: #0F172A !important;
}
/* Uploaded File Name Chip in Sidebar */
[data-testid="stSidebar"] [data-testid="stFileUploaderFile"] * {
    color: #E2E8F0 !important;
}

/* Header Banner */
.omaha-header {
    background: linear-gradient(135deg, #0B0F19 0%, #1A2235 100%);
    border-radius: 16px;
    padding: 26px 36px;
    color: white;
    margin-bottom: 22px;
    border-left: 8px solid #D71920;
    box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1);
}
.omaha-header h1 {
    font-size: 38px;
    font-weight: 900;
    margin: 0;
    letter-spacing: -1px;
    color: #FFFFFF;
}
.omaha-header .sub {
    font-size: 14px;
    font-weight: 600;
    color: #94A3B8;
    letter-spacing: 1px;
    margin-top: 6px;
}

/* KPI Grid */
.kpi-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(130px, 1fr));
    gap: 12px;
    margin-bottom: 24px;
}
.kpi-card {
    background: #FFFFFF;
    border: 1px solid #E2E8F0;
    border-radius: 12px;
    padding: 16px 10px;
    text-align: center;
    box-shadow: 0 4px 6px -1px rgba(0,0,0,0.03);
}
.kpi-label {
    font-size: 11px;
    font-weight: 800;
    color: #64748B;
    margin-bottom: 4px;
}
.kpi-val {
    font-size: 24px;
    font-weight: 900;
}

/* Tabs Styling */
button[data-baseweb="tab"] {
    background-color: #E2E8F0 !important;
    border-radius: 6px 6px 0 0 !important;
    padding: 10px 20px !important;
    margin-right: 6px !important;
    font-weight: 700 !important;
    color: #0F172A !important;
}
button[data-baseweb="tab"][aria-selected="true"] {
    background-color: #FFFFFF !important;
    color: #0F172A !important;
    border-top: 3px solid #D71920 !important;
}
</style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# DATABASE & CONSTANTS
# -----------------------------------------------------------------------------
DB_NAME = "trackman_master.db"

EXPECTED_COLS = [
    'PitchNo', 'Date', 'Time', 'Pitcher', 'Batter', 'BatterSide', 'PitcherThrows',
    'TaggedPitchType', 'ExitSpeed', 'Angle', 'Direction', 'Distance', 'HitSpinRate',
    'HangTime', 'PlateLocHeight', 'PlateLocSide', 'ContactPositionX',
    'ContactPositionY', 'ContactPositionZ', 'PitchCall', 'PlayResult', 'TaggedHitType',
    'KorBB', 'Balls', 'Strikes', 'RelSpeed', 'InducedVertBreak', 'HorzBreak', 'VertApprAngle'
]

NUMERIC_COLS = [
    'PitchNo', 'ExitSpeed', 'Angle', 'Direction', 'Distance', 'HitSpinRate',
    'HangTime', 'PlateLocHeight', 'PlateLocSide', 'ContactPositionX',
    'ContactPositionY', 'ContactPositionZ', 'Balls', 'Strikes', 'RelSpeed',
    'InducedVertBreak', 'HorzBreak', 'VertApprAngle'
]

SWING_CALLS = [
    'InPlay', 'Foul', 'FoulBall', 'FoulBallNotFieldable',
    'FoulBallFieldable', 'StrikeSwinging', 'FoulBunt'
]

HIT_TYPE_COLORS = {
    'Line Drive': '#D71920',   # Crimson Red
    'Fly Ball': '#2563EB',     # Royal Blue
    'Ground Ball': '#D97706',  # Amber Gold
    'Pop Up': '#9333EA'        # Purple
}


def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS trackman_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            PitchNo INTEGER, Date TEXT, Time TEXT, Pitcher TEXT, Batter TEXT,
            BatterSide TEXT, PitcherThrows TEXT, TaggedPitchType TEXT,
            ExitSpeed REAL, Angle REAL, Direction REAL, Distance REAL,
            HitSpinRate REAL, HangTime REAL, PlateLocHeight REAL, PlateLocSide REAL,
            ContactPositionX REAL, ContactPositionY REAL, ContactPositionZ REAL,
            PitchCall TEXT, PlayResult TEXT, TaggedHitType TEXT, KorBB TEXT,
            Balls INTEGER, Strikes INTEGER, RelSpeed REAL,
            InducedVertBreak REAL, HorzBreak REAL, VertApprAngle REAL
        )
    ''')
    conn.commit()
    conn.close()


init_db()

if "ingested_files" not in st.session_state:
    st.session_state.ingested_files = set()


# -----------------------------------------------------------------------------
# HELPER FUNCTIONS
# -----------------------------------------------------------------------------
def get_batter_side(df_batter):
    if 'BatterSide' not in df_batter.columns:
        return "UNK"
    valid_sides = df_batter['BatterSide'].dropna().astype(str).str.strip().str.lower()
    if valid_sides.empty:
        return "UNK"
    side_str = valid_sides.iloc[0]
    if side_str in ['left', 'l', 'lhh']:
        return 'LHH'
    if side_str in ['right', 'r', 'rhh']:
        return 'RHH'
    if side_str in ['switch', 's', 'shh', 'both']:
        return 'SHH'
    return "UNK"


def classify_hit_type(row):
    tagged = str(row.get('TaggedHitType', '')).strip().lower()
    if tagged in ['linedrive', 'line_drive', 'line drive', 'ld']:
        return 'Line Drive'
    if tagged in ['flyball', 'fly_ball', 'fly ball', 'fb']:
        return 'Fly Ball'
    if tagged in ['groundball', 'ground_ball', 'ground ball', 'gb']:
        return 'Ground Ball'
    if tagged in ['popup', 'pop_up', 'pop up', 'pu', 'pop']:
        return 'Pop Up'

    angle = row.get('Angle')
    if pd.isna(angle):
        return 'Line Drive'
    if angle < 10:
        return 'Ground Ball'
    elif angle < 25:
        return 'Line Drive'
    elif angle < 50:
        return 'Fly Ball'
    else:
        return 'Pop Up'


def assign_sz_zone(x, z):
    if pd.isna(x) or pd.isna(z):
        return None
    if -0.833 <= x <= 0.833 and 1.5 <= z <= 3.5:
        if z >= 2.833:
            return 'Z1' if x <= -0.277 else 'Z2' if x <= 0.277 else 'Z3'
        elif z >= 2.166:
            return 'Z4' if x <= -0.277 else 'Z5' if x <= 0.277 else 'Z6'
        else:
            return 'Z7' if x <= -0.277 else 'Z8' if x <= 0.277 else 'Z9'
    elif -1.166 <= x <= 1.166 and 3.5 < z <= 3.833:
        return 'S1'
    elif -1.166 <= x <= 1.166 and 1.166 <= z < 1.5:
        return 'S3'
    elif -1.166 <= x < -0.833 and 1.5 <= z <= 3.5:
        return 'S2'
    elif 0.833 < x <= 1.166 and 1.5 <= z <= 3.5:
        return 'S4'
    return 'Out'


def assign_field_zone(dist, direction):
    if pd.isna(dist) or pd.isna(direction):
        return None
    if dist < 180:
        if direction < -22.5:
            return 'IF_LL'
        elif direction < 0:
            return 'IF_LC'
        elif direction < 22.5:
            return 'IF_RC'
        else:
            return 'IF_RR'
    else:
        if direction < -15:
            return 'OF_L'
        elif direction < 15:
            return 'OF_C'
        else:
            return 'OF_R'


def create_wedge_polygon(r_inner, r_outer, theta1, theta2, num_points=40):
    t1_rad, t2_rad = np.radians(theta1), np.radians(theta2)
    theta_vals = np.linspace(t1_rad, t2_rad, num_points)
    x_outer = r_outer * np.sin(theta_vals)
    y_outer = r_outer * np.cos(theta_vals)
    x_inner = r_inner * np.sin(theta_vals[::-1])
    y_inner = r_inner * np.cos(theta_vals[::-1])
    return np.concatenate([x_outer, x_inner, [x_outer[0]]]), np.concatenate([y_outer, y_inner, [y_outer[0]]])


# -----------------------------------------------------------------------------
# PLOT GENERATORS
# -----------------------------------------------------------------------------
def render_3d_stadium(df):
    fig = go.Figure()

    theta = np.linspace(-np.pi / 4, np.pi / 4, 90)

    # 1. Outfield Grass Mowing Stripes (Using go.Surface so curved arcs render solidly)
    for r_inner in range(150, 376, 25):
        r_outer = min(r_inner + 25, 385)
        r_grid, t_grid = np.meshgrid([r_inner, r_outer], theta)
        x_surf = r_grid * np.sin(t_grid)
        y_surf = r_grid * np.cos(t_grid)
        z_surf = np.zeros_like(x_surf)
        stripe_color = '#15803D' if ((r_inner // 25) % 2 == 0) else '#166534'
        fig.add_trace(go.Surface(
            x=x_surf, y=y_surf, z=z_surf,
            surfacecolor=np.zeros_like(x_surf),
            colorscale=[[0, stripe_color], [1, stripe_color]],
            showscale=False, hoverinfo='skip', showlegend=False,
            lighting=dict(ambient=0.85, diffuse=0.8, roughness=0.9, specular=0.05)
        ))

    # 2. Warning Track (385 ft to 400 ft)
    r_wt, t_wt = np.meshgrid([385, 400], theta)
    fig.add_trace(go.Surface(
        x=r_wt * np.sin(t_wt), y=r_wt * np.cos(t_wt), z=np.full_like(r_wt, 0.05, dtype=float),
        surfacecolor=np.zeros_like(r_wt),
        colorscale=[[0, '#6D4C41'], [1, '#6D4C41']],
        showscale=False, hoverinfo='skip', showlegend=False
    ))

    # 3. Infield Dirt Arc (0 ft to 150 ft)
    r_if, t_if = np.meshgrid([0, 150], theta)
    fig.add_trace(go.Surface(
        x=r_if * np.sin(t_if), y=r_if * np.cos(t_if), z=np.full_like(r_if, 0.08, dtype=float),
        surfacecolor=np.zeros_like(r_if),
        colorscale=[[0, '#A1887F'], [1, '#A1887F']],
        showscale=False, hoverinfo='skip', showlegend=False
    ))

    # 4. Infield Grass Diamond (Inside Basepaths)
    diamond_s = np.linspace(0, 1, 20)
    u_grid, v_grid = np.meshgrid(diamond_s, diamond_s)
    # 4 corners of inner grass diamond: (0, 22), (52, 63.6), (0, 108), (-52, 63.6)
    p00 = np.array([0.0, 22.0])
    p10 = np.array([52.0, 63.6])
    p01 = np.array([-52.0, 63.6])
    p11 = np.array([0.0, 108.0])
    x_diam = (1 - u_grid) * (1 - v_grid) * p00[0] + u_grid * (1 - v_grid) * p10[0] + (1 - u_grid) * v_grid * p01[0] + u_grid * v_grid * p11[0]
    y_diam = (1 - u_grid) * (1 - v_grid) * p00[1] + u_grid * (1 - v_grid) * p10[1] + (1 - u_grid) * v_grid * p01[1] + u_grid * v_grid * p11[1]
    fig.add_trace(go.Surface(
        x=x_diam, y=y_diam, z=np.full_like(x_diam, 0.15),
        surfacecolor=np.zeros_like(x_diam),
        colorscale=[[0, '#15803D'], [1, '#15803D']],
        showscale=False, hoverinfo='skip', showlegend=False
    ))

    # 5. Pitcher's Mound Dirt Circle
    theta_mound = np.linspace(0, 2 * np.pi, 40)
    r_m, t_m = np.meshgrid([0, 9], theta_mound)
    fig.add_trace(go.Surface(
        x=r_m * np.sin(t_m), y=60.5 + r_m * np.cos(t_m), z=np.full_like(r_m, 0.25, dtype=float),
        surfacecolor=np.zeros_like(r_m),
        colorscale=[[0, '#8D6E63'], [1, '#8D6E63']],
        showscale=False, hoverinfo='skip', showlegend=False
    ))

    # 6. Outfield Wall (r=400 ft, height 0 to 12 ft) & Top Trim
    z_wall, t_wall = np.meshgrid([0, 12], theta)
    fig.add_trace(go.Surface(
        x=400 * np.sin(t_wall), y=400 * np.cos(t_wall), z=z_wall,
        surfacecolor=np.zeros_like(z_wall),
        colorscale=[[0, '#0F172A'], [1, '#1E293B']],
        opacity=0.85, showscale=False, hoverinfo='skip', showlegend=False
    ))
    fig.add_trace(go.Scatter3d(
        x=400 * np.sin(theta), y=400 * np.cos(theta), z=np.full_like(theta, 12.2),
        mode='lines', line=dict(color='#D71920', width=6), hoverinfo='skip', showlegend=False
    ))

    # 7. Foul Lines & Bases
    fig.add_trace(go.Scatter3d(
        x=[0, 400 * np.sin(np.pi / 4)], y=[0, 400 * np.cos(np.pi / 4)], z=[0.2, 0.2],
        mode='lines', line=dict(color='white', width=4), hoverinfo='skip', showlegend=False
    ))
    fig.add_trace(go.Scatter3d(
        x=[0, 400 * np.sin(-np.pi / 4)], y=[0, 400 * np.cos(-np.pi / 4)], z=[0.2, 0.2],
        mode='lines', line=dict(color='white', width=4), hoverinfo='skip', showlegend=False
    ))
    fig.add_trace(go.Scatter3d(
        x=[63.6, 0, -63.6, 0], y=[63.6, 127.2, 63.6, 0], z=[0.35, 0.35, 0.35, 0.35],
        mode='markers', marker=dict(color='white', size=5, symbol='diamond'), hoverinfo='skip', showlegend=False
    ))

    # 8. Batted Ball Trajectories & Landing Markers Grouped by Hit Type
    shown_in_legend = set()
    if not df.empty:
        df_plot = df.copy()
        df_plot['HitCategory'] = df_plot.apply(classify_hit_type, axis=1)

        # Ensure consistent legend order
        for hit_cat in ['Line Drive', 'Fly Ball', 'Ground Ball', 'Pop Up']:
            sub = df_plot[df_plot['HitCategory'] == hit_cat]
            color = HIT_TYPE_COLORS[hit_cat]

            if sub.empty:
                # Dummy trace so legend always shows all 4 hit categories
                fig.add_trace(go.Scatter3d(
                    x=[None], y=[None], z=[None],
                    mode='lines+markers',
                    line=dict(color=color, width=5),
                    marker=dict(color=color, size=6),
                    name=hit_cat,
                    legendgroup=hit_cat,
                    showlegend=True
                ))
                continue

            for _, row in sub.iterrows():
                dist = row.get('Distance')
                direction = row.get('Direction')
                angle = row.get('Angle')
                ev = row.get('ExitSpeed')
                play_res = row.get('PlayResult', 'Undefined')
                if pd.isna(dist) or pd.isna(direction) or pd.isna(angle) or pd.isna(ev):
                    continue

                t = np.linspace(0, 1, 50)
                x_end = dist * np.sin(np.radians(direction))
                y_end = dist * np.cos(np.radians(direction))
                x_traj, y_traj = t * x_end, t * y_end
                h_max = dist * np.tan(np.radians(max(1.0, angle))) * 0.25
                z_traj = 4 * h_max * t * (1 - t) + 0.3

                show_leg = hit_cat not in shown_in_legend
                shown_in_legend.add(hit_cat)

                hover_txt = (
                    f"<b>{hit_cat}</b> ({play_res})<br>"
                    f"<b>EV:</b> {ev:.1f} mph<br>"
                    f"<b>LA:</b> {angle:.1f}°<br>"
                    f"<b>Dist:</b> {dist:.0f} ft<extra></extra>"
                )

                # Flight Path
                fig.add_trace(go.Scatter3d(
                    x=x_traj, y=y_traj, z=z_traj,
                    mode='lines',
                    line=dict(color=color, width=5),
                    name=hit_cat,
                    legendgroup=hit_cat,
                    showlegend=show_leg,
                    hovertemplate=hover_txt
                ))
                # Landing Spot
                fig.add_trace(go.Scatter3d(
                    x=[x_end], y=[y_end], z=[0.4],
                    mode='markers',
                    marker=dict(color=color, size=6, line=dict(color='white', width=1.5)),
                    name=hit_cat,
                    legendgroup=hit_cat,
                    showlegend=False,
                    hovertemplate=hover_txt
                ))

    fig.update_layout(
        height=480,
        legend=dict(
            title=dict(text="<b>Batted Ball Type</b>", font=dict(size=12, color="#0F172A")),
            orientation="h",
            yanchor="bottom",
            y=0.92,
            xanchor="center",
            x=0.5,
            bgcolor="rgba(255, 255, 255, 0.92)",
            bordercolor="#CBD5E1",
             borderwidth=1,
            font=dict(size=12, color="#0F172A", family="Inter")
        ),
        scene=dict(
            xaxis=dict(range=[-300, 300], visible=False),
            yaxis=dict(range=[-20, 430], visible=False),
            zaxis=dict(range=[0, 140], visible=False),
            aspectmode='manual',
            aspectratio=dict(x=1.25, y=1.25, z=0.32),
            camera=dict(
                up=dict(x=0, y=0, z=1),
                center=dict(x=0, y=0, z=-0.05),
                eye=dict(x=0.0, y=-1.35, z=0.55)
            )
        ),
        margin=dict(l=0, r=0, b=0, t=0),
        paper_bgcolor='#FFFFFF'
    )
    return fig


def render_3d_strikezone(df):
    """
    TrackMan V3 Coordinate System for ContactPosition:
      - Origin (0,0,0) = Back apex (tip) of home plate on the ground
      - ContactPositionX = Depth along X-axis toward pitcher (ft). Front edge of home plate = 1.417 ft (17 in).
      - ContactPositionY = Vertical height above ground (ft), corresponding to PlateLocHeight.
      - ContactPositionZ = Horizontal side-to-side across home plate (ft), corresponding to PlateLocSide.
    """
    fig = go.Figure()

    # Home Plate: Apex at Y=0 (facing catcher), flat 17" front edge at Y=1.417 ft (facing pitcher)
    plate_x = [-0.708, 0.708, 0.708, 0.0, -0.708, -0.708]
    plate_y = [1.417, 1.417, 0.708, 0.0, 0.708, 1.417]
    fig.add_trace(go.Scatter3d(
        x=plate_x, y=plate_y, z=np.zeros(6),
        mode='lines',
        surfaceaxis=2,
        surfacecolor='#FFFFFF',
        line=dict(color='#0F172A', width=6),
        hoverinfo='skip',
        showlegend=False
    ))

    # 3D Strike Zone Prism (Front plane at Y=1.417 ft, Back plane at Y=0 ft)
    sz_z_lines = [1.5, 2.166, 2.833, 3.5]
    sz_x_lines = [-0.833, -0.277, 0.277, 0.833]
    for y_plane in [0.0, 1.417]:
        fig.add_trace(go.Scatter3d(
            x=[-0.833, 0.833, 0.833, -0.833, -0.833],
            y=np.full(5, y_plane),
            z=[1.5, 1.5, 3.5, 3.5, 1.5],
            mode='lines',
            line=dict(
                color='rgba(215, 25, 32, 0.9)' if y_plane == 1.417 else 'rgba(148, 163, 184, 0.45)',
                width=5
            ),
            hoverinfo='skip',
            showlegend=False
        ))
        for z in sz_z_lines[1:3]:
            fig.add_trace(go.Scatter3d(
                x=[-0.833, 0.833], y=[y_plane, y_plane], z=[z, z],
                mode='lines',
                line=dict(color='rgba(148, 163, 184, 0.3)', width=2),
                hoverinfo='skip',
                showlegend=False
            ))
        for x in sz_x_lines[1:3]:
            fig.add_trace(go.Scatter3d(
                x=[x, x], y=[y_plane, y_plane], z=[1.5, 3.5],
                mode='lines',
                line=dict(color='rgba(148, 163, 184, 0.3)', width=2),
                hoverinfo='skip',
                showlegend=False
            ))

    for x in [-0.833, 0.833]:
        for z in [1.5, 3.5]:
            fig.add_trace(go.Scatter3d(
                x=[x, x], y=[0.0, 1.417], z=[z, z],
                mode='lines',
                line=dict(color='rgba(148, 163, 184, 0.45)', width=3),
                hoverinfo='skip',
                showlegend=False
            ))

    if not df.empty:
        df_cp = df.copy()

        # True TrackMan V3 Contact Coordinates:
        # ContactPositionZ = Horizontal Side (ft)
        # ContactPositionX = Depth in front of plate apex (ft)
        # ContactPositionY = Vertical Height above ground (ft)
        cp_side = pd.to_numeric(df_cp.get('ContactPositionZ'), errors='coerce')
        plate_side = pd.to_numeric(df_cp.get('PlateLocSide'), errors='coerce')
        df_cp['Side'] = cp_side.combine_first(plate_side)

        cp_depth = pd.to_numeric(df_cp.get('ContactPositionX'), errors='coerce')
        df_cp['Depth'] = cp_depth.fillna(1.417)

        cp_height = pd.to_numeric(df_cp.get('ContactPositionY'), errors='coerce')
        plate_height = pd.to_numeric(df_cp.get('PlateLocHeight'), errors='coerce')
        df_cp['Height'] = cp_height.combine_first(plate_height)

        valid_cp = df_cp.dropna(subset=['Side', 'Height', 'Depth', 'ExitSpeed']).copy()

        if not valid_cp.empty:
            # Drop-lines to ground (Z=0) to clearly visualize contact depth vs home plate
            drop_x, drop_y, drop_z = [], [], []
            for _, r in valid_cp.iterrows():
                drop_x.extend([r['Side'], r['Side'], None])
                drop_y.extend([r['Depth'], r['Depth'], None])
                drop_z.extend([0.0, r['Height'], None])

            fig.add_trace(go.Scatter3d(
                x=drop_x, y=drop_y, z=drop_z,
                mode='lines',
                line=dict(color='rgba(100, 116, 139, 0.35)', width=2, dash='dot'),
                hoverinfo='skip',
                showlegend=False
            ))

            # Ground shadow markers (Z=0)
            fig.add_trace(go.Scatter3d(
                x=valid_cp['Side'],
                y=valid_cp['Depth'],
                z=np.zeros(len(valid_cp)),
                mode='markers',
                marker=dict(color='rgba(15, 23, 42, 0.25)', size=4),
                hoverinfo='skip',
                showlegend=False
            ))

            # 3D Contact Points colored Blue (Low EV) to Red (High EV)
            fig.add_trace(go.Scatter3d(
                x=valid_cp['Side'],
                y=valid_cp['Depth'],
                z=valid_cp['Height'],
                mode='markers',
                marker=dict(
                    size=9,
                    color=valid_cp['ExitSpeed'],
                    colorscale='RdBu_r',
                    cmin=70,
                    cmax=105,
                    showscale=True,
                    colorbar=dict(title="EV (mph)", len=0.75, thickness=18),
                    line=dict(color='#0F172A', width=1.5)
                ),
                hovertemplate=(
                    "<b>EV: %{marker.color:.1f} mph</b><br>"
                    "Horiz (ContactPositionZ): %{x:.2f} ft<br>"
                    "Depth (ContactPositionX): %{y:.2f} ft<br>"
                    "Height (ContactPositionY): %{z:.2f} ft<extra></extra>"
                ),
                name='Contact Point',
                showlegend=False
            ))

    fig.update_layout(
        height=480,
        scene=dict(
            xaxis=dict(title='Side (ContactPositionZ, ft)', range=[-2.5, 2.5], gridcolor='#E2E8F0', backgroundcolor='#F8FAFC', showbackground=True),
            yaxis=dict(title='Depth: Catcher ⬅️ ➡️ Pitcher (ContactPositionX, ft)', range=[-0.5, 4.0], gridcolor='#E2E8F0', backgroundcolor='#F8FAFC', showbackground=True),
            zaxis=dict(title='Height (ContactPositionY, ft)', range=[0, 4.8], gridcolor='#E2E8F0', backgroundcolor='#F8FAFC', showbackground=True),
            aspectmode='manual',
            aspectratio=dict(x=1.1, y=1.3, z=0.95),
            camera=dict(eye=dict(x=1.35, y=-1.55, z=0.75))
        ),
        margin=dict(l=0, r=0, b=0, t=0),
        paper_bgcolor='#FFFFFF'
    )
    return fig


def get_blue_to_red_color(val, vmin, vmax, alpha=0.92):
    """Returns a Blue (Low) -> Red (High) RGBA string."""
    cmap = plt.get_cmap('coolwarm')
    norm = mcolors.Normalize(vmin=vmin, vmax=vmax)
    rgba = cmap(np.clip(norm(val), 0.0, 1.0))
    return f'rgba({int(rgba[0]*255)}, {int(rgba[1]*255)}, {int(rgba[2]*255)}, {alpha})'


def render_2d_field_heatmap(df, metric='ExitSpeed'):
    fig = go.Figure()
    theta_arc = np.linspace(-np.pi / 4, np.pi / 4, 100)
    fig.add_trace(go.Scatter(x=400 * np.sin(theta_arc), y=400 * np.cos(theta_arc), mode='lines', line=dict(color='#64748B', width=2), hoverinfo='skip', showlegend=False))
    fig.add_trace(go.Scatter(x=[0, 400 * np.sin(np.pi / 4)], y=[0, 400 * np.cos(np.pi / 4)], mode='lines', line=dict(color='#64748B', width=2), hoverinfo='skip', showlegend=False))
    fig.add_trace(go.Scatter(x=[0, 400 * np.sin(-np.pi / 4)], y=[0, 400 * np.cos(-np.pi / 4)], mode='lines', line=dict(color='#64748B', width=2), hoverinfo='skip', showlegend=False))
    fig.add_trace(go.Scatter(x=180 * np.sin(theta_arc), y=180 * np.cos(theta_arc), mode='lines', line=dict(color='#94A3B8', width=2, dash='dash'), hoverinfo='skip', showlegend=False))

    zones = {
        'IF_LL': {'r': (0, 180), 't': (-45, -22.5)},
        'IF_LC': {'r': (0, 180), 't': (-22.5, 0)},
        'IF_RC': {'r': (0, 180), 't': (0, 22.5)},
        'IF_RR': {'r': (0, 180), 't': (22.5, 45)},
        'OF_L': {'r': (180, 400), 't': (-45, -15)},
        'OF_C': {'r': (180, 400), 't': (-15, 15)},
        'OF_R': {'r': (180, 400), 't': (15, 45)}
    }

    avgs = pd.Series(dtype=float)
    if not df.empty and 'Distance' in df.columns and 'Direction' in df.columns:
        df_copy = df.copy()
        df_copy['FieldZone'] = [
            assign_field_zone(d, dir_)
            for d, dir_ in zip(df_copy['Distance'], df_copy['Direction'])
        ]
        if df_copy['FieldZone'].notna().any():
            avgs = df_copy.groupby('FieldZone')[metric].mean()

    # Blue (Low) -> Red (High) for both ExitSpeed and Angle
    vmin, vmax = (75, 100) if metric == 'ExitSpeed' else (0, 35)
    unit = ' mph' if metric == 'ExitSpeed' else '°'

    for z, params in zones.items():
        val = avgs.get(z, np.nan)
        color, text_val = 'rgba(241, 245, 249, 0.5)', "<b>N/A</b>"
        if not pd.isna(val):
            color = get_blue_to_red_color(val, vmin, vmax, alpha=0.9)
            text_val = f"<b>{val:.1f}{unit}</b>"

        x_pts, y_pts = create_wedge_polygon(params['r'][0], params['r'][1], params['t'][0], params['t'][1])
        fig.add_trace(go.Scatter(
            x=x_pts, y=y_pts, fill='toself', fillcolor=color,
            mode='lines', line=dict(color='white', width=1.5),
            hoverinfo='skip', showlegend=False
        ))
        mid_r = params['r'][0] + (params['r'][1] - params['r'][0]) / 2
        mid_t = np.radians(params['t'][0] + (params['t'][1] - params['t'][0]) / 2)
        fig.add_trace(go.Scatter(
            x=[mid_r * np.sin(mid_t)],
            y=[mid_r * np.cos(mid_t)],
            mode='text',
            text=[text_val],
            textfont=dict(color='#0F172A', size=14, family='Inter'),
            hoverinfo='skip',
            showlegend=False
        ))

    # Colorbar trace for Blue -> Red reference
    fig.add_trace(go.Scatter(
        x=[None], y=[None], mode='markers',
        marker=dict(
            colorscale='RdBu_r', cmin=vmin, cmax=vmax, showscale=True,
            colorbar=dict(title="mph" if metric == 'ExitSpeed' else "deg", thickness=14, len=0.65)
        ),
        hoverinfo='skip', showlegend=False
    ))

    title_label = "EXIT SPEED" if metric == 'ExitSpeed' else "LAUNCH ANGLE"
    fig.update_layout(
        height=480,
        xaxis=dict(visible=False, range=[-300, 300]),
        yaxis=dict(visible=False, range=[-20, 420], scaleanchor='x', scaleratio=1),
        margin=dict(l=10, r=40, b=10, t=45),
        title=dict(text=f"<b>AVERAGE {title_label} BY FIELD QUADRANT</b>", font=dict(size=14, family='Inter', color='#0F172A'), x=0.5, y=0.95),
        paper_bgcolor='white',
        plot_bgcolor='white'
    )
    return fig


def render_2d_sz_heatmap(df, metric='ExitSpeed'):
    fig = go.Figure()

    # Home plate: flat edge facing up toward zone (y=0.65), apex pointing down toward catcher (y=0.15)
    plate_x = [-0.708, 0.708, 0.708, 0.0, -0.708, -0.708]
    plate_y = [0.65, 0.65, 0.40, 0.15, 0.40, 0.65]
    fig.add_trace(go.Scatter(x=plate_x, y=plate_y, mode='lines', fill='toself', fillcolor='white', line=dict(color='#0F172A', width=2), hoverinfo='skip', showlegend=False))
    fig.add_trace(go.Scatter(x=[-0.833, 0.833, 0.833, -0.833, -0.833], y=[1.5, 1.5, 3.5, 3.5, 1.5], mode='lines', line=dict(color='#0F172A', width=3), hoverinfo='skip', showlegend=False))

    sz_rects = {
        'Z1': {'x': -0.833, 'y': 2.833, 'w': 0.556, 'h': 0.667},
        'Z2': {'x': -0.277, 'y': 2.833, 'w': 0.554, 'h': 0.667},
        'Z3': {'x': 0.277, 'y': 2.833, 'w': 0.556, 'h': 0.667},
        'Z4': {'x': -0.833, 'y': 2.166, 'w': 0.556, 'h': 0.667},
        'Z5': {'x': -0.277, 'y': 2.166, 'w': 0.554, 'h': 0.667},
        'Z6': {'x': 0.277, 'y': 2.166, 'w': 0.556, 'h': 0.667},
        'Z7': {'x': -0.833, 'y': 1.5, 'w': 0.556, 'h': 0.666},
        'Z8': {'x': -0.277, 'y': 1.5, 'w': 0.554, 'h': 0.666},
        'Z9': {'x': 0.277, 'y': 1.5, 'w': 0.556, 'h': 0.666},
        'S1': {'x': -1.166, 'y': 3.5, 'w': 2.332, 'h': 0.333},
        'S3': {'x': -1.166, 'y': 1.167, 'w': 2.332, 'h': 0.333},
        'S2': {'x': -1.166, 'y': 1.5, 'w': 0.333, 'h': 2.0},
        'S4': {'x': 0.833, 'y': 1.5, 'w': 0.333, 'h': 2.0}
    }

    avgs = pd.Series(dtype=float)
    if not df.empty and 'PlateLocSide' in df.columns and 'PlateLocHeight' in df.columns:
        df_copy = df.copy()
        df_copy['SZ'] = [
            assign_sz_zone(x, z)
            for x, z in zip(df_copy['PlateLocSide'], df_copy['PlateLocHeight'])
        ]
        if df_copy['SZ'].notna().any():
            avgs = df_copy.groupby('SZ')[metric].mean()

    # Blue (Low) -> Red (High) for both ExitSpeed and Angle
    vmin, vmax = (75, 100) if metric == 'ExitSpeed' else (0, 35)

    for z, r in sz_rects.items():
        val = avgs.get(z, np.nan)
        color, text_val = 'rgba(241, 245, 249, 0.5)', "<b>N/A</b>"
        if not pd.isna(val):
            color = get_blue_to_red_color(val, vmin, vmax, alpha=0.95)
            text_val = f"<b>{val:.1f}</b>"

        x_pts = [r['x'], r['x'] + r['w'], r['x'] + r['w'], r['x'], r['x']]
        y_pts = [r['y'], r['y'], r['y'] + r['h'], r['y'] + r['h'], r['y']]
        line_color = 'white' if z.startswith('Z') else 'rgba(148, 163, 184, 0.35)'
        fig.add_trace(go.Scatter(
            x=x_pts, y=y_pts, fill='toself', fillcolor=color,
            mode='lines', line=dict(color=line_color, width=2),
            hoverinfo='skip', showlegend=False
        ))
        fig.add_trace(go.Scatter(
            x=[r['x'] + r['w'] / 2],
            y=[r['y'] + r['h'] / 2],
            mode='text',
            text=[text_val],
            textfont=dict(color='#0F172A', size=15 if z.startswith('Z') else 11, family='Inter'),
            hoverinfo='skip',
            showlegend=False
        ))

    # Colorbar trace for Blue -> Red reference
    fig.add_trace(go.Scatter(
        x=[None], y=[None], mode='markers',
        marker=dict(
            colorscale='RdBu_r', cmin=vmin, cmax=vmax, showscale=True,
            colorbar=dict(title="mph" if metric == 'ExitSpeed' else "deg", thickness=14, len=0.65)
        ),
        hoverinfo='skip', showlegend=False
    ))

    title_label = "EXIT SPEED" if metric == 'ExitSpeed' else "LAUNCH ANGLE"
    fig.update_layout(
        height=480,
        xaxis=dict(visible=False, range=[-2, 2]),
        yaxis=dict(visible=False, range=[0, 4.3], scaleanchor='x', scaleratio=1),
        margin=dict(l=10, r=40, b=10, t=45),
        title=dict(text=f"<b>AVERAGE {title_label} BY PITCH LOCATION</b>", font=dict(size=14, family='Inter', color='#0F172A'), x=0.5, y=0.95),
        paper_bgcolor='white',
        plot_bgcolor='white'
    )
    return fig


def ingest_uploaded_files(uploaded_files):
    total_added = 0
    conn = sqlite3.connect(DB_NAME)
    for up_file in uploaded_files:
        raw_bytes = up_file.getvalue()
        file_hash = hashlib.md5(raw_bytes).hexdigest()
        if file_hash in st.session_state.ingested_files:
            continue

        try:
            df_upload = pd.read_csv(io.BytesIO(raw_bytes), encoding='utf-8-sig', low_memory=False)
        except Exception:
            df_upload = pd.read_csv(io.BytesIO(raw_bytes), encoding='latin1', low_memory=False)

        df_upload.columns = df_upload.columns.str.strip()
        keep = [c for c in EXPECTED_COLS if c in df_upload.columns]
        df_cleaned = df_upload[keep].copy()

        for str_col in ['Batter', 'Pitcher', 'BatterSide', 'PitcherThrows', 'TaggedPitchType', 'PitchCall', 'PlayResult', 'TaggedHitType', 'KorBB', 'Time']:
            if str_col in df_cleaned.columns:
                df_cleaned[str_col] = df_cleaned[str_col].astype(str).str.strip().replace({'nan': None, 'None': None, '': None})

        if 'Date' in df_cleaned.columns:
            parsed_dates = pd.to_datetime(df_cleaned['Date'], errors='coerce')
            df_cleaned['Date'] = parsed_dates.dt.strftime('%Y-%m-%d').fillna(df_cleaned['Date'].astype(str).str.strip())

        for col in NUMERIC_COLS:
            if col in df_cleaned.columns:
                df_cleaned[col] = pd.to_numeric(df_cleaned[col], errors='coerce')

        if 'Batter' in df_cleaned.columns:
            df_cleaned = df_cleaned.dropna(subset=['Batter'])

        existing = pd.read_sql("SELECT Date, Time, PitchNo, Batter FROM trackman_data", conn)
        if not existing.empty and all(k in df_cleaned.columns for k in ['Date', 'Time', 'PitchNo', 'Batter']):
            merged = df_cleaned.merge(existing, on=['Date', 'Time', 'PitchNo', 'Batter'], how='left', indicator=True)
            df_cleaned = df_cleaned[merged['_merge'].values == 'left_only']

        if not df_cleaned.empty:
            df_cleaned.to_sql('trackman_data', conn, if_exists='append', index=False)
            total_added += len(df_cleaned)

        st.session_state.ingested_files.add(file_hash)

    conn.close()
    return total_added


# -----------------------------------------------------------------------------
# SIDEBAR
# -----------------------------------------------------------------------------
with st.sidebar:
    st.markdown(
        '<img src="https://upload.wikimedia.org/wikipedia/en/thumb/0/01/Omaha_Mavericks_logo.svg/1200px-Omaha_Mavericks_logo.svg.png" '
        'style="width: 140px; display: block; margin: 0 auto 25px auto;">',
        unsafe_allow_html=True
    )

    st.markdown(
        '<div class="sidebar-section-title" style="color: #94A3B8; font-size: 13px; text-transform: uppercase; '
        'letter-spacing: 1px; margin-bottom: 10px; font-weight: bold;">Data Ingestion</div>',
        unsafe_allow_html=True
    )

    uploaded_files = st.file_uploader(
        "Drop CSV or Select File",
        type=["csv"],
        accept_multiple_files=True,
        label_visibility="collapsed"
    )

    if uploaded_files:
        added_rows = ingest_uploaded_files(uploaded_files)
        if added_rows > 0:
            st.markdown(
                f'<div style="color: #4ADE80; font-size: 13px; font-weight: bold; margin-top: 8px;">'
                f'✅ Ingested {added_rows} new rows.</div>',
                unsafe_allow_html=True
            )
        else:
            st.markdown(
                '<div style="color: #4ADE80; font-size: 13px; font-weight: bold; margin-top: 8px;">'
                '✅ Data ready in database.</div>',
                unsafe_allow_html=True
            )

    st.markdown('<hr style="border-color: #334155;">', unsafe_allow_html=True)

    st.markdown(
        '<div class="sidebar-section-title" style="color: #94A3B8; font-size: 13px; text-transform: uppercase; '
        'letter-spacing: 1px; margin-bottom: 12px; font-weight: bold;">Performance Filters</div>',
        unsafe_allow_html=True
    )

    conn = sqlite3.connect(DB_NAME)
    batters_df = pd.read_sql("SELECT DISTINCT Batter FROM trackman_data WHERE Batter IS NOT NULL", conn)
    conn.close()

    batter_list = sorted(batters_df['Batter'].dropna().unique().tolist()) if not batters_df.empty else []

    selected_hitter = st.selectbox("Hitter Profile", options=batter_list, index=0 if batter_list else None)

    date_list = ["All-Time"]
    if selected_hitter:
        conn = sqlite3.connect(DB_NAME)
        dates_df = pd.read_sql(
            "SELECT DISTINCT Date FROM trackman_data WHERE Batter = ?",
            conn,
            params=(selected_hitter,)
        )
        conn.close()
        if not dates_df.empty:
            date_list += sorted(dates_df['Date'].dropna().unique().tolist(), reverse=True)

    selected_date = st.selectbox("Date Range", options=date_list, index=0)

    st.markdown('<hr style="border-color: #334155;">', unsafe_allow_html=True)
    if st.button("🗑️ Reset Database", use_container_width=True):
        conn = sqlite3.connect(DB_NAME)
        conn.execute("DELETE FROM trackman_data")
        conn.commit()
        conn.close()
        st.session_state.ingested_files.clear()
        st.rerun()

# -----------------------------------------------------------------------------
# MAIN CONTENT AREA
# -----------------------------------------------------------------------------
if not selected_hitter:
    st.markdown("""
    <div class="omaha-header">
        <h1>OMAHA HITTING PORTAL</h1>
        <div class="sub">UPLOAD A TRACKMAN CSV IN THE SIDEBAR TO BEGIN</div>
    </div>
    """, unsafe_allow_html=True)
else:
    conn = sqlite3.connect(DB_NAME)
    if selected_date and selected_date != "All-Time":
        df = pd.read_sql(
            "SELECT * FROM trackman_data WHERE Batter = ? AND Date = ?",
            conn,
            params=(selected_hitter, selected_date)
        )
    else:
        df = pd.read_sql(
            "SELECT * FROM trackman_data WHERE Batter = ?",
            conn,
            params=(selected_hitter,)
        )
    conn.close()

    for col in NUMERIC_COLS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')

    batted_balls = df.dropna(subset=['ExitSpeed']).copy()
    batted_balls = batted_balls[batted_balls['ExitSpeed'] > 0]

    if batted_balls.empty:
        st.markdown(f"""
        <div class="omaha-header">
            <h1>{selected_hitter.upper()}</h1>
            <div class="sub" style="color: #D71920;">NO BATTED BALL EVENTS FOUND FOR SELECTION</div>
        </div>
        """, unsafe_allow_html=True)
    else:
        side = get_batter_side(df)
        total_swings = len(df[df['PitchCall'].isin(SWING_CALLS)]) if 'PitchCall' in df.columns else len(batted_balls)
        bip = len(batted_balls)

        avg_ev = batted_balls['ExitSpeed'].mean()
        max_ev = batted_balls['ExitSpeed'].max()
        ev90 = np.percentile(batted_balls['ExitSpeed'].dropna(), 90)
        hh_pct = (len(batted_balls[batted_balls['ExitSpeed'] >= 95]) / bip) * 100 if bip > 0 else 0.0

        valid_angles = batted_balls['Angle'].dropna()
        swsp_pct = (len(batted_balls[(batted_balls['Angle'] >= 8) & (batted_balls['Angle'] <= 32)]) / bip) * 100 if bip > 0 else 0.0
        avg_la = valid_angles.mean() if not valid_angles.empty else 0.0
        std_la = valid_angles.std() if len(valid_angles) > 1 else 0.0
        avg_dist = batted_balls['Distance'].dropna().mean()

        # Header
        st.markdown(f"""
        <div class="omaha-header">
            <h1>{selected_hitter.upper()}</h1>
            <div class="sub">BATS: {side} &nbsp;|&nbsp; RANGE: {selected_date} &nbsp;|&nbsp; BATTED BALL EVENTS: {bip}</div>
        </div>
        """, unsafe_allow_html=True)

        # KPI Cards
        kpis = [
            ("TOTAL SWINGS", f"{total_swings}"),
            ("HARD HIT %", f"{hh_pct:.1f}%"),
            ("SWEET SPOT %", f"{swsp_pct:.1f}%"),
            ("AVG EV", f"{avg_ev:.1f}"),
            ("90th% EV", f"{ev90:.1f}"),
            ("MAX EV", f"{max_ev:.1f}"),
            ("AVG LA", f"{avg_la:.1f}°"),
            ("LA DEV", f"{std_la:.1f}°"),
            ("AVG DIST", f"{avg_dist:.0f} ft" if not pd.isna(avg_dist) else "N/A")
        ]

        kpi_html = '<div class="kpi-grid">'
        for label, val in kpis:
            val_color = "#D71920" if label in ["90th% EV", "SWEET SPOT %", "HARD HIT %"] else "#0F172A"
            kpi_html += (
                f'<div class="kpi-card">'
                f'<div class="kpi-label">{label}</div>'
                f'<div class="kpi-val" style="color: {val_color};">{val}</div>'
                f'</div>'
            )
        kpi_html += '</div>'
        st.markdown(kpi_html, unsafe_allow_html=True)

        # Tabs
        tab1, tab2, tab3, tab4 = st.tabs([
            "🌐 Interactive Spray Chart",
            "⚾ 3D Strike Zone",
            "🔥 Heatmap Matrices",
            "📊 Performance Tables"
        ])

        with tab1:
            fig_field = render_3d_stadium(batted_balls)
            st.plotly_chart(fig_field, use_container_width=True, theme=None)

        with tab2:
            fig_zone = render_3d_strikezone(batted_balls)
            st.plotly_chart(fig_zone, use_container_width=True, theme=None)

        with tab3:
            col_a, col_b = st.columns(2)
            with col_a:
                st.plotly_chart(render_2d_field_heatmap(batted_balls, metric='ExitSpeed'), use_container_width=True, theme=None)
            with col_b:
                st.plotly_chart(render_2d_field_heatmap(batted_balls, metric='Angle'), use_container_width=True, theme=None)

            col_c, col_d = st.columns(2)
            with col_c:
                st.plotly_chart(render_2d_sz_heatmap(batted_balls, metric='ExitSpeed'), use_container_width=True, theme=None)
            with col_d:
                st.plotly_chart(render_2d_sz_heatmap(batted_balls, metric='Angle'), use_container_width=True, theme=None)

        with tab4:
            st.markdown("<h4 style='color:#0F172A; font-weight:800; margin-bottom:15px;'>Raw Event Log</h4>", unsafe_allow_html=True)
            display_cols = [
                c for c in [
                    'Date', 'PitchNo', 'Pitcher', 'TaggedPitchType', 'ExitSpeed', 'Angle',
                    'Direction', 'Distance', 'TaggedHitType', 'PlayResult',
                    'ContactPositionX', 'ContactPositionY', 'ContactPositionZ'
                ]
                if c in batted_balls.columns
            ]
            table_df = batted_balls[display_cols].sort_values(by='ExitSpeed', ascending=False).copy()
            for num_c in ['ExitSpeed', 'Angle', 'Direction', 'Distance', 'ContactPositionX', 'ContactPositionY', 'ContactPositionZ']:
                if num_c in table_df.columns:
                    table_df[num_c] = table_df[num_c].round(2)

            st.dataframe(table_df, use_container_width=True, hide_index=True, height=480)
