import base64
import io
import sqlite3
import dash
from dash import dcc, html, Input, Output, State, dash_table
import dash_bootstrap_components as dbc
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors

app = dash.Dash(
    __name__,
    external_stylesheets=[
        dbc.themes.SLATE,
        "https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800;900&display=swap"
    ],
    suppress_callback_exceptions=True
)
app.title = "Omaha Baseball Analytics"
server = app.server

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


def render_3d_stadium(df):
    fig = go.Figure()
    grass_material = dict(ambient=0.8, diffuse=0.9, roughness=0.9, specular=0.1)
    dirt_material = dict(ambient=0.9, diffuse=0.8, roughness=1.0, specular=0.0)

    theta_arc = np.linspace(-np.pi / 4, np.pi / 4, 200)
    for r in range(150, 401, 25):
        x_out, y_out = r * np.sin(theta_arc), r * np.cos(theta_arc)
        x_in, y_in = (r - 25) * np.sin(theta_arc[::-1]), (r - 25) * np.cos(theta_arc[::-1])
        stripe_color = '#14532D' if (r // 25) % 2 == 0 else '#166534'
        fig.add_trace(go.Mesh3d(
            x=np.concatenate([x_out, x_in, [x_out[0]]]),
            y=np.concatenate([y_out, y_in, [y_out[0]]]),
            z=np.zeros(401),
            color=stripe_color,
            lighting=grass_material,
            hoverinfo='skip',
            showlegend=False
        ))

    theta_full = np.linspace(0, 2 * np.pi, 100)
    fig.add_trace(go.Mesh3d(
        x=np.concatenate([[0], 145 * np.sin(np.linspace(-np.pi / 4, np.pi / 4, 100)), [0]]),
        y=np.concatenate([[0], 145 * np.cos(np.linspace(-np.pi / 4, np.pi / 4, 100)), [0]]),
        z=np.full(102, 0.1),
        color='#8D6E63',
        lighting=dirt_material,
        hoverinfo='skip',
        showlegend=False
    ))
    fig.add_trace(go.Mesh3d(
        x=13 * np.sin(theta_full),
        y=13 * np.cos(theta_full),
        z=np.full(100, 0.15),
        color='#8D6E63',
        lighting=dirt_material,
        hoverinfo='skip',
        showlegend=False
    ))
    fig.add_trace(go.Mesh3d(
        x=9 * np.sin(theta_full),
        y=60.5 + 9 * np.cos(theta_full),
        z=np.full(100, 0.15),
        color='#8D6E63',
        lighting=dirt_material,
        hoverinfo='skip',
        showlegend=False
    ))

    fig.add_trace(go.Mesh3d(
        x=np.concatenate([400 * np.sin(theta_arc), 385 * np.sin(theta_arc[::-1]), [400 * np.sin(theta_arc[0])]]),
        y=np.concatenate([400 * np.cos(theta_arc), 385 * np.cos(theta_arc[::-1]), [400 * np.cos(theta_arc[0])]]),
        z=np.full(401, 0.2),
        color='#5D4037',
        lighting=dirt_material,
        hoverinfo='skip',
        showlegend=False
    ))

    wall_x = np.concatenate([400 * np.sin(theta_arc), 400 * np.sin(theta_arc[::-1])])
    wall_y = np.concatenate([400 * np.cos(theta_arc), 400 * np.cos(theta_arc[::-1])])
    wall_z = np.concatenate([np.zeros(200), np.full(200, 15)])
    fig.add_trace(go.Mesh3d(
        x=wall_x, y=wall_y, z=wall_z,
        color='rgba(15, 23, 42, 0.4)',
        alphahull=0,
        hoverinfo='skip',
        showlegend=False
    ))
    fig.add_trace(go.Scatter3d(
        x=400 * np.sin(theta_arc),
        y=400 * np.cos(theta_arc),
        z=np.full(200, 15),
        mode='lines',
        line=dict(color='#D71920', width=8),
        hoverinfo='skip',
        showlegend=False
    ))

    fig.add_trace(go.Scatter3d(
        x=[63.6, 0, -63.6],
        y=[63.6, 127.2, 63.6],
        z=[0.3, 0.3, 0.3],
        mode='markers',
        marker=dict(color='white', size=6, symbol='square'),
        hoverinfo='skip',
        showlegend=False
    ))
    fig.add_trace(go.Scatter3d(
        x=[0, 283], y=[0, 283], z=[0.2, 0.2],
        mode='lines',
        line=dict(color='white', width=4),
        hoverinfo='skip',
        showlegend=False
    ))
    fig.add_trace(go.Scatter3d(
        x=[0, -283], y=[0, 283], z=[0.2, 0.2],
        mode='lines',
        line=dict(color='white', width=4),
        hoverinfo='skip',
        showlegend=False
    ))

    if not df.empty:
        for _, row in df.iterrows():
            dist = row.get('Distance')
            direction = row.get('Direction')
            angle = row.get('Angle')
            ev = row.get('ExitSpeed')
            if pd.isna(dist) or pd.isna(direction) or pd.isna(angle) or pd.isna(ev):
                continue
            t = np.linspace(0, 1, 60)
            x_end = dist * np.sin(np.radians(direction))
            y_end = dist * np.cos(np.radians(direction))
            x_traj, y_traj = t * x_end, t * y_end
            h_max = dist * np.tan(np.radians(max(0.1, angle))) * 0.25
            z_traj = 4 * h_max * t * (1 - t)

            color = '#D71920' if (ev >= 95 and 8 <= angle <= 32) else '#3B82F6' if ev >= 90 else '#94A3B8'
            fig.add_trace(go.Scatter3d(
                x=x_traj, y=y_traj, z=z_traj,
                mode='lines',
                line=dict(color=color, width=6),
                hovertemplate=f"<b>EV:</b> {ev:.1f} mph<br><b>LA:</b> {angle:.1f}°<br><b>Dist:</b> {dist:.0f} ft<extra></extra>",
                showlegend=False
            ))
            fig.add_trace(go.Scatter3d(
                x=x_traj, y=y_traj, z=np.full(60, 0.3),
                mode='lines',
                line=dict(color='rgba(0,0,0,0.2)', width=2, dash='dot'),
                hoverinfo='skip',
                showlegend=False
            ))
            fig.add_trace(go.Scatter3d(
                x=[x_end], y=[y_end], z=[0.3],
                mode='markers',
                marker=dict(color=color, size=7, line=dict(color='white', width=2)),
                hoverinfo='skip',
                showlegend=False
            ))

    fig.update_layout(
        scene=dict(
            xaxis=dict(range=[-300, 300], visible=False),
            yaxis=dict(range=[-20, 450], visible=False),
            zaxis=dict(range=[0, 150], visible=False),
            aspectmode='manual',
            aspectratio=dict(x=1.3, y=1.3, z=0.3),
            camera=dict(
                up=dict(x=0, y=0, z=1),
                center=dict(x=0, y=0, z=0),
                eye=dict(x=0, y=-1.5, z=0.6)
            )
        ),
        margin=dict(l=0, r=0, b=0, t=0),
        paper_bgcolor='rgba(0,0,0,0)'
    )
    return fig


def render_3d_strikezone(df):
    fig = go.Figure()

    # Home plate: flat 17" edge at Y=1.417 (facing pitcher), apex at Y=0 (facing catcher)
    plate_x = [-0.708, 0.708, 0.708, 0.0, -0.708, -0.708]
    plate_y = [1.417, 1.417, 0.708, 0.0, 0.708, 1.417]
    fig.add_trace(go.Scatter3d(
        x=plate_x, y=plate_y, z=np.zeros(6),
        mode='lines',
        surfaceaxis=2,
        surfacecolor='white',
        line=dict(color='#0F172A', width=6),
        hoverinfo='skip',
        showlegend=False
    ))

    sz_z_lines = [1.5, 2.166, 2.833, 3.5]
    sz_x_lines = [-0.833, -0.277, 0.277, 0.833]
    for y_plane in [0, 1.417]:
        fig.add_trace(go.Scatter3d(
            x=[-0.833, 0.833, 0.833, -0.833, -0.833],
            y=np.full(5, y_plane),
            z=[1.5, 1.5, 3.5, 3.5, 1.5],
            mode='lines',
            line=dict(
                color='rgba(215, 25, 32, 0.9)' if y_plane == 1.417 else 'rgba(148, 163, 184, 0.5)',
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
                x=[x, x], y=[0, 1.417], z=[z, z],
                mode='lines',
                line=dict(color='rgba(148, 163, 184, 0.5)', width=4),
                hoverinfo='skip',
                showlegend=False
            ))

    if not df.empty:
        df_cp = df.copy()
        side_col = pd.to_numeric(df_cp.get('ContactPositionX'), errors='coerce')
        plate_side = pd.to_numeric(df_cp.get('PlateLocSide'), errors='coerce')
        df_cp['Side'] = side_col.combine_first(plate_side)

        depth_col = pd.to_numeric(df_cp.get('ContactPositionY'), errors='coerce')
        df_cp['Depth'] = depth_col.fillna(1.417)

        height_col = pd.to_numeric(df_cp.get('ContactPositionZ'), errors='coerce')
        plate_height = pd.to_numeric(df_cp.get('PlateLocHeight'), errors='coerce')
        df_cp['Height'] = height_col.combine_first(plate_height)

        valid_cp = df_cp.dropna(subset=['Side', 'Height', 'Depth', 'ExitSpeed'])

        if not valid_cp.empty:
            fig.add_trace(go.Scatter3d(
                x=valid_cp['Side'],
                y=valid_cp['Depth'],
                z=valid_cp['Height'],
                mode='markers',
                marker=dict(
                    size=10,
                    color=valid_cp['ExitSpeed'],
                    colorscale='Turbo',
                    cmin=70,
                    cmax=105,
                    showscale=True,
                    colorbar=dict(title="EV (mph)", len=0.8, thickness=20),
                    line=dict(color='black', width=1.5)
                ),
                hovertemplate=(
                    "<b>EV: %{marker.color:.1f} mph</b><br>"
                    "Side: %{x:.2f} ft<br>"
                    "Depth: %{y:.2f} ft<br>"
                    "Height: %{z:.2f} ft<extra></extra>"
                ),
                name='Contact Point'
            ))
            fig.add_trace(go.Scatter3d(
                x=valid_cp['Side'],
                y=valid_cp['Depth'],
                z=np.zeros(len(valid_cp)),
                mode='markers',
                marker=dict(color='rgba(0,0,0,0.15)', size=5),
                hoverinfo='skip',
                showlegend=False
            ))

    fig.update_layout(
        scene=dict(
            xaxis=dict(title='Side to Side (ft)', range=[-3, 3], gridcolor='#E2E8F0', backgroundcolor='#F8FAFC', showbackground=True),
            yaxis=dict(title='Depth: Catcher ⬅️ Pitcher (ft)', range=[-1, 4], gridcolor='#E2E8F0', backgroundcolor='#F8FAFC', showbackground=True),
            zaxis=dict(title='Height (ft)', range=[0, 5], gridcolor='#E2E8F0', backgroundcolor='#F8FAFC', showbackground=True),
            aspectmode='manual',
            aspectratio=dict(x=1.2, y=1.2, z=0.9),
            camera=dict(eye=dict(x=1.4, y=-1.6, z=0.8))
        ),
        margin=dict(l=0, r=0, b=0, t=0),
        paper_bgcolor='rgba(0,0,0,0)'
    )
    return fig


def create_wedge_polygon(r_inner, r_outer, theta1, theta2, num_points=40):
    t1_rad, t2_rad = np.radians(theta1), np.radians(theta2)
    theta_vals = np.linspace(t1_rad, t2_rad, num_points)
    x_outer = r_outer * np.sin(theta_vals)
    y_outer = r_outer * np.cos(theta_vals)
    x_inner = r_inner * np.sin(theta_vals[::-1])
    y_inner = r_inner * np.cos(theta_vals[::-1])
    return np.concatenate([x_outer, x_inner, [x_outer[0]]]), np.concatenate([y_outer, y_inner, [y_outer[0]]])


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

    vmin, vmax = (75, 100) if metric == 'ExitSpeed' else (0, 35)
    cmap = plt.get_cmap('coolwarm' if metric == 'ExitSpeed' else 'viridis')
    norm = mcolors.Normalize(vmin=vmin, vmax=vmax)

    for z, params in zones.items():
        val = avgs.get(z, np.nan)
        color, text_val = 'rgba(241, 245, 249, 0.4)', "<b>N/A</b>"
        if not pd.isna(val):
            rgba = cmap(norm(val))
            color = f'rgba({int(rgba[0]*255)}, {int(rgba[1]*255)}, {int(rgba[2]*255)}, 0.9)'
            unit = ' mph' if metric == 'ExitSpeed' else '°'
            text_val = f"<b>{val:.1f}{unit}</b>"

        x_pts, y_pts = create_wedge_polygon(params['r'][0], params['r'][1], params['t'][0], params['t'][1])
        fig.add_trace(go.Scatter(x=x_pts, y=y_pts, fill='toself', fillcolor=color, mode='lines', line=dict(color='white', width=1.5), hoverinfo='skip', showlegend=False))
        mid_r = params['r'][0] + (params['r'][1] - params['r'][0]) / 2
        mid_t = np.radians(params['t'][0] + (params['t'][1] - params['t'][0]) / 2)
        fig.add_trace(go.Scatter(
            x=[mid_r * np.sin(mid_t)],
            y=[mid_r * np.cos(mid_t)],
            mode='text',
            text=[text_val],
            textfont=dict(color='black', size=14, family='Inter'),
            hoverinfo='skip',
            showlegend=False
        ))

    title_label = "EXIT SPEED" if metric == 'ExitSpeed' else "LAUNCH ANGLE"
    fig.update_layout(
        xaxis=dict(visible=False, range=[-300, 300]),
        yaxis=dict(visible=False, range=[-20, 420], scaleanchor='x', scaleratio=1),
        margin=dict(l=0, r=0, b=0, t=40),
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

    vmin, vmax = (75, 100) if metric == 'ExitSpeed' else (0, 35)
    cmap = plt.get_cmap('coolwarm' if metric == 'ExitSpeed' else 'viridis')
    norm = mcolors.Normalize(vmin=vmin, vmax=vmax)

    for z, r in sz_rects.items():
        val = avgs.get(z, np.nan)
        color, text_val = 'rgba(241, 245, 249, 0.4)', "<b>N/A</b>"
        if not pd.isna(val):
            rgba = cmap(norm(val))
            color = f'rgba({int(rgba[0]*255)}, {int(rgba[1]*255)}, {int(rgba[2]*255)}, 0.95)'
            text_val = f"<b>{val:.1f}</b>"

        x_pts = [r['x'], r['x'] + r['w'], r['x'] + r['w'], r['x'], r['x']]
        y_pts = [r['y'], r['y'], r['y'] + r['h'], r['y'] + r['h'], r['y']]
        line_color = 'white' if z.startswith('Z') else 'rgba(0,0,0,0)'
        fig.add_trace(go.Scatter(x=x_pts, y=y_pts, fill='toself', fillcolor=color, mode='lines', line=dict(color=line_color, width=2), hoverinfo='skip', showlegend=False))
        fig.add_trace(go.Scatter(
            x=[r['x'] + r['w'] / 2],
            y=[r['y'] + r['h'] / 2],
            mode='text',
            text=[text_val],
            textfont=dict(color='black', size=15 if z.startswith('Z') else 11, family='Inter'),
            hoverinfo='skip',
            showlegend=False
        ))

    title_label = "EXIT SPEED" if metric == 'ExitSpeed' else "LAUNCH ANGLE"
    fig.update_layout(
        xaxis=dict(visible=False, range=[-2, 2]),
        yaxis=dict(visible=False, range=[0, 4.5], scaleanchor='x', scaleratio=1),
        margin=dict(l=0, r=0, b=0, t=40),
        title=dict(text=f"<b>AVERAGE {title_label} BY PITCH LOCATION</b>", font=dict(size=14, family='Inter', color='#0F172A'), x=0.5, y=0.95),
        paper_bgcolor='white',
        plot_bgcolor='white'
    )
    return fig


SIDEBAR_STYLE = {
    "position": "fixed", "top": 0, "left": 0, "bottom": 0,
    "width": "22rem", "padding": "2rem 1.5rem",
    "backgroundColor": "#0F172A", "color": "white", "overflowY": "auto"
}

CONTENT_STYLE = {
    "marginLeft": "23rem", "padding": "2rem",
    "backgroundColor": "#F8FAFC", "minHeight": "100vh"
}

sidebar = html.Div([
    html.Img(
        src="https://upload.wikimedia.org/wikipedia/en/thumb/0/01/Omaha_Mavericks_logo.svg/1200px-Omaha_Mavericks_logo.svg.png",
        style={"width": "140px", "display": "block", "margin": "0 auto 30px auto"}
    ),

    html.H5("Data Ingestion", style={"color": "#94A3B8", "fontSize": "13px", "textTransform": "uppercase", "letterSpacing": "1px", "marginBottom": "15px", "fontWeight": "bold"}),
    dcc.Upload(
        id='upload-data',
        children=html.Div(['Drop CSV(s) or ', html.A('Select Files', style={"fontWeight": "bold"})]),
        multiple=True,
        style={
            'width': '100%', 'height': '60px', 'lineHeight': '60px',
            'borderWidth': '2px', 'borderStyle': 'dashed', 'borderColor': '#D71920',
            'borderRadius': '8px', 'textAlign': 'center', 'cursor': 'pointer',
            'backgroundColor': '#1E293B', 'color': 'white'
        }
    ),
    html.Div(id='upload-output', style={"color": "#4ADE80", "fontSize": "13px", "marginTop": "10px", "fontWeight": "bold", "marginBottom": "15px"}),

    html.Hr(style={"borderColor": "#334155"}),

    html.H5("Performance Filters", style={"color": "#94A3B8", "fontSize": "13px", "textTransform": "uppercase", "letterSpacing": "1px", "marginBottom": "15px", "fontWeight": "bold"}),
    html.Label("Hitter Profile", style={"fontSize": "12px", "fontWeight": "600"}),
    dcc.Dropdown(id='hitter-dropdown', style={"color": "black", "marginBottom": "15px"}),

    html.Label("Date Range", style={"fontSize": "12px", "fontWeight": "600"}),
    dcc.Dropdown(id='date-dropdown', style={"color": "black", "marginBottom": "25px"}),

    html.Hr(style={"borderColor": "#334155"}),
    dbc.Button("Reset Database", id="reset-db-btn", color="danger", outline=True, size="sm", style={"width": "100%"})
], style=SIDEBAR_STYLE)

main_content = html.Div([
    html.Div(
        id="dashboard-header",
        style={
            "background": "linear-gradient(135deg, #0B0F19 0%, #1A2235 100%)",
            "borderRadius": "16px", "padding": "30px 40px", "color": "white",
            "marginBottom": "30px", "borderLeft": "8px solid #D71920",
            "boxShadow": "0 20px 25px -5px rgba(0, 0, 0, 0.1)"
        }
    ),
    html.Div(
        id="kpi-grid",
        style={
            "display": "grid",
            "gridTemplateColumns": "repeat(auto-fit, minmax(140px, 1fr))",
            "gap": "15px", "marginBottom": "30px"
        }
    ),

    dbc.Tabs([
        dbc.Tab(
            html.Div([dbc.Row([dbc.Col(dcc.Graph(id='3d-stadium-graph', style={"height": "750px"}), width=12)])], style={"padding": "20px"}),
            label="🌐 Interactive Spray Chart",
            tab_style={"backgroundColor": "#E2E8F0", "border": "none"},
            active_tab_style={"backgroundColor": "white", "color": "#0F172A", "fontWeight": "bold", "borderTop": "3px solid #D71920"}
        ),
        dbc.Tab(
            html.Div([dbc.Row([dbc.Col(dcc.Graph(id='3d-strikezone-graph', style={"height": "750px"}), width=12)])], style={"padding": "20px"}),
            label="⚾ 3D Strike Zone",
            tab_style={"backgroundColor": "#E2E8F0", "border": "none"},
            active_tab_style={"backgroundColor": "white", "color": "#0F172A", "fontWeight": "bold", "borderTop": "3px solid #D71920"}
        ),
        dbc.Tab(
            html.Div([
                dbc.Row([
                    dbc.Col(dcc.Graph(id='2d-ev-field', style={"height": "600px"}), width=6),
                    dbc.Col(dcc.Graph(id='2d-la-field', style={"height": "600px"}), width=6)
                ]),
                dbc.Row([
                    dbc.Col(dcc.Graph(id='2d-ev-sz', style={"height": "600px"}), width=6),
                    dbc.Col(dcc.Graph(id='2d-la-sz', style={"height": "600px"}), width=6)
                ], style={"marginTop": "20px"})
            ], style={"padding": "20px"}),
            label="🔥 Heatmap Matrices",
            tab_style={"backgroundColor": "#E2E8F0", "border": "none"},
            active_tab_style={"backgroundColor": "white", "color": "#0F172A", "fontWeight": "bold", "borderTop": "3px solid #D71920"}
        ),
        dbc.Tab(
            html.Div([
                html.H4("Raw Event Log", style={"marginBottom": "20px", "fontWeight": "bold", "color": "#0F172A"}),
                html.Div(id="data-table-container")
            ], style={"padding": "30px", "backgroundColor": "white", "borderRadius": "8px", "border": "1px solid #E2E8F0"}),
            label="📊 Performance Tables",
            tab_style={"backgroundColor": "#E2E8F0", "border": "none"},
            active_tab_style={"backgroundColor": "white", "color": "#0F172A", "fontWeight": "bold", "borderTop": "3px solid #D71920"}
        ),
    ])
], style=CONTENT_STYLE)

app.layout = html.Div([sidebar, main_content])


@app.callback(
    Output('upload-output', 'children'),
    [Input('upload-data', 'contents'), Input('reset-db-btn', 'n_clicks')],
    prevent_initial_call=True
)
def process_upload_or_reset(contents, reset_clicks):
    ctx = dash.callback_context
    if not ctx.triggered:
        return ""
    trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]

    if trigger_id == 'reset-db-btn':
        conn = sqlite3.connect(DB_NAME)
        conn.execute("DELETE FROM trackman_data")
        conn.commit()
        conn.close()
        return "🗑️ Database cleared."

    if not contents:
        return ""

    if not isinstance(contents, list):
        contents = [contents]

    total_added = 0
    try:
        conn = sqlite3.connect(DB_NAME)
        for content in contents:
            _, content_string = content.split(',')
            decoded = base64.b64decode(content_string)

            try:
                df_upload = pd.read_csv(io.StringIO(decoded.decode('utf-8-sig')), low_memory=False)
            except Exception:
                df_upload = pd.read_csv(io.StringIO(decoded.decode('latin1')), low_memory=False)

            df_upload.columns = df_upload.columns.str.strip()
            keep = [c for c in EXPECTED_COLS if c in df_upload.columns]
            df_cleaned = df_upload[keep].copy()

            # Clean string columns
            for str_col in ['Batter', 'Pitcher', 'BatterSide', 'PitcherThrows', 'TaggedPitchType', 'PitchCall', 'PlayResult', 'TaggedHitType', 'KorBB', 'Time']:
                if str_col in df_cleaned.columns:
                    df_cleaned[str_col] = df_cleaned[str_col].astype(str).str.strip().replace({'nan': None, 'None': None, '': None})

            # Standardize Date to YYYY-MM-DD for accurate chronological sorting
            if 'Date' in df_cleaned.columns:
                parsed_dates = pd.to_datetime(df_cleaned['Date'], errors='coerce')
                df_cleaned['Date'] = parsed_dates.dt.strftime('%Y-%m-%d').fillna(df_cleaned['Date'].astype(str).str.strip())

            # Coerce numeric columns
            for col in NUMERIC_COLS:
                if col in df_cleaned.columns:
                    df_cleaned[col] = pd.to_numeric(df_cleaned[col], errors='coerce')

            df_cleaned = df_cleaned.dropna(subset=['Batter'])

            # Deduplicate before appending
            existing = pd.read_sql("SELECT Date, Time, PitchNo, Batter FROM trackman_data", conn)
            if not existing.empty and all(k in df_cleaned.columns for k in ['Date', 'Time', 'PitchNo', 'Batter']):
                merged = df_cleaned.merge(existing, on=['Date', 'Time', 'PitchNo', 'Batter'], how='left', indicator=True)
                df_cleaned = df_cleaned[merged['_merge'].values == 'left_only']

            if not df_cleaned.empty:
                df_cleaned.to_sql('trackman_data', conn, if_exists='append', index=False)
                total_added += len(df_cleaned)

        conn.close()
        return f"✅ Ingested {total_added} new rows."
    except Exception as e:
        return f"❌ Error: {str(e)}"


@app.callback(
    [Output('hitter-dropdown', 'options'), Output('hitter-dropdown', 'value')],
    Input('upload-output', 'children')
)
def update_hitters(_):
    conn = sqlite3.connect(DB_NAME)
    df = pd.read_sql("SELECT DISTINCT Batter FROM trackman_data WHERE Batter IS NOT NULL", conn)
    conn.close()
    if df.empty:
        return [], None
    batters = sorted(df['Batter'].dropna().unique().tolist())
    return [{'label': b, 'value': b} for b in batters], batters[0]


@app.callback(
    [Output('date-dropdown', 'options'), Output('date-dropdown', 'value')],
    Input('hitter-dropdown', 'value')
)
def update_dates(hitter):
    if not hitter:
        return [], None
    conn = sqlite3.connect(DB_NAME)
    df = pd.read_sql("SELECT DISTINCT Date FROM trackman_data WHERE Batter = ?", conn, params=(hitter,))
    conn.close()
    dates = ["All-Time"] + sorted(df['Date'].dropna().unique().tolist(), reverse=True)
    return [{'label': d, 'value': d} for d in dates], "All-Time"


@app.callback(
    [
        Output('dashboard-header', 'children'),
        Output('kpi-grid', 'children'),
        Output('3d-stadium-graph', 'figure'),
        Output('3d-strikezone-graph', 'figure'),
        Output('2d-ev-field', 'figure'),
        Output('2d-la-field', 'figure'),
        Output('2d-ev-sz', 'figure'),
        Output('2d-la-sz', 'figure'),
        Output('data-table-container', 'children')
    ],
    [Input('hitter-dropdown', 'value'), Input('date-dropdown', 'value')]
)
def update_dashboard(hitter, date):
    empty_fig = go.Figure()
    if not hitter:
        empty_header = html.Div([
            html.H1("OMAHA HITTING PORTAL", style={"fontSize": "36px", "fontWeight": "900", "margin": 0}),
            html.Div("UPLOAD A TRACKMAN CSV IN THE SIDEBAR TO BEGIN", style={"fontSize": "14px", "fontWeight": "600", "color": "#94A3B8", "marginTop": "6px"})
        ])
        return empty_header, [], empty_fig, empty_fig, empty_fig, empty_fig, empty_fig, empty_fig, ""

    conn = sqlite3.connect(DB_NAME)
    if date and date != "All-Time":
        df = pd.read_sql("SELECT * FROM trackman_data WHERE Batter = ? AND Date = ?", conn, params=(hitter, date))
    else:
        df = pd.read_sql("SELECT * FROM trackman_data WHERE Batter = ?", conn, params=(hitter,))
    conn.close()

    for col in NUMERIC_COLS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')

    batted_balls = df.dropna(subset=['ExitSpeed']).copy()
    batted_balls = batted_balls[batted_balls['ExitSpeed'] > 0]

    if batted_balls.empty:
        empty_header = html.Div([
            html.H1(hitter.upper(), style={"fontSize": "42px", "fontWeight": "900", "margin": 0}),
            html.Div("NO BATTED BALL EVENTS FOUND FOR SELECTION", style={"fontSize": "15px", "fontWeight": "600", "color": "#D71920", "marginTop": "6px"})
        ])
        return empty_header, [], empty_fig, empty_fig, empty_fig, empty_fig, empty_fig, empty_fig, ""

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

    header = [
        html.Div([
            html.H1(hitter.upper(), style={"fontSize": "42px", "fontWeight": "900", "margin": 0, "letterSpacing": "-1px"}),
            html.Div(
                f"BATS: {side}  |  RANGE: {date}  |  BATTED BALL EVENTS: {bip}",
                style={"fontSize": "15px", "fontWeight": "600", "color": "#94A3B8", "letterSpacing": "1px", "marginTop": "6px"}
            )
        ])
    ]

    kpis = [
        ("TOTAL SWINGS", total_swings),
        ("HARD HIT %", f"{hh_pct:.1f}%"),
        ("SWEET SPOT %", f"{swsp_pct:.1f}%"),
        ("AVG EV", f"{avg_ev:.1f}"),
        ("90th% EV", f"{ev90:.1f}"),
        ("MAX EV", f"{max_ev:.1f}"),
        ("AVG LA", f"{avg_la:.1f}°"),
        ("LA DEV", f"{std_la:.1f}°"),
        ("AVG DIST", f"{avg_dist:.0f} ft" if not pd.isna(avg_dist) else "N/A")
    ]

    kpi_cards = []
    for label, val in kpis:
        val_color = "#D71920" if label in ["90th% EV", "SWEET SPOT %", "HARD HIT %"] else "#0F172A"
        kpi_cards.append(html.Div([
            html.Div(label, style={"fontSize": "11px", "fontWeight": "800", "color": "#64748B", "marginBottom": "5px"}),
            html.Div(val, style={"fontSize": "26px", "fontWeight": "900", "color": val_color})
        ], style={
            "background": "#FFFFFF", "border": "1px solid #E2E8F0",
            "borderRadius": "12px", "padding": "20px 10px",
            "textAlign": "center", "boxShadow": "0 4px 6px -1px rgba(0,0,0,0.03)"
        }))

    fig_field = render_3d_stadium(batted_balls)
    fig_zone = render_3d_strikezone(batted_balls)
    fig_ev_field = render_2d_field_heatmap(batted_balls, metric='ExitSpeed')
    fig_la_field = render_2d_field_heatmap(batted_balls, metric='Angle')
    fig_ev_sz = render_2d_sz_heatmap(batted_balls, metric='ExitSpeed')
    fig_la_sz = render_2d_sz_heatmap(batted_balls, metric='Angle')

    display_cols = [
        c for c in ['Date', 'PitchNo', 'Pitcher', 'TaggedPitchType', 'ExitSpeed', 'Angle', 'Direction', 'Distance', 'PlayResult']
        if c in batted_balls.columns
    ]
    table_df = batted_balls[display_cols].sort_values(by='ExitSpeed', ascending=False).copy()
    for num_c in ['ExitSpeed', 'Angle', 'Direction', 'Distance']:
        if num_c in table_df.columns:
            table_df[num_c] = table_df[num_c].round(1)

    raw_table = dash_table.DataTable(
        data=table_df.to_dict('records'),
        columns=[{"name": i, "id": i} for i in display_cols],
        page_size=15,
        sort_action="native",
        style_header={'backgroundColor': '#0F172A', 'color': 'white', 'fontWeight': 'bold'},
        style_cell={'textAlign': 'center', 'padding': '10px', 'fontFamily': 'Inter', 'color': '#0F172A'},
        style_data_conditional=[{'if': {'row_index': 'odd'}, 'backgroundColor': '#F8FAFC'}]
    )

    return header, kpi_cards, fig_field, fig_zone, fig_ev_field, fig_la_field, fig_ev_sz, fig_la_sz, raw_table


if __name__ == '__main__':
    app.run(debug=True)
