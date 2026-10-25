"""Doğrulanmış ham yanıtlardan altı deney şekli üretir (PNG ve SVG)."""
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from analyze_final import OUT, collect_summary, main as analyze

FIGURES = OUT / 'figures'
NAMES = ['A: Prompt only', 'B: JSON Schema', 'C: Optimized schema']
COLORS = ['#4878b5', '#df9840', '#37946e']


def save(fig, name):
    fig.tight_layout()
    for suffix in ('png', 'svg'):
        fig.savefig(FIGURES / f'{name}.{suffix}', dpi=180)
    plt.close(fig)


def label_bars(ax, bars, unit=''):
    ax.bar_label(bars, labels=[f'{b.get_height():.2f}{unit}' for b in bars], padding=4, fontsize=9)


def main():
    summary, matrices = collect_summary()
    assert summary['status'] == 'complete', 'Three completed experiments are required for figures.'
    analyze()
    assert json.loads((OUT / 'metrics_summary.json').read_text()) == summary
    FIGURES.mkdir(exist_ok=True)
    plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 10, 'axes.spines.top': False, 'axes.spines.right': False})
    metrics = [summary['experiments'][key]['final_metrics'] for key in 'ABC']
    n = summary['dataset']['evaluation_records']
    x = np.arange(3)

    fig, ax = plt.subplots(figsize=(10, 5))
    for i, (field, label) in enumerate([('raw_json_success_pct', 'Raw JSON'), ('clean_json_success_pct', 'Clean JSON'), ('schema_success_pct', 'Schema valid')]):
        bars = ax.bar(x + (i-1)*.25, [m[field] for m in metrics], .25, label=label)
        label_bars(ax, bars, '%')
    ax.set(xticks=x, xticklabels=NAMES, ylim=(0, 120), ylabel=f'Success (%) / {n} requests', title='JSON parsing and schema validity')
    ax.legend(loc='upper left', ncol=3)
    save(fig, 'json_success_comparison')

    fig, ax = plt.subplots(figsize=(10, 5))
    for i, (field, label) in enumerate([('end_to_end_accuracy_pct', 'End-to-end / 200'), ('conditional_accuracy_pct', 'Conditional / schema-valid')]):
        bars = ax.bar(x + (i-.5)*.35, [m[field] for m in metrics], .35, label=label)
        label_bars(ax, bars, '%')
    labels = [f'{name}\nCorrect: {m["category_correct_count"]}/{n}; valid: {m["schema_success_count"]}' for name,m in zip(NAMES,metrics)]
    ax.set(xticks=x, xticklabels=labels, ylim=(0, 100), ylabel='Classification accuracy (%)', title='Classification: distinct denominators')
    ax.legend()
    save(fig, 'classification_accuracy')

    fig, axes = plt.subplots(1, 2, figsize=(11, 5))
    for ax, field, title in zip(axes, ['total_inference_seconds', 'mean_inference_seconds'], [f'Total runtime ({n} samples)', 'Mean runtime per sample']):
        values = [m[field] for m in metrics]
        bars = ax.bar(list('ABC'), values, color=COLORS)
        label_bars(ax, bars, ' s')
        ax.set(ylabel='Seconds', title=title, ylim=(0, max(values)*1.2))
    fig.suptitle('Recorded client-side inference time (includes parsing)')
    save(fig, 'inference_performance')

    matrix = matrices['C']
    categories = sorted(matrix)
    columns = categories + ['INVALID']
    values = np.array([[matrix[c][p] for p in columns] for c in categories])
    fig, ax = plt.subplots(figsize=(10, 7))
    im = ax.imshow(values, cmap='Blues', vmin=0)
    ax.set(xticks=range(8), xticklabels=columns, yticks=range(7), yticklabels=categories,
           xlabel='Predicted category', ylabel='Reference category', title=f'Experiment C confusion matrix (N = {n})')
    plt.setp(ax.get_xticklabels(), rotation=30, ha='right')
    for i in range(7):
        for j in range(8):
            ax.text(j, i, str(values[i,j]), ha='center', va='center', color='white' if values[i,j] > values.max()/2 else 'black')
    fig.colorbar(im, ax=ax)
    save(fig, 'confusion_matrix')

    fig, ax = plt.subplots(figsize=(10, 5))
    per_category = metrics[2]['per_category']
    bars = ax.bar(categories, [per_category[c]['accuracy_pct'] for c in categories], color=COLORS[2])
    ax.bar_label(bars, labels=[f'{per_category[c]["correct"]}/{per_category[c]["total"]}\n{per_category[c]["accuracy_pct"]:.2f}%' for c in categories], padding=4)
    overall = metrics[2]['end_to_end_accuracy_pct']
    ax.axhline(overall, linestyle='--', color='#333333', label=f'Overall: {overall:.2f}%')
    ax.set(ylim=(0, 115), ylabel='End-to-end accuracy (%)', title=f'Experiment C per-category accuracy (N = {n})')
    ax.legend(loc='upper left')
    save(fig, 'category_accuracy')

    failures = summary['experiments']['B']['failure_breakdown']
    counts = [metrics[1]['schema_success_count'], failures['schema_invalid_with_length_stop'], failures['schema_invalid_other_or_unrecorded_stop']]
    assert sum(counts) == n
    fig, ax = plt.subplots(figsize=(10, 5))
    bars = ax.bar(['Schema valid', 'Schema invalid\nlength stop', 'Schema invalid\nother / unrecorded stop'], counts, color=['#37946e', '#bc4c4c', '#df9840'])
    ax.bar_label(bars, labels=[f'{c}/{n} ({100*c/n:.2f}%)' for c in counts], padding=5)
    ax.set(ylim=(0, n*1.05), ylabel='Number of samples', title=f'Experiment B outcome and failure breakdown (N = {n})')
    save(fig, 'schema_failure_analysis')
    print('Generated all six figures in PNG and SVG.')


if __name__ == '__main__':
    main()
