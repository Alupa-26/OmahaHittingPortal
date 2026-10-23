import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Wedge, Polygon, FancyBboxPatch, Rectangle
import matplotlib.colors as mcolors
from io import BytesIO

# --- PAGE SETUP ---
st.set_page_config(page_title="Omaha BP Reports", layout="wide")

# --- CUSTOM CSS FOR PROFESSIONAL AESTHETICS ---
st.markdown("""
    <style>
        .block-container {
            padding-top: 2rem;
            padding-bottom: 2rem;
        }
        .metric-card {
            background-color: #ffffff;
            border: 1px solid #e2e8f0;
            border-radius: 8px;
            padding: 15px;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03);
            text-align: center;
            margin-bottom: 15px;
        }
        .metric-label {
            font-size: 13px;
            font-weight: 600;
            color: #64748b;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 5px;
        }
        .metric-value {
            font-size: 24px;
            font-weight: 700;
            color: #0f172a;
        }
        .header-container {
            background: linear-gradient(90deg, #f8fafc 0%, #edf2f7 100%);
            border-radius: 12px;
            padding: 24px;
            border: 1px solid #e2e8f0;
            margin-bottom: 25px;
        }
    </style>
""", unsafe_allow_html=True)

# --- HELPER FUNCTIONS ---
def get_batter_side(side_str):
    if pd.isna(side_str): return "Unk"
    s = str(side_str).strip().lower()
    if s == 'left': return 'LHH'
    if s == 'right': return 'RHH'
    if s == 'switch': return 'SHH'
    return s

def assign_zone(dist, direction):
    if pd.isna(dist) or pd.isna(direction): return None
    if dist < 180: 
        if direction < -22.5: return 'IF_LL'
        elif direction < 0: return 'IF_LC'
        elif direction < 22.5: return 'IF_RC'
        else: return 'IF_RR'
    else:          
        if direction < -15: return 'OF_L'
        elif direction < 15: return 'OF_C'
        else: return 'OF_R'

def assign_sz_zone(x, z):
    if pd.isna(x) or pd.isna(z): return None
    if -0.833 <= x <= 0.833 and 1.5 <= z <= 3.5:
        if z >= 2.833:
            if x <= -0.277: return 'Z1'
            elif x <= 0.277: return 'Z2'
            else: return 'Z3'
        elif z >= 2.166:
            if x <= -0.277: return 'Z4'
            elif x <= 0.277: return 'Z5'
            else: return 'Z6'
        else:
            if x <= -0.277: return 'Z7'
            elif x <= 0.277: return 'Z8'
            else: return 'Z9'
    elif -1.166 <= x <= 1.166 and 3.5 < z <= 3.833: return 'S1'
    elif -1.166 <= x <= 1.166 and 1.166 <= z < 1.5: return 'S3'
    elif -1.166 <= x < -0.833 and 1.5 <= z <= 3.5: return 'S2'
    elif 0.833 < x <= 1.166 and 1.5 <= z <= 3.5: return 'S4'
    return None

ZONES_CONFIG = {
    'IF_LL': {'r_inner': 0, 'width': 180, 'theta1': 112.5, 'theta2': 135, 'text_r': 160, 'text_theta': 123.75},
    'IF_LC': {'r_inner': 0, 'width': 180, 'theta1': 90, 'theta2': 112.5, 'text_r': 160, 'text_theta': 101.25},
    'IF_RC': {'r_inner': 0, 'width': 180, 'theta1': 67.5, 'theta2': 90, 'text_r': 160, 'text_theta': 78.75},
    'IF_RR': {'r_inner': 0, 'width': 180, 'theta1': 45, 'theta2': 67.5, 'text_r': 160, 'text_theta': 56.25},
    'OF_L':  {'r_inner': 180, 'width': 200, 'theta1': 105, 'theta2': 135, 'text_r': 350, 'text_theta': 120},
    'OF_C':  {'r_inner': 180, 'width': 200, 'theta1': 75, 'theta2': 105, 'text_r': 350, 'text_theta': 90},
    'OF_R':  {'r_inner': 180, 'width': 200, 'theta1': 45, 'theta2': 75, 'text_r': 350, 'text_theta': 60},
}

