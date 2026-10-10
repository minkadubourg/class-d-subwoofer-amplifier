"""Signal-chain block diagram (figures/signal_chain.png)."""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

INK, MUTED, FILL, ACC = "#1f1f1e", "#6b6a64", "#eef4fc", "#2a78d6"
blocks = [("Line-level\naudio", "±1.23 V"), ("Level shifter", "→ 0–3 V"),
          ("STM32L475\nADC + PWM", "200 kHz, AD mode"), ("Gate drive", "4 signals"),
          ("Full H-bridge", "4 × NTPF082N65S3F\n100 V rail"), ("LC filter", "2nd order"),
          ("Subwoofer", "1.7 kW")]
fig, ax = plt.subplots(figsize=(12, 2.0)); ax.set_xlim(0, 12); ax.set_ylim(0, 2); ax.axis("off")
w, gap = 1.45, 0.25
for i, (name, sub) in enumerate(blocks):
    x = 0.1 + i * (w + gap)
    ax.add_patch(FancyBboxPatch((x, 0.55), w, 0.95, boxstyle="round,pad=0.02,rounding_size=0.08",
                                fc=FILL, ec=ACC if i in (2, 4) else MUTED, lw=1.6 if i in (2, 4) else 1))
    ax.text(x + w / 2, 1.12, name, ha="center", va="center", fontsize=9.5, color=INK, weight="bold")
    ax.text(x + w / 2, 0.3, sub, ha="center", va="center", fontsize=8, color=MUTED)
    if i < len(blocks) - 1:
        ax.annotate("", xy=(x + w + gap - 0.02, 1.02), xytext=(x + w + 0.02, 1.02),
                    arrowprops=dict(arrowstyle="-|>", color=MUTED, lw=1.2))
fig.savefig(os.path.join(os.path.dirname(__file__), "..", "figures", "signal_chain.png"), dpi=170, bbox_inches="tight")
