# Bootstrap grid layout snippet for side-by-side layout
# Include the custom CSS for Bootstrap grid at the top of your file

"""
<style>
/* Bootstrap grid container for side-by-side layout */
.bs-grid-container {
    display: flex;
    width: 100%;
    margin: 0;
    padding: 0;
}
.bs-grid-left {
    flex: 6;
    padding-right: 10px;
    min-width: 600px;
}
.bs-grid-right {
    flex: 6;
    padding-left: 0;
    min-width: 600px;
}
@media (max-width: 1200px) {
    .bs-grid-container {
        flex-direction: column;
    }
    .bs-grid-left, .bs-grid-right {
        flex: 100%;
        padding: 0;
        width: 100%;
        min-width: 100%;
    }
}
</style>
"""

# Start the Bootstrap grid container
st.markdown('<div class="bs-grid-container">', unsafe_allow_html=True)

# Left container for the table
st.markdown('<div class="bs-grid-left">', unsafe_allow_html=True)

# Add a card for the table content
st.markdown('<div class="card shadow-sm mb-3"><div class="card-header bg-primary text-white d-flex justify-content-between align-items-center"><span>Train Data</span><span class="badge bg-light text-dark rounded-pill">Select stations to display on map</span></div><div class="card-body p-0">', unsafe_allow_html=True)

# Data table with selection functionality
edited_df = st.data_editor(
    df,
    hide_index=True,
    column_config={
        "Select": st.column_config.CheckboxColumn("Select", help="Select to show on map", default=False),
        "Train No.": st.column_config.TextColumn("Train No.", help="Train Number"),
        "FROM-TO": st.column_config.TextColumn("FROM-TO", help="Source to Destination"),
        "IC Entry Delay": st.column_config.TextColumn("IC Entry Delay", help="Entry Delay"),
        "Delay": st.column_config.TextColumn("Delay", help="Delay in Minutes")
    },
    disabled=[col for col in df.columns if col != 'Select'],
    use_container_width=True,
    height=600,
    num_rows="dynamic"
)

# Add a footer to the card with information about the data
selected_count = len(edited_df[edited_df['Select']])
st.markdown(f'<div class="card-footer bg-light d-flex justify-content-between align-items-center"><span>Total Rows: {len(df)}</span><span>Selected: {selected_count}</span></div>', unsafe_allow_html=True)
st.markdown('</div></div>', unsafe_allow_html=True)

# Close the left container
st.markdown('</div>', unsafe_allow_html=True)

# Right container for the map
st.markdown('<div class="bs-grid-right">', unsafe_allow_html=True)

# Add a card for the map content
st.markdown('<div class="card mb-3"><div class="card-header bg-secondary text-white d-flex justify-content-between align-items-center"><span>Interactive GPS Map</span><span class="badge bg-light text-dark rounded-pill">Showing selected stations</span></div><div class="card-body p-0">', unsafe_allow_html=True)

# Create and display the interactive map
m = folium.Map(
    location=[16.5167, 80.6167],  # Centered around Vijayawada
    zoom_start=7,
    control_scale=True
)

# Add interactive map layers, markers, etc.
# ...

# Render the map
folium_static(m, width=650, height=600)

st.markdown('</div></div>', unsafe_allow_html=True)

# Close the right container
st.markdown('</div>', unsafe_allow_html=True)

# Close the grid container
st.markdown('</div>', unsafe_allow_html=True)