SZ_ZONES_CONFIG = {
    'Z1': {'x': -0.833, 'y': 2.833, 'w': 0.556, 'h': 0.667},
    'Z2': {'x': -0.277, 'y': 2.833, 'w': 0.554, 'h': 0.667},
    'Z3': {'x': 0.277,  'y': 2.833, 'w': 0.556, 'h': 0.667},
    'Z4': {'x': -0.833, 'y': 2.166, 'w': 0.556, 'h': 0.667},
    'Z5': {'x': -0.277, 'y': 2.166, 'w': 0.554, 'h': 0.667},
    'Z6': {'x': 0.277,  'y': 2.166, 'w': 0.556, 'h': 0.667},
    'Z7': {'x': -0.833, 'y': 1.5,   'w': 0.556, 'h': 0.666},
    'Z8': {'x': -0.277, 'y': 1.5,   'w': 0.554, 'h': 0.666},
    'Z9': {'x': 0.277,  'y': 1.5,   'w': 0.556, 'h': 0.666},
    'S1': {'x': -1.166, 'y': 3.5,   'w': 2.332, 'h': 0.333},
    'S3': {'x': -1.166, 'y': 1.167, 'w': 2.332, 'h': 0.333},
    'S2': {'x': -1.166, 'y': 1.5,   'w': 0.333, 'h': 2.0},
    'S4': {'x': 0.833,  'y': 1.5,   'w': 0.333, 'h': 2.0},
}

def draw_field_skeleton(ax, draw_infield=False):
    angles = np.linspace(-45, 45, 100)
    fence_x = 380 * np.sin(np.radians(angles))
    fence_y = 380 * np.cos(np.radians(angles))
    if draw_infield:
        outfield = Wedge(center=(0, 0), r=380, theta1=45, theta2=135, facecolor='#e6f4ea', edgecolor='black', lw=2, zorder=1)
        ax.add_patch(outfield)
        infield_dirt = Wedge(center=(0, 0), r=154, theta1=45, theta2=135, facecolor='#f3e9d2', edgecolor='black', lw=1.5, zorder=2)
        ax.add_patch(infield_dirt)
        for angle in [-22.5, 0, 22.5]:
            ax.plot([0, 380 * np.sin(np.radians(angle))], [0, 380 * np.cos(np.radians(angle))], color='black', lw=1, zorder=3)
        bases_x = [90*np.sin(np.radians(45)), 0, 90*np.sin(np.radians(-45))]
        bases_y = [90*np.cos(np.radians(45)), 90*np.sqrt(2), 90*np.cos(np.radians(-45))]
        for bx, by in zip(bases_x, bases_y):
            base = Polygon([[bx, by+4], [bx+4, by], [bx, by-4], [bx-4, by]], facecolor='white', edgecolor='black', lw=1, zorder=4)
            ax.add_patch(base)
        ax.scatter(0, 0, color='red', s=45, zorder=5)
    else:
        ax.plot([0, 380 * np.sin(np.radians(-45))], [0, 380 * np.cos(np.radians(-45))], color='#475569', lw=2, zorder=3)
        ax.plot([0, 380 * np.sin(np.radians(45))], [0, 380 * np.cos(np.radians(45))], color='#475569', lw=2, zorder=3)
        ax.plot(fence_x, fence_y, color='#475569', lw=2, zorder=3)
        ax.scatter(0, 0, marker='D', color='#94a3b8', s=40, zorder=4)

