import streamlit as st
import pandas as pd
import base64
from io import BytesIO
from typing import Dict, Optional

def get_train_class_color(train_no: str) -> Dict[str, str]:
    """
    Get color settings for a train number based on its first digit.
    
    Args:
        train_no: Train number as string
        
    Returns:
        Dictionary with color properties
    """
    if not train_no or not isinstance(train_no, str) or len(train_no) == 0:
        return {"color": "#333333", "bg_color": "#ffffff"}
    
    first_digit = train_no[0]
    
    # Color mapping by first digit
    color_map = {
        "1": {"color": "#d63384", "bg_color": "#f8f1f5"},  # Pink
        "2": {"color": "#6f42c1", "bg_color": "#f3f0f9"},  # Purple
        "3": {"color": "#0d6efd", "bg_color": "#edf5ff"},  # Blue
        "4": {"color": "#20c997", "bg_color": "#ebfbf5"},  # Teal
        "5": {"color": "#198754", "bg_color": "#ebf5f0"},  # Green
        "6": {"color": "#0dcaf0", "bg_color": "#ebfafd"},  # Cyan
        "7": {"color": "#fd7e14", "bg_color": "#fff4eb"},  # Orange
        "8": {"color": "#dc3545", "bg_color": "#fbedee"},  # Red
        "9": {"color": "#6610f2", "bg_color": "#f2ebfd"},  # Indigo
        "0": {"color": "#333333", "bg_color": "#f5f5f5"}   # Gray
    }
    
    return color_map.get(first_digit, {"color": "#333333", "bg_color": "#ffffff"})

def format_train_df_as_html(df: pd.DataFrame, 
                          train_column: str = "Train No.", 
                          height: Optional[int] = 600,
                          with_checkboxes: bool = False) -> str:
    """
    Convert a DataFrame to styled HTML with colored train numbers.
    
    Args:
        df: DataFrame to format
        train_column: Name of the column containing train numbers
        height: Height of the table in pixels (or None for auto)
        with_checkboxes: Whether to add interactive checkboxes in the first column
        
    Returns:
        HTML string of the styled table
    """
    if df.empty:
        return "<div>No data available</div>"
    
    # Generate a unique ID for this table
    table_id = f"train-table-{pd.util.hash_pandas_object(df).sum() % 1000000}"
    
    # Start building HTML table
    html = f"""
    <div style="max-height: {height}px; overflow-y: auto; margin-bottom: 20px;">
    <table id="{table_id}" class="styled-table" style="width: 100%; border-collapse: collapse;">
        <thead>
            <tr>
    """
    
    # Add headers
    for col in df.columns:
        # Skip the Select column if we're using checkboxes - we'll add our own
        if with_checkboxes and col == 'Select':
            html += f'<th style="position: sticky; top: 0; background-color: #1e3c72; color: white; padding: 8px; text-align: center; border-bottom: 2px solid #ddd; width: 60px;">Select</th>'
        else:
            html += f'<th style="position: sticky; top: 0; background-color: #1e3c72; color: white; padding: 8px; text-align: left; border-bottom: 2px solid #ddd;">{col}</th>'
    
    html += """
            </tr>
        </thead>
        <tbody>
    """
    
    # Add rows with styled train numbers
    for i, (_, row) in enumerate(df.iterrows()):
        row_id = f"row-{i}"
        html += f'<tr id="{row_id}" style="border-bottom: 1px solid #ddd; background-color: #ffffff;">'
        
        for col in df.columns:
            cell_value = row.get(col, "")
            
            # For the Select column, add a checkbox if requested
            if with_checkboxes and col == 'Select':
                is_checked = bool(cell_value) if pd.notna(cell_value) else False
                checked_attr = 'checked="checked"' if is_checked else ''
                html += f'''
                <td style="padding: 8px; text-align: center;">
                    <input type="checkbox" id="chk-{row_id}" class="select-station" {checked_attr}
                           style="width: 18px; height: 18px; cursor: pointer;" 
                           onchange="this.closest('tr').classList.toggle('selected-row', this.checked)" />
                </td>
                '''
            # Apply special styling for train numbers
            elif col == train_column and str(cell_value).strip():
                train_no = str(cell_value).strip()
                colors = get_train_class_color(train_no)
                
                html += f"""
                <td style="padding: 8px; text-align: center; color: {colors['color']}; 
                    background-color: {colors['bg_color']}; font-weight: bold; 
                    border-left: 4px solid {colors['color']}; border-radius: 4px;">
                    {train_no}
                </td>
                """
            else:
                # Regular styling for other cells
                cell_style = ""
                if isinstance(cell_value, str) and ("+" in cell_value or "LATE" in cell_value):
                    cell_style = "color: #dc3545; font-weight: bold;"
                elif isinstance(cell_value, str) and "EARLY" in cell_value:
                    cell_style = "color: #198754; font-weight: bold;"
                
                html += f'<td style="padding: 8px; {cell_style}">{cell_value}</td>'
        
        html += '</tr>'
    
    html += """
        </tbody>
    </table>
    </div>
    """
    
    # Add JavaScript for interactive features if checkboxes are enabled
    if with_checkboxes:
        html += f"""
        <script>
        // Add listeners to checkboxes
        document.querySelectorAll('#{table_id} .select-station').forEach(checkbox => {{
            checkbox.addEventListener('change', function() {{
                // Handle checkbox change
                const selectedCount = document.querySelectorAll('#{table_id} .select-station:checked').length;
                document.getElementById('selected-count').textContent = selectedCount;
                
                // You can add more JavaScript here to update other parts of the page
            }});
        }});
        </script>
        """
    
    return html

def display_styled_train_table(df: pd.DataFrame, 
                             train_column: str = "Train No.", 
                             height: int = 600,
                             key: Optional[str] = None) -> None:
    """
    Display a DataFrame as a styled HTML table with colored train numbers.
    
    Args:
        df: DataFrame to display
        train_column: Name of the column containing train numbers
        height: Height of the table in pixels
        key: Optional key for the component
    """
    html = format_train_df_as_html(df, train_column, height)
    st.markdown(html, unsafe_allow_html=True)

def download_styled_table_as_html(df: pd.DataFrame, 
                                 train_column: str = "Train No.",
                                 filename: str = "train_data.html") -> None:
    """
    Create a download button for the styled table as an HTML file.
    
    Args:
        df: DataFrame to convert
        train_column: Name of the column containing train numbers
        filename: Name of the downloaded file
    """
    html = format_train_df_as_html(df, train_column, height=None)
    
    # Add HTML document structure
    full_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Train Data</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; }}
            .styled-table {{ width: 100%; border-collapse: collapse; }}
            .styled-table th {{ background-color: #1e3c72; color: white; padding: 12px; text-align: left; }}
            .styled-table td {{ padding: 8px; border-bottom: 1px solid #ddd; }}
            .styled-table tr:hover {{ background-color: #f5f5f5; }}
        </style>
    </head>
    <body>
        <h1>Train Data</h1>
        <p>Generated on {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        {html}
    </body>
    </html>
    """
    
    # Convert to bytes for download
    b64 = base64.b64encode(full_html.encode()).decode()
    href = f'<a href="data:text/html;base64,{b64}" download="{filename}" class="btn btn-primary">Download HTML Table</a>'
    
    st.markdown(href, unsafe_allow_html=True)