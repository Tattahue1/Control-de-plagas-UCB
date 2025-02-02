import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import numpy as np

# Set page config
st.set_page_config(
    page_title="Sistema de monitoreo",
    layout="wide"
)

# Title
st.markdown("<h1 style='text-align: center; color: white;'>Sistema de monitoreo de alerta temprana automática para polilla de papa en cultivos de papa en Tiraque</h1>", unsafe_allow_html=True)


# Function to fetch data
def fetch_weather_data():
    url = "https://watchcloud.piensadiferente.net/weather/api/device/get/list/sebas/data"
    try:
        response = requests.get(url)
        data = response.json()
        # Sort data by createdAt in descending order
        sorted_data = sorted(data, key=lambda x: datetime.strptime(x['createdAt'], '%Y-%m-%d %H:%M:%S'), reverse=True)
        # Filter for temperatures greater than 25 °C
        filtered_data = [entry for entry in sorted_data if entry['temp'] > 5]
        return filtered_data[:20][::-1]  # Get latest 10 entries and reverse to chronological order
    except Exception as e:
        st.error(f"Error fetching data: {e}")
        return []


# Fetch data
data = fetch_weather_data()

if data:
    # Get latest values
    latest = data[-1]

    # Create three columns for metrics
    col1, col2, col3 = st.columns(3)

    # Custom CSS for metrics
    st.markdown("""
        <style>
        .metric-container {
            background-color: #1F2A40;
            padding: 20px;
            border-radius: 10px;
            text-align: center;
        }
        .metric-label {
            color: #4cceac;
            font-size: 18px;
            font-weight: bold;
        }
        .metric-value {
            color: white;
            font-size: 24px;
            margin-top: 10px;
        }
        </style>
    """, unsafe_allow_html=True)

    # Display metrics
    with col1:
        st.markdown(f"""
            <div class="metric-container">
                <div class="metric-label">Temperatura</div>
                <div class="metric-value">🌡️ {latest['temp']}°C</div>
            </div>
        """, unsafe_allow_html=True)

    with col2:
        # Custom humidity gauge
        humidity = latest['hum']
        st.markdown("""
            <div class="metric-container">
                <div class="metric-label">Humedad Relativa</div>
                <div class="metric-value">💧 {}%</div>
            </div>
        """.format(humidity), unsafe_allow_html=True)

    with col3:
        st.markdown("""
            <div class="metric-container">
                <div class="metric-label">Presión</div>
                <div class="metric-value">🔽 {} mmHg</div>
            </div>
        """.format(latest['pres']), unsafe_allow_html=True)

    # Create DataFrame for plotting
    df = pd.DataFrame(data)
    df['createdAt'] = pd.to_datetime(df['createdAt'])
    df['time'] = df['createdAt'].dt.strftime('%H:%M:%S')

    # Normalize the data
    df['temp_normalized'] = (df['temp'] - df['temp'].min()) / (df['temp'].max() - df['temp'].min())
    df['hum_normalized'] = (df['hum'] - df['hum'].min()) / (df['hum'].max() - df['hum'].min())
    df['pres_normalized'] = (df['pres'] - df['pres'].min()) / (df['pres'].max() - df['pres'].min())

    # Create two columns for chart and description
    col_chart, col_desc = st.columns([2, 1])

    with col_chart:
        # Create line chart using plotly
        fig = go.Figure()

        # Add traces with normalized data
        fig.add_trace(go.Scatter(
            x=df['time'],
            y=df['temp_normalized'],
            name="Temperature",  # Label for the temperature line
            line=dict(color="#4cceac"),
            marker=dict(color="#4cceac"),  # Match marker color to line color
            text=df['temp'],  # Display temperature values as tags
            mode='lines+markers+text',  # Show lines, markers, and text
            textposition='top center'  # Position text above markers
        ))

        fig.add_trace(go.Scatter(
            x=df['time'],
            y=df['hum_normalized'],
            name="Humidity",  # Label for the humidity line
            line=dict(color="#6870fa"),
            marker=dict(color="#6870fa"),  # Match marker color to line color
            text=df['hum'],  # Display humidity values as tags
            mode='lines+markers+text',  # Show lines, markers, and text
            textposition='top center'  # Position text above markers
        ))

        fig.add_trace(go.Scatter(
            x=df['time'],
            y=df['pres_normalized'],
            name="Pressure",  # Label for the pressure line
            line=dict(color="#ffc658"),
            marker=dict(color="#ffc658"),  # Match marker color to line color
            text=df['pres'],  # Display pressure values as tags
            mode='lines+markers+text',  # Show lines, markers, and text
            textposition='top center'  # Position text above markers
        ))

        # Update layout
        fig.update_layout(
            title="Registro de Temperatura, Humedad y Presión",
            plot_bgcolor="#1F2A40",
            paper_bgcolor="#1F2A40",
            font=dict(color="#e0e0e0"),
            xaxis=dict(gridcolor="#2e3951"),
            yaxis=dict(gridcolor="#2e3951"),
            legend=dict(
                bgcolor="#1F2A40",
                bordercolor="#e0e0e0",
                title=dict(font=dict(color="#e0e0e0")),  # Legend title color
                font=dict(color="#e0e0e0")  # Legend text color
            )
        )

        st.plotly_chart(fig, use_container_width=True)

    with col_desc:
        # Weather description
        st.markdown("""
            <div style="background-color: #1F2A40; padding: 20px; border-radius: 10px;">
                <p style="color: #e0e0e0;">La temperatura actual es {}°C.</p>
                <p style="color: #e0e0e0;">La humedad actual es {}%.</p>
                <p style="color: #e0e0e0;">La presión atmosférica es {} mmHg.</p>
            </div>
        """.format(latest['temp'], latest['hum'], latest['pres']), unsafe_allow_html=True)

        # New block for the equations

        # Given values
        temperature = latest['temp']  # Temperature in °C

        # Random coefficients for demonstration
        a = 1.2  # Example value for intercept
        b = 0.37  # Example value for regression factor

        # Calculate Y, K, and t_min
        Y = a + b * temperature
        K = 1 / b
        t_min = -a / b

        # New block for the development rate
        st.markdown(f"""
            <div class="metric-container" style="background-color: #1F2A40; padding: 10px; border-radius: 10px; margin-top: 20px;">
                <div class="metric-label" style="color: #4cceac; font-size: 18px; font-weight: bold; text-align: center;">Los periodos de desarrollo de Polilla de la Papa</div>
                <p style="color: #e0e0e0; text-align: center; font-size: 20px; font-weight: bold;">Y = {Y:.2f} días</p>
            </p>
            </div>
        """, unsafe_allow_html=True)

        # Assuming latest values are available
        temperature = latest['temp']  # Example: 25°C
        humidity = latest['hum']  # Example: 60%
        pressure = latest['pres']  # Example: 1013 mmHg

        # Random coefficients for demonstration
        alpha = 0.01
        beta = 0.005
        gamma = 0.02
        delta = 1

        # Calculate PLI
        PLI = alpha * temperature + beta * humidity + gamma / pressure + delta

        # New block for PLI Calculation
        st.markdown(f"""
            <div class="metric-container" style="background-color: #1F2A40; padding: 10px; border-radius: 10px; margin-top: 20px;">
                <div class="metric-label" style="color: #4cceac; font-size: 18px; font-weight: bold; text-align: center;">IPPO (Índice de probabilidad de Polilla de la Papa)</div>
                <p style="color: #e0e0e0; text-align: center; font-size: 20px; font-weight: bold;">IPPO = {PLI:.2f}<br>
                Cuando IPPO > 1.5 ocurren las infestaciones</p>
            </div>
        """, unsafe_allow_html=True)

        # Assuming latest values are available
        temperature = latest['temp']  # Example: 25°C
        humidity = latest['hum']  # Example: 60%
        pressure = latest['pres']  # Example: 1013

        # Random coefficients for demonstration
        a = 0.4
        b = 0.3
        c = 0.2
        d = 1.0

        # Calculate Moth Activity Score
        moth_activity_score = a * temperature + b * humidity + c * pressure + d

        # New block for Moth Activity Score Calculation


else:
    st.error("No data available")