def draw_zoned_plot(ax, df, metric, title, vmin, vmax, cmap='coolwarm', unit='', is_ev=False):
    draw_field_skeleton(ax, draw_infield=False) 
    df['Zone'] = df.apply(lambda row: assign_zone(row['Distance'], row['Direction']), axis=1)
    zone_avgs = df.groupby('Zone')[metric].mean()
    norm = mcolors.Normalize(vmin=vmin, vmax=vmax)
    colormap = plt.get_cmap(cmap)
    for zone_name, config in ZONES_CONFIG.items():
        avg_val = zone_avgs.get(zone_name, np.nan)
        if pd.isna(avg_val):
            color = '#f1f5f9'
            text_val = "N/A"
        else:
            color = colormap(norm(avg_val))
            text_val = f"{avg_val:.1f}{unit}"
        font_size = 11
        if is_ev and zone_name.startswith('IF'):
            font_size = 8
        wedge = Wedge(center=(0, 0), r=config['r_inner'] + config['width'], 
                      theta1=config['theta1'], theta2=config['theta2'], 
                      width=config['width'], facecolor=color, edgecolor='#cbd5e1', lw=1.5, alpha=0.85, zorder=1)
        ax.add_patch(wedge)
        text_x = config['text_r'] * np.cos(np.radians(config['text_theta']))
        text_y = config['text_r'] * np.sin(np.radians(config['text_theta']))
        ax.text(text_x, text_y, text_val, ha='center', va='center', fontsize=font_size, fontweight='bold', 
                color='#0f172a', bbox=dict(facecolor='white', alpha=0.75, edgecolor='#e2e8f0', boxstyle='round,pad=0.3'), zorder=4)
                
    ax.set_xlim(-300, 300); ax.set_ylim(-30, 410); ax.set_aspect('equal')
    ax.set_xticks([]); ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_visible(True)
        spine.set_edgecolor('black')
        spine.set_linewidth(1)
        
    ax.set_title(title, fontsize=13, fontweight='bold', pad=10, color='#1e293b')
    sm = plt.cm.ScalarMappable(cmap=colormap, norm=norm)
    sm.set_array([])
    cbar = plt.colorbar(sm, ax=ax, fraction=0.04, pad=0.04)
    cbar.ax.tick_params(labelsize=9)
    cbar.set_label(f"Avg {metric}", fontsize=10, weight='bold', color='#475569')

def draw_strike_zone_plot(ax, df, metric, title, vmin, vmax, cmap='coolwarm', unit='', is_ev=False):
    df['SZ_Zone'] = df.apply(lambda row: assign_sz_zone(row['PlateLocSide'], row['PlateLocHeight']), axis=1)
    zone_avgs = df.groupby('SZ_Zone')[metric].mean()
    norm = mcolors.Normalize(vmin=vmin, vmax=vmax)
    colormap = plt.get_cmap(cmap)
    for zone, rect in SZ_ZONES_CONFIG.items():
        avg_val = zone_avgs.get(zone, np.nan)
        color = colormap(norm(avg_val)) if not pd.isna(avg_val) else '#f1f5f9'
        if pd.isna(avg_val):
            text_val = "N/A"
        else:
            text_val = f"{avg_val:.1f}{unit}" if not is_ev else f"{avg_val:.1f}"
        patch = Rectangle((rect['x'], rect['y']), rect['w'], rect['h'], 
                          facecolor=color, edgecolor='#94a3b8', lw=1.5, zorder=1)
        ax.add_patch(patch)
        cx = rect['x'] + rect['w']/2
        cy = rect['y'] + rect['h']/2
        font_size = 10 if zone.startswith('Z') else 8
        ax.text(cx, cy, text_val, ha='center', va='center', fontsize=font_size, fontweight='bold',
                color='#0f172a', bbox=dict(facecolor='white', alpha=0.7, edgecolor='none', pad=1), zorder=3)
    sz_border = Rectangle((-0.833, 1.5), 1.666, 2.0, fill=False, edgecolor='black', lw=2.5, zorder=2)
    ax.add_patch(sz_border)
    hp_x = [-0.708, 0.708, 0.708, 0, -0.708]
    hp_y = [0, 0, 0.25, 0.5, 0.25] 
    hp = Polygon(np.column_stack((hp_x, hp_y)), facecolor='white', edgecolor='black', lw=1.5, zorder=2)
    ax.add_patch(hp)
    
    ax.set_xlim(-2, 2); ax.set_ylim(0, 4.5); ax.set_aspect('equal')
    ax.set_xticks([]); ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_visible(True)
        spine.set_edgecolor('black')
        spine.set_linewidth(1)
        
    ax.set_title(title, fontsize=13, fontweight='bold', pad=10, color='#1e293b')
    sm = plt.cm.ScalarMappable(cmap=colormap, norm=norm)
    sm.set_array([])
    cbar = plt.colorbar(sm, ax=ax, fraction=0.04, pad=0.04)
    cbar.ax.tick_params(labelsize=9)
    cbar.set_label(f"Avg {metric}", fontsize=10, weight='bold', color='#475569')

