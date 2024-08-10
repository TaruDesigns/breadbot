import os
from datetime import datetime

import matplotlib.pyplot as plt
import seaborn as sns

from db import models


def plot_roundness_by_user(user_id: int) -> str:
    # Data: list of tuples with (X, Y) values
    data = models.get_roundness_history(user_id)
    x_values, y_values = zip(*data)
    # Scale Y values to percentages
    y_values_percent = [y * 100 for y in y_values]

    sns.set(style="darkgrid", context="talk")
    plt.figure(figsize=(12, 7))
    sns.lineplot(x=x_values, y=y_values_percent, marker="o", color="teal", linewidth=2.5, linestyle="--")
    sns.scatterplot(x=x_values, y=y_values_percent, color="orange", s=100, zorder=5)

    # Set the plot labels and title
    plt.xlabel("X", fontsize=14, fontweight="bold")
    plt.ylabel("Y (%)", fontsize=14, fontweight="bold")
    plt.title("Amazing roundness history for User", fontsize=18, fontweight="bold")

    # Save the plot as a PNG image
    outputfolder = os.path.join(os.getcwd(), "output", "plots")
    os.makedirs(outputfolder, exist_ok=True)

    filename = f"{user_id}_roundhistory.png"
    output_img_path = os.path.join(outputfolder, filename)
    plt.savefig(output_img_path, dpi=300, bbox_inches="tight")
    return output_img_path


if __name__ == "__main__":
    path = plot_roundness_by_user(95618667529637888)
    print(path)
