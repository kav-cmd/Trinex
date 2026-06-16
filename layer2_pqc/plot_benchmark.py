"""
plot_benchmark.py

Generates a comparison chart: ML-DSA vs Classical Cryptography.
Reads benchmark_table.csv and produces benchmark_graph.png.
"""

import matplotlib.pyplot as plt
import pandas as pd
import os

base = os.path.dirname(os.path.abspath(__file__))
results_dir = os.path.join(base, 'results')

# Load benchmark data
df_bench = pd.read_csv(os.path.join(results_dir, 'benchmark_table.csv'))

fig, axes = plt.subplots(1, 3, figsize=(15, 5))
fig.suptitle(
    'ML-DSA (Dilithium) vs Classical Cryptography',
    fontsize=14, fontweight='bold')

algorithms = df_bench['Algorithm'].tolist()

# Dynamically assign colors: Green for Quantum Safe, Orange/Red for Classical
colors = []
for _, row in df_bench.iterrows():
    if row['Quantum Safe'] == 'Yes':
        colors.append('green')
    elif row['Algorithm'] == 'ECDSA-256':
        colors.append('orange')
    else:
        colors.append('red')

# Graph 1 — Signing time
axes[0].bar(algorithms, df_bench['Sign (ms)'], color=colors)
axes[0].set_title('Signing Time (ms)')
axes[0].set_ylabel('milliseconds')
axes[0].tick_params(axis='x', rotation=20)
axes[0].axhline(y=1.0, color='gray', linestyle='--', label='1ms line')

# Graph 2 — Signature size
axes[1].bar(algorithms, df_bench['Signature (bytes)'], color=colors)
axes[1].set_title('Signature Size (bytes)')
axes[1].set_ylabel('bytes')
axes[1].tick_params(axis='x', rotation=20)

# Graph 3 — Verify time
axes[2].bar(algorithms, df_bench['Verify (ms)'], color=colors)
axes[2].set_title('Verification Time (ms)')
axes[2].set_ylabel('milliseconds')
axes[2].tick_params(axis='x', rotation=20)

plt.tight_layout()

plt.savefig(
    os.path.join(results_dir, 'benchmark_graph.png'),
    dpi=150,
    bbox_inches='tight')

plt.show()
print("Graph plotted and saved!")