def draw_contact_plot(ax, df, title="Contact Depth Position"):
    df_cp = df.copy()
    df_cp['CP_X_in'] = df_cp['ContactPositionX'] * 12
    df_cp['CP_Z_in'] = df_cp['ContactPositionZ'] * 12
    
    ax.grid(True, linestyle='--', alpha=0.6, color='#cbd5e1', zorder=0)
    ax.axhline(0, color='black', lw=1.5, zorder=1)
    ax.axvline(0, color='black', lw=1.5, zorder=1)
    
    hp_z = [0, -8.5, -8.5, 8.5, 8.5, 0] 
    hp_x = [0, 8.5, 17, 17, 8.5, 0] 
    hp = Polygon(np.column_stack((hp_z, hp_x)), facecolor='#f1f5f9', edgecolor='black', lw=1.5, zorder=2)
    ax.add_patch(hp)
    
    sc = ax.scatter(df_cp['CP_Z_in'], df_cp['CP_X_in'], 
                    c=df_cp['ExitSpeed'], cmap='coolwarm', vmin=75, vmax=100,
                    s=65, edgecolors='#0f172a', lw=0.75, zorder=5)
                    
    ax.set_xlim(-30, 30); ax.set_ylim(-5, 55); ax.set_aspect('equal')
    ax.set_xticks(np.arange(-30, 31, 10))
    ax.set_yticks(np.arange(0, 51, 10))
    
    for spine in ax.spines.values():
        spine.set_visible(True)
        spine.set_edgecolor('black')
        spine.set_linewidth(1)
    
    ax.set_title(title, fontsize=13, fontweight='bold', pad=10, color='#1e293b')
    ax.set_xlabel("Side to Side (inches)", fontsize=10, fontweight='bold', color='#64748b')
    ax.set_ylabel("Out in Front (inches)", fontsize=10, fontweight='bold', color='#64748b')
    
    cbar = plt.colorbar(sc, ax=ax, fraction=0.04, pad=0.04)
    cbar.ax.tick_params(labelsize=9)
    cbar.set_label("Exit Velocity (mph)", fontsize=10, weight='bold', color='#475569')

# --- FILE UPLOAD ---
uploaded_file = st.file_uploader("Upload Trackman CSV", type=['csv'])

