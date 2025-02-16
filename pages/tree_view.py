import streamlit as st
import json
from train_tree import TrainScheduleTree
import pandas as pd

# Page configuration
st.set_page_config(
    page_title="Train Schedule Tree - Train Tracking System",
    page_icon="🌳",
    layout="wide"
)

# Initialize train schedule tree if not in session state
if 'train_tree' not in st.session_state:
    st.session_state['train_tree'] = TrainScheduleTree.build_from_json('bhanu.json')

# Page title
st.title("🌳 Train Schedule Tree")
st.markdown("Binary tree visualization of train schedules")

def display_tree_node(node_data, level=0):
    if node_data is None:
        return
        
    # Create indentation based on level
    indent = "  " * level
    
    # Display current node
    st.markdown(f"{indent}📍 Train {node_data['train_number']}")
    
    # Recursively display left and right children
    if node_data['left']:
        st.markdown(f"{indent}↙️ Left:")
        display_tree_node(node_data['left'], level + 1)
    if node_data['right']:
        st.markdown(f"{indent}↘️ Right:")
        display_tree_node(node_data['right'], level + 1)

# Get tree structure
tree_structure = st.session_state['train_tree'].get_tree_structure()

# Create two columns
col1, col2 = st.columns([2, 3])

with col1:
    st.subheader("Tree Structure")
    display_tree_node(tree_structure)

with col2:
    st.subheader("Search Train Schedule")
    search_train = st.text_input("Enter train number")
    
    if search_train:
        schedule = st.session_state['train_tree'].find(search_train)
        if schedule:
            st.success(f"Found schedule for train {search_train}")
            
            # Convert schedule to DataFrame for better display
            rows = []
            for station, timings in schedule.items():
                rows.append({
                    'Station': station,
                    'Arrival': timings['arrival'],
                    'Departure': timings['departure']
                })
            
            schedule_df = pd.DataFrame(rows)
            st.dataframe(schedule_df)
        else:
            st.error(f"No schedule found for train {search_train}")
