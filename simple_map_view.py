import streamlit as st

def draw_station_map():
    """Draw a simple ASCII-style map of stations"""
    st.text("""
    Station Map:
    
    VNEC ━━━━ GALA ━━━━ MBD ━━━━ GWM ━━━━ PAVP
         │                    │
         │                    │
         │                    │
         └────────────────────┘
    """)

def show_train_location(station_code):
    """Show where the train is on the map"""
    stations = {
        'VNEC': 'Secunderabad',
        'GALA': 'Gala',
        'MBD': 'Malakpet',
        'GWM': 'Gandhigram',
        'PAVP': 'Pavalavagu',
        'BZA': 'Vijayawada'
    }
    station_name = stations.get(station_code, station_code)
    st.markdown(f"**Current Location: {station_name} ({station_code})**")

def render_simple_map(selected_train=None):
    """Render the simple map view"""
    st.subheader("🗺️ Simple Route Map")
    draw_station_map()
    
    if selected_train and 'station' in selected_train:
        show_train_location(selected_train['station'])
