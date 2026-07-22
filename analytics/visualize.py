import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import os
from sklearn.linear_model import LinearRegression
from sklearn.metrics import r2_score

def setup_academic_style():
    """Apply standard academic formatting to matplotlib/seaborn."""
    sns.set_theme(style="whitegrid")
    sns.set_palette("deep")
    plt.rcParams.update({
        'font.family': 'serif',
        'font.serif': ['Times New Roman'],
        'axes.labelsize': 12,
        'axes.titlesize': 14,
        'xtick.labelsize': 10,
        'ytick.labelsize': 10,
        'legend.fontsize': 10,
        'figure.dpi': 300,
        'savefig.bbox': 'tight'
    })

def plot_staircase_quantization(csv_path, out_path):
    """
    Figure 1: Relationship between memory allocation and telemetry feedback.
    Shows the staircase quantization and linear regression.
    """
    if not os.path.exists(csv_path):
        print(f"[-] {csv_path} not found. Skipping Figure 1.")
        return
        
    df = pd.read_csv(csv_path)
    if len(df) == 0:
        return

    # Calculate exact MB allocated by the payload: (val + 1) * 1900000 bytes
    df['allocated_mb'] = (df['val'] + 1) * 1900000 / (1024 * 1024)
    df['memory_cost_mb'] = df['memory_cost_raw'] / (1024 * 1024)
    
    # Calculate means for each val for the regression line
    means = df.groupby('allocated_mb')['memory_cost_mb'].mean().reset_index()
    X = means[['allocated_mb']]
    y = means['memory_cost_mb']
    
    model = LinearRegression()
    model.fit(X, y)
    y_pred = model.predict(X)
    r2 = r2_score(y, y_pred)
    
    fig, ax = plt.subplots(figsize=(8, 6))
    
    # Scatter plot of raw data points (showing variance)
    sns.scatterplot(
        data=df, 
        x='allocated_mb', 
        y='memory_cost_mb', 
        alpha=0.5, 
        color='blue', 
        label='Telemetry Data',
        ax=ax
    )
    
    # Regression line
    ax.plot(
        X['allocated_mb'], 
        y_pred, 
        color='red', 
        linestyle='--', 
        label=f'Linear Fit ($R^2={r2:.4f}$)\n$y = {model.coef_[0]:.2f}x + {model.intercept_:.2f}$'
    )
    
    ax.set_title("Memory Allocation vs. Telemetry Feedback (No Defense)")
    ax.set_xlabel("Memory Allocated in Sandbox (MB)")
    ax.set_ylabel("Reported memory_cost (MB)")
    ax.legend(loc='upper left')
    
    plt.savefig(out_path, format='pdf')
    plt.close()
    print(f"[+] Saved Figure 1 to {out_path}")

def plot_rate_ber_tradeoff(csv_path, out_path):
    """
    Figure 2: Rate vs BER Trade-off Plot using a dual Y-axis.
    """
    if not os.path.exists(csv_path):
        print(f"[-] {csv_path} not found. Skipping Figure 2.")
        return
        
    df = pd.read_csv(csv_path)
    if len(df) == 0:
        return
        
    # Aggregate if there are multiple runs per delay
    df_agg = df.groupby('delay_sec').agg({
        'throughput_bps': 'mean',
        'ber_percent': 'mean'
    }).reset_index()
    
    fig, ax1 = plt.subplots(figsize=(8, 6))
    
    color = 'tab:blue'
    ax1.set_xlabel('Network Delay per Request (Seconds)')
    ax1.set_ylabel('Throughput (Bytes/sec)', color=color)
    ax1.plot(df_agg['delay_sec'], df_agg['throughput_bps'], marker='o', color=color, linewidth=2, label='Throughput')
    ax1.tick_params(axis='y', labelcolor=color)
    
    ax2 = ax1.twinx()
    color = 'tab:red'
    ax2.set_ylabel('Bit Error Rate (BER %)', color=color)
    ax2.plot(df_agg['delay_sec'], df_agg['ber_percent'], marker='s', color=color, linewidth=2, linestyle='--', label='BER')
    ax2.tick_params(axis='y', labelcolor=color)
    
    # Optional: Fill area under BER if it exceeds a threshold to show danger zone
    ax2.axhline(y=10, color='gray', linestyle=':', alpha=0.5)
    ax2.text(max(df_agg['delay_sec'])*0.8, 12, '10% BER Threshold', color='gray')

    fig.suptitle('Channel Capacity vs. Reliability Trade-off')
    
    # Gather legends from both axes
    lines_1, labels_1 = ax1.get_legend_handles_labels()
    lines_2, labels_2 = ax2.get_legend_handles_labels()
    ax1.legend(lines_1 + lines_2, labels_1 + labels_2, loc='upper right')
    
    fig.tight_layout()
    plt.savefig(out_path, format='pdf')
    plt.close()
    print(f"[+] Saved Figure 2 to {out_path}")

