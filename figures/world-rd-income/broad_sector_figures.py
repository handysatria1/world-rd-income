"""Render a reproducible six-economy example with the chart maker's exact input rows."""
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Patch

ROOT = Path(__file__).resolve().parent


def main():
    data = json.loads((ROOT / 'data/broad_sector_explorer.json').read_text('utf-8'))
    countries = {c['iso']: c for c in data['countries']}
    rows = [max((r for r in data['rows'] if r['iso'] == iso and r['status'] == 'available'), key=lambda r: r['year']) for iso in data['defaults']]
    fig, ax = plt.subplots(figsize=(12.4, 6.4))
    fig.subplots_adjust(left=.07, right=.73, bottom=.24, top=.78)
    for i, row in enumerate(rows):
        bottom = 0
        for j, group in enumerate(data['groups']):
            value = row['shares'][j]
            ax.bar(i, value, bottom=bottom, color=group['color'], width=.94)
            if value >= 2:
                ax.text(i, bottom + value / 2, f'{value:.0f}%', ha='center', va='center', fontsize=9, color='white' if j != 5 else '#222222')
            bottom += value
        if row['totalUSD'] is not None:
            label = f"US$ {row['totalUSD'] / 1e9:,.0f}\nbillion"
        else:
            label = f"{row['currency']} {row['totalLocal'] / 1e9:,.1f}bn\nUSD conversion missing"
        ax.text(i, 101, label, ha='center', va='bottom', fontsize=10)
    ax.set_xlim(-.55, len(rows)-.45)
    ax.set_ylim(0, 100)
    ax.set_xticks(range(len(rows)), [countries[r['iso']]['display'] + '\n' + str(r['year']) + (' (p)' if r['note'] else '') + '\n' + ('Eustat · region' if r['iso'] == 'ES-PV' else 'OECD TiVA') for r in rows], fontsize=9)
    ax.set_ylabel('Share of grouped GVA (%)')
    ax.spines[['top', 'right']].set_visible(False)
    ax.spines[['bottom', 'left']].set_color('#c0cdd5')
    ax.tick_params(axis='x', length=0)
    handles = [Patch(color=g['color'], label=g['label'].replace(' manufacturing', '\nmanufacturing').replace(' services', '\nservices')) for g in reversed(data['groups'])]
    ax.legend(handles=handles, loc='upper left', bbox_to_anchor=(1.01, 1), frameon=False, labelspacing=1.3)
    fig.text(.07, .96, 'Gross value added by broad sector', fontsize=17, fontweight='bold', va='top')
    fig.text(.07, .91, 'Latest available complete year in the selected sources', fontsize=11, color='#526777')
    fig.text(.07, .1, 'Handy Satria · OECD TiVA 2025; Eustat A38; WDI annual exchange rates. (p) Provisional.', fontsize=9)
    fig.text(.07, .065, 'User-supplied six-sector grouping; sections A–T. GVA at basic prices, excluding net product taxes and section U.', fontsize=9)
    for extension in ['png', 'svg', 'pdf']:
        fig.savefig(ROOT / 'output' / ('broad_sector_gva_latest.' + extension), dpi=220, facecolor='white')
    plt.close(fig)


if __name__ == '__main__':
    main()
