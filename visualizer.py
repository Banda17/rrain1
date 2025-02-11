import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from typing import Dict

class Visualizer:
    @staticmethod
    def create_train_position_map(data: pd.DataFrame) -> go.Figure:
        """Create a visual representation of train positions"""
        fig = go.Figure()

        # Create a horizontal line representing the route
        stations = data['station'].unique()
        x_positions = list(range(len(stations)))
        
        # Add route line
        fig.add_trace(go.Scatter(
            x=x_positions,
            y=[0] * len(stations),
            mode='lines',
            line=dict(color='blue', width=2),
            name='Route'
        ))

        # Add station markers
        fig.add_trace(go.Scatter(
            x=x_positions,
            y=[0] * len(stations),
            mode='markers+text',
            marker=dict(size=12, color='red'),
            text=stations,
            textposition='top center',
            name='Stations'
        ))

        # Add train position
        current_station_idx = data['station'].iloc[-1]
        fig.add_trace(go.Scatter(
            x=[stations.tolist().index(current_station_idx)],
            y=[0],
            mode='text',
            text=['🚂'],
            textposition='top center',
            name='Train'
        ))

        fig.update_layout(
            title="Train Position Visualization",
            showlegend=False,
            yaxis_visible=False,
            yaxis_showticklabels=False,
            plot_bgcolor='white'
        )

        return fig

    @staticmethod
    def create_delay_histogram(data: pd.DataFrame) -> go.Figure:
        """Create a histogram of delays"""
        fig = px.histogram(
            data,
            x='delay',
            title='Distribution of Delays',
            labels={'delay': 'Delay (minutes)'},
            color_discrete_sequence=['blue']
        )
        
        fig.update_layout(
            showlegend=False,
            plot_bgcolor='white'
        )

        return fig