def plot_mitigation_comparison(csv_path, out_path):
    """
    Figure 3: Violin plot comparing residuals/variance across defense modes.
    """
    if not os.path.exists(csv_path):
        print(f"[-] {csv_path} not found. Skipping Figure 3.")
        return
        
    df = pd.read_csv(csv_path)
    if len(df) == 0:
        return
        
    # We want to show how "noisy" or "quantized" the telemetry is compared to the ideal fit.
    # To do this, we compute the residual = (reported_mem - expected_mem) / 1MB
    
    # First, find the expected ideal mapping from the 'raw' (no defense) data
    df['allocated_mb'] = (df['val'] + 1) * 1900000 / (1024 * 1024)
    raw_means = df.groupby('allocated_mb')['memory_cost_raw'].mean().reset_index()
    X = raw_means[['allocated_mb']]
    y = raw_means['memory_cost_raw']
    model = LinearRegression()
    model.fit(X, y)
    
    df['expected_raw'] = model.predict(df[['allocated_mb']])
    
    # Melt the dataframe so we have a 'Mode' column and a 'Reported Memory' column
    df_melt = pd.melt(df, 
                      id_vars=['val', 'allocated_mb', 'expected_raw'], 
                      value_vars=['memory_cost_raw', 'memory_cost_quantized', 'memory_cost_noisy'],
                      var_name='Defense Mode', 
                      value_name='Reported Memory')
    
    # Clean up names
    mode_map = {
        'memory_cost_raw': 'No Defense\n(Baseline)',
        'memory_cost_quantized': 'Coarse-Grained\n(16MB Quantization)',
        'memory_cost_noisy': 'Diff. Privacy\n(Gaussian Noise)'
    }
    df_melt['Defense Mode'] = df_melt['Defense Mode'].map(mode_map)
    
    # Calculate Residuals in MB
    df_melt['Residual (MB)'] = (df_melt['Reported Memory'] - df_melt['expected_raw']) / (1024 * 1024)
    
    fig, ax = plt.subplots(figsize=(9, 6))
    
    sns.violinplot(
        data=df_melt, 
        x='Defense Mode', 
        y='Residual (MB)', 
        palette='muted',
        inner='quartile',
        ax=ax
    )
    
    ax.axhline(0, color='black', linestyle='-', alpha=0.3)
    ax.set_title("Impact of Defense Mechanisms on Telemetry Resolution")
    ax.set_ylabel("Telemetry Residual Error (MB)")
    ax.set_xlabel("System Configuration")
    
    plt.savefig(out_path, format='pdf')
    plt.close()
    print(f"[+] Saved Figure 3 to {out_path}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Generate JudgeSCA Academic Charts")
    args = parser.parse_args()
    
    setup_academic_style()
    
    base_dir = os.path.dirname(__file__)
    data_dir = os.path.join(base_dir, 'data')
    
    os.makedirs(data_dir, exist_ok=True)
    
    calib_csv = os.path.join(data_dir, 'calibration_data.csv')
    tp_csv = os.path.join(data_dir, 'throughput_data.csv')
    
    plot_staircase_quantization(calib_csv, os.path.join(base_dir, 'figure1_staircase.pdf'))
    plot_rate_ber_tradeoff(tp_csv, os.path.join(base_dir, 'figure2_tradeoff.pdf'))
    plot_mitigation_comparison(calib_csv, os.path.join(base_dir, 'figure3_mitigation.pdf'))
