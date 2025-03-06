"""
This is the core layout snippet to maintain side-by-side columns in Streamlit
using Bootstrap grid system.
"""

# 1. Add this CSS in your main file
css = """
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

# 2. Add this to your Streamlit app where you want the side-by-side layout
"""
# Add this at the start of your side-by-side section
st.markdown('<div class="bs-grid-container">', unsafe_allow_html=True)

# Left container for the table
st.markdown('<div class="bs-grid-left">', unsafe_allow_html=True)

# Your table content goes here
# ...
# For example: st.data_editor(your_dataframe)

st.markdown('</div>', unsafe_allow_html=True)  # Close left container

# Right container for the map
st.markdown('<div class="bs-grid-right">', unsafe_allow_html=True)

# Your map content goes here
# ...
# For example: folium_static(your_map)

st.markdown('</div>', unsafe_allow_html=True)  # Close right container

st.markdown('</div>', unsafe_allow_html=True)  # Close grid container
"""