if uploaded_file is not None:
    try:
        df = pd.read_csv(uploaded_file)
    except UnicodeDecodeError:
        uploaded_file.seek(0)
        df = pd.read_csv(uploaded_file, encoding='latin1')
    
    required_cols = ['ExitSpeed', 'Direction', 'Distance', 'Angle', 'HitSpinRate', 'HangTime', 
                     'PlateLocHeight', 'PlateLocSide', 'ContactPositionX', 'ContactPositionZ']
    missing = [c for c in required_cols if c not in df.columns]
    
    if missing:
        st.error(f"Missing columns in CSV: {missing}")
    else:
        df_hit = df.dropna(subset=['ExitSpeed', 'Direction', 'Distance', 'Angle', 'PlateLocHeight', 'PlateLocSide', 'ContactPositionX', 'ContactPositionZ']).copy()
        
        if df_hit.empty:
            st.error("No valid batted ball data found in this CSV.")
        else:
            batters = df_hit['Batter'].unique()
            selected_batter = st.selectbox("Select Hitter:", sorted(batters))
            batter_data = df_hit[df_hit['Batter'] == selected_batter].copy()
            
            # --- METRICS ---
            total_swings = len(batter_data)
            max_ev = batter_data['ExitSpeed'].max()
            
            # Hard Hit Calculation (Within 10% of Max EV)
            hard_hit_threshold = max_ev * 0.90
            total_hh = len(batter_data[batter_data['ExitSpeed'] >= hard_hit_threshold])
            hh_pct = (total_hh / total_swings) * 100 if total_swings > 0 else 0.0
            
            avg_ev = batter_data['ExitSpeed'].mean()
            avg_la = batter_data['Angle'].mean()
            avg_dist = batter_data['Distance'].mean()
            max_dist = batter_data['Distance'].max()
            avg_spin = batter_data['HitSpinRate'].mean()
            avg_hang = batter_data['HangTime'].mean()
            
            side_raw = batter_data['BatterSide'].iloc[0] if 'BatterSide' in batter_data.columns else "Undefined"
            batter_side = get_batter_side(side_raw)
            session_date = batter_data['Date'].iloc[0] if 'Date' in batter_data.columns else "Unknown Date"
            
            # --- WEB HEADER ---
            st.markdown(f"""
                <div class="header-container">
                    <table style="width:100%; border:none; border-collapse:collapse; background:transparent;">
                        <tr style="background:transparent;">
                            <td style="width:100px; border:none; padding:0; vertical-align:middle;">
                                <img src="Logo.png" style="width:90px; height:auto;">
                            </td>
                            <td style="border:none; padding-left:20px; vertical-align:middle;">
                                <div style="font-size: 28px; font-weight: 800; color: #0f172a; line-height:1.1;">{selected_batter} <span style="color:#3b82f6; font-size:22px;">| {batter_side}</span></div>
                                <div style="font-size: 15px; font-weight: 500; color: #64748b; margin-top: 4px;">OMAHA BP REPORTS • Recorded: {session_date}</div>
                            </td>
                        </tr>
                    </table>
                </div>
            """, unsafe_allow_html=True)
            
            # --- WEB TILES ---
            st.markdown("<h4 style='color:#1e293b; margin-bottom:15px;'>Performance Overview</h4>", unsafe_allow_html=True)
            
            # Expanded to 10 columns for the two new Hard Hit metrics
            t_cols = st.columns(10)
            metrics = [
                ("Total Swings", f"{int(total_swings)}", t_cols[0]), 
                ("Total HH", f"{int(total_hh)}", t_cols[1]),
                ("Hard Hit %", f"{hh_pct:.1f}%", t_cols[2]),
                ("Avg EV", f"{avg_ev:.1f} mph", t_cols[3]),
                ("Max EV", f"{max_ev:.1f} mph", t_cols[4]), 
                ("Avg LA", f"{avg_la:.1f}°", t_cols[5]),
                ("Avg Dist.", f"{avg_dist:.0f} ft", t_cols[6]), 
                ("Max Dist.", f"{max_dist:.0f} ft", t_cols[7]),
                ("Avg Spin", f"{avg_spin:.0f} rpm", t_cols[8]), 
                ("Avg Hang", f"{avg_hang:.2f} s", t_cols[9])
            ]
            for label, value, col in metrics:
                col.markdown(f"""
                    <div class="metric-card">
                        <div class="metric-label">{label}</div>
                        <div class="metric-value">{value}</div>
                    </div>
                """, unsafe_allow_html=True)
            st.markdown("<br>", unsafe_allow_html=True)

            # --- WEB PLOTS (ROW 1 - FIELD SPRAYS) ---
            p_col1, p_col2, p_col3 = st.columns([1, 1, 1])
            with p_col1:
                fig1, ax1 = plt.subplots(figsize=(7, 7), dpi=100)
                draw_field_skeleton(ax1, draw_infield=True)
                gb = batter_data[batter_data['Angle'] < 10]
                ld = batter_data[(batter_data['Angle'] >= 10) & (batter_data['Angle'] <= 25)]
                fb = batter_data[batter_data['Angle'] > 25]
                for sub_df, color, lbl in [(gb, '#3b82f6', 'GB (<10°)'), (ld, '#22c55e', 'LD (10°-25°)'), (fb, '#ef4444', 'FB (>25°)')]:
                    if not sub_df.empty:
                        x = sub_df['Distance'] * np.sin(np.radians(sub_df['Direction']))
                        y = sub_df['Distance'] * np.cos(np.radians(sub_df['Direction']))
                        ax1.scatter(x, y, color=color, s=55, edgecolors='#0f172a', linewidths=0.75, label=lbl, zorder=6)
                
                ax1.set_xlim(-300, 300); ax1.set_ylim(-30, 410); ax1.set_aspect('equal')
                ax1.set_xticks([]); ax1.set_yticks([])
                for spine in ax1.spines.values():
                    spine.set_visible(True)
                    spine.set_edgecolor('black')
                    spine.set_linewidth(1)
                    
                ax1.set_title("Batted Ball Profile", fontsize=13, fontweight='bold', pad=10, color='#1e293b')
                ax1.legend(loc='lower left', frameon=True, facecolor='white', edgecolor='#e2e8f0', fontsize=9)
                st.pyplot(fig1)

            with p_col2:
                fig2, ax2 = plt.subplots(figsize=(7, 7), dpi=100)
                draw_zoned_plot(ax2, batter_data, metric='ExitSpeed', title="Avg EV by Field Quadrant", vmin=75, vmax=100, cmap='coolwarm', unit='', is_ev=True)
                st.pyplot(fig2)

            with p_col3:
                fig3, ax3 = plt.subplots(figsize=(7, 7), dpi=100)
                draw_zoned_plot(ax3, batter_data, metric='Angle', title="Avg LA by Field Quadrant", vmin=0, vmax=35, cmap='coolwarm', unit='°')
                st.pyplot(fig3)

            st.markdown("<br>", unsafe_allow_html=True)

            # --- WEB PLOTS (ROW 2 - STRIKE ZONES & CONTACT) ---
            sz_col1, sz_col2, cp_col3 = st.columns([1, 1, 1])
            with sz_col1:
                fig4, ax4 = plt.subplots(figsize=(7, 7), dpi=100)
                draw_strike_zone_plot(ax4, batter_data, metric='ExitSpeed', title="Avg EV by Pitch Location", vmin=75, vmax=100, cmap='coolwarm', is_ev=True)
                st.pyplot(fig4)
            with sz_col2:
                fig5, ax5 = plt.subplots(figsize=(7, 7), dpi=100)
                draw_strike_zone_plot(ax5, batter_data, metric='Angle', title="Avg LA by Pitch Location", vmin=0, vmax=35, cmap='coolwarm', unit='°')
                st.pyplot(fig5)
            with cp_col3:
                fig6, ax6 = plt.subplots(figsize=(7, 7), dpi=100)
                draw_contact_plot(ax6, batter_data, title="Contact Depth Position")
                st.pyplot(fig6)

            # --- PDF GENERATOR ---
            def create_pdf():
                pdf_buffer = BytesIO()
                fig = plt.figure(figsize=(14, 11)) 
                
                # Page Border
                page_border = Rectangle((0.015, 0.015), 0.97, 0.97, fill=False, edgecolor='black', lw=1, transform=fig.transFigure)
                fig.patches.append(page_border)

                # PDF Header
                fig.text(0.04, 0.94, f"{selected_batter}  |  {batter_side}", fontsize=26, fontweight='bold', color='#0f172a')
                fig.text(0.04, 0.91, f"OMAHA BP REPORTS • Profile Date: {session_date}", fontsize=14, color='#64748b')
                fig.add_artist(plt.Line2D((0.04, 0.89), (0.89, 0.89), color='#cbd5e1', linewidth=1.5))

                # Styled PDF Metric Tiles
                box_width = 0.075 
                pad = 0.005 
                x_offsets = np.linspace(0.025, 0.885, 10).tolist()
                
                pdf_metrics = [
                    ("TOTAL SWINGS", f"{int(total_swings)}"),
                    ("TOTAL HH", f"{int(total_hh)}"),
                    ("HARD HIT %", f"{hh_pct:.1f}%"),
                    ("AVG EV", f"{avg_ev:.1f} mph"),
                    ("MAX EV", f"{max_ev:.1f} mph"),
                    ("AVG LA", f"{avg_la:.1f}°"),
                    ("AVG DIST", f"{avg_dist:.0f} ft"),
                    ("MAX DIST", f"{max_dist:.0f} ft"),
                    ("AVG SPIN", f"{avg_spin:.0f} rpm"),
                    ("AVG HANG", f"{avg_hang:.2f} s")
                ]
                
                for idx, (label, val) in enumerate(pdf_metrics):
                    bbox = FancyBboxPatch((x_offsets[idx], 0.80), box_width, 0.06, boxstyle=f"round,pad={pad}", 
                                          fc="#f8fafc", ec="#cbd5e1", lw=1.5, transform=fig.transFigure)
                    fig.patches.append(bbox)
                    center_x = x_offsets[idx] + (box_width / 2)
                    fig.text(center_x, 0.84, label, fontsize=7.5, fontweight='bold', color='#64748b', ha='center')
                    fig.text(center_x, 0.815, val, fontsize=12, fontweight='bold', color='#0f172a', ha='center')

                # Row 1 Charts (Field Plots)
                ax1_pdf = fig.add_axes([0.025, 0.42, 0.28, 0.34])
                draw_field_skeleton(ax1_pdf, draw_infield=True)
                for sub_df, color, lbl in [(gb, '#3b82f6', 'GB (<10°)'), (ld, '#22c55e', 'LD (10°-25°)'), (fb, '#ef4444', 'FB (>25°)')]:
                    if not sub_df.empty:
                        ax1_pdf.scatter(sub_df['Distance'] * np.sin(np.radians(sub_df['Direction'])), 
                                        sub_df['Distance'] * np.cos(np.radians(sub_df['Direction'])), 
                                        color=color, s=45, edgecolors='#0f172a', linewidths=0.5, label=lbl, zorder=6)
                ax1_pdf.set_xlim(-300, 300); ax1_pdf.set_ylim(-30, 410); ax1_pdf.set_aspect('equal')
                
                ax1_pdf.set_xticks([]); ax1_pdf.set_yticks([])
                for spine in ax1_pdf.spines.values():
                    spine.set_visible(True)
                    spine.set_edgecolor('black')
                    spine.set_linewidth(1)
                    
                ax1_pdf.set_title("Batted Ball Profile", fontsize=11, fontweight='bold', pad=8)
                ax1_pdf.legend(loc='lower left', frameon=True, fontsize=8)

                ax2_pdf = fig.add_axes([0.345, 0.42, 0.28, 0.34])
                draw_zoned_plot(ax2_pdf, batter_data, metric='ExitSpeed', title="Avg Exit Velocity Profile", vmin=75, vmax=100, cmap='coolwarm', unit='', is_ev=True)

                ax3_pdf = fig.add_axes([0.665, 0.42, 0.28, 0.34])
                draw_zoned_plot(ax3_pdf, batter_data, metric='Angle', title="Avg Launch Angle Profile", vmin=0, vmax=35, cmap='coolwarm', unit='°')

                # Row 2 Charts (Strike Zones + Contact Position)
                ax4_pdf = fig.add_axes([0.025, 0.06, 0.28, 0.34])
                draw_strike_zone_plot(ax4_pdf, batter_data, metric='ExitSpeed', title="Avg EV by Pitch Location", vmin=75, vmax=100, cmap='coolwarm', is_ev=True)
                
                ax5_pdf = fig.add_axes([0.345, 0.06, 0.28, 0.34])
                draw_strike_zone_plot(ax5_pdf, batter_data, metric='Angle', title="Avg LA by Pitch Location", vmin=0, vmax=35, cmap='coolwarm', unit='°')

                ax6_pdf = fig.add_axes([0.665, 0.06, 0.28, 0.34])
                draw_contact_plot(ax6_pdf, batter_data, title="Contact Depth Position")

                fig.savefig(pdf_buffer, format='pdf', dpi=150)
                plt.close(fig)
                return pdf_buffer.getvalue()

            st.divider()
            st.markdown("### Export Report Documents")
            pdf_bytes = create_pdf()
            safe_name = selected_batter.replace(", ", "_").replace(" ", "_")
            st.download_button(
                label=f"📄 Download Professional PDF Report for {selected_batter}",
                data=pdf_bytes,
                file_name=f"BP_Analytics_Report_{safe_name}.pdf",
                mime="application/pdf"
            )
