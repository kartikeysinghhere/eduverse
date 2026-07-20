import plotly.graph_objects as go
import plotly.express as px

def apply_neon_theme(fig, title=None):
    neon_colors = ['#00f2fe', '#4facfe', '#43e97b', '#fa709a', '#f093fb', '#ffd700']

    fig.update_layout(
        title={
            'text': title,
            'y': 0.95,
            'x': 0.5,
            'xanchor': 'center',
            'yanchor': 'top',
            'font': {'size': 20, 'color': '#ffffff', 'family': 'Inter'}
        },
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font_color='white',
        margin=dict(l=40, r=40, t=60, b=40),
        hovermode='closest',
        showlegend=True,
        legend=dict(
            bgcolor='rgba(0,0,0,0)',
            font=dict(color='#94a3b8')
        )
    )

    fig.update_xaxes(
        showgrid=False,
        zeroline=False,
        showline=False,
        title_text='',
        tickfont=dict(color='#64748b')
    )

    fig.update_yaxes(
        showgrid=False,
        zeroline=False,
        showline=False,
        title_text='',
        tickfont=dict(color='#64748b')
    )

    if hasattr(fig, 'data'):
        for i, trace in enumerate(fig.data):
            if hasattr(trace, 'type') and trace.type == 'pie':
                trace.marker.colors = neon_colors
            elif 'marker' in trace:
                if not hasattr(trace.marker, 'color') or trace.type == 'bar':
                    trace.marker.color = neon_colors[i % len(neon_colors)]

                if hasattr(trace, 'type') and 'bar' in trace.type:
                    trace.marker.line = dict(width=0)

    return fig
