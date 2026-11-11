"""Render the five source-grounded example layouts as PNG, SVG and PDF."""
import json
import textwrap
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

from sector_economy import DATA, DEFAULTS

ROOT = Path(__file__).resolve().parent
EXAMPLES = [('employment', 2022, 'Employment by broad sector'),
            ('comparison', 2022, 'GVA and employment shares by broad sector'),
            ('sector', 2022, 'Gross value added per employed person by sector'),
            ('economy', 2022, 'Gross value added per employed person by economy'),
            ('exports', 2024, 'Goods exports by manufacturing technology group')]


def build():
    data = json.loads((DATA / 'sector_economy_explorer.json').read_text('utf-8'))
    names = {c['iso']: c['display'] for c in data['countries']}
    plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 11, 'axes.spines.top': False, 'axes.spines.right': False,
                         'axes.spines.left': False, 'axes.spines.bottom': False, 'svg.fonttype': 'none'})
    for kind, year, title in EXAMPLES:
        series = 'exports' if kind == 'exports' else 'employment' if kind == 'employment' else 'productivity'
        rows = [next(r[series] for r in data['rows'] if r['iso'] == iso and r['year'] == year) for iso in DEFAULTS]
        assert all(r['status'] == 'available' for r in rows), (kind, rows)
        groups = data['exportGroups'] if kind == 'exports' else data['groups']
        colors = [g['color'] for g in groups]
        if kind in ['sector', 'economy']:
            fig, axes = plt.subplots(2, 3, figsize=(17, 10.5))
            for j, ax in enumerate(axes.flat):
                values = [r['amounts'][j] for r in rows] if kind == 'sector' else rows[j]['amounts']
                labels = [names[iso].replace(' ', '\n') for iso in DEFAULTS] if kind == 'sector' else [g['id'] for g in groups]
                bars = ax.bar(range(6), values, color=colors[j] if kind == 'sector' else colors, width=.7)
                ax.bar_label(bars, fmt='%.0f', padding=4, fontsize=10)
                reference = float(np.median(values)) if kind == 'sector' else rows[j]['total']
                ax.axhline(reference, color='#b54831', linestyle='--', linewidth=1.5)
                ax.text(0, -.25, ('Selected-economy median: ' if kind == 'sector' else 'Economy total GVA/person: ') + f'{reference:.1f}', transform=ax.transAxes, color='#a13a24', fontsize=10)
                ax.set_title(groups[j]['label'] if kind == 'sector' else names[DEFAULTS[j]], fontsize=12, fontweight='bold')
                ax.set_xticks(range(6), labels, fontsize=10)
                ax.set_ylim(0, max(values) * 1.2)
                ax.grid(axis='y', color='#e4e9ec'); ax.set_axisbelow(True)
            fig.subplots_adjust(left=.055, right=.98, top=.86, bottom=.27 if kind == 'economy' else .23, hspace=.65, wspace=.2)
            fig.text(.055, .91, f'{year} · Current US$ thousand per employed person · panels have individual scales', color='#526777')
            if kind == 'economy':
                fig.text(.055, .135, '\n'.join('   |   '.join(g['id'] + ': ' + g['label'] for g in groups[k:k+3]) for k in [0, 3]), fontsize=10, linespacing=1.8)
        else:
            fig, ax = plt.subplots(figsize=(15, 8.5))
            x = np.arange(6)
            series_ = ['gvaShares', 'employmentShares'] if kind == 'comparison' else ['shares']
            for k, field in enumerate(series_):
                positions = x + ((k - .5) * .37 if kind == 'comparison' else 0)
                width = .34 if kind == 'comparison' else .72
                bottom = np.zeros(6)
                for j, group in enumerate(groups):
                    values = np.array([r[field][j] for r in rows])
                    ax.bar(positions, values, bottom=bottom, width=width, color=group['color'], label=group['label'] if k == 0 else None)
                    for p, v, b in zip(positions, values, bottom):
                        if v >= 3.2:
                            ax.text(p, b + v / 2, f'{v:.0f}%', ha='center', va='center', color='white', fontsize=10)
                    bottom += values
                for i, r in enumerate(rows):
                    total = (f"${r['totalGVA']/1e9:,.0f}bn" if k == 0 else f"{r['totalPersons']/1e6:,.2f}m") if kind == 'comparison' else f"{r['total']/1e6:,.2f} million" if kind == 'employment' else f"US$ {r['total']/1e9:,.1f}bn"
                    if kind == 'comparison':
                        total = total.replace('bn', '\nbillion').replace('m', '\nmillion')
                    ax.text(positions[i], 103, total, ha='center', va='bottom', fontsize=9)
                if kind == 'comparison':
                    for p in positions:
                        ax.text(p, -4, 'GVA' if k == 0 else 'Emp.', ha='center', fontsize=9)
            ax.set_xticks(x, [names[iso].replace(' ', '\n') for iso in DEFAULTS])
            ax.tick_params(axis='x', pad=25 if kind == 'comparison' else 10)
            ax.set_ylim(0, 111); ax.set_yticks(range(0, 101, 20), [str(v) + '%' for v in range(0, 101, 20)])
            ax.grid(axis='y', color='#e4e9ec'); ax.set_axisbelow(True)
            handles, labels = ax.get_legend_handles_labels()
            ax.legend(handles[::-1], ['\n'.join(textwrap.wrap(s, 27)) for s in labels[::-1]], bbox_to_anchor=(1.01, .95), loc='upper left', frameon=False, labelspacing=1.5, fontsize=10)
            fig.subplots_adjust(left=.055, right=.77, top=.82, bottom=.22)
            fig.text(.055, .89, f'{year} · Shares of ' + ('reported goods exports' if kind == 'exports' else 'six-sector totals') + ' · totals above stacks', color='#526777')
        fig.suptitle(title, x=.055, y=.97, ha='left', fontsize=20, fontweight='bold')
        fig.text(.055, .09, 'Handy Satria · Sources: OECD TiM 2025 / TiVA 2025 / BTiGE; Eustat; WDI exchange rates.', fontsize=10, color='#526777')
        note = 'Goods only; custom manufacturing groups. Other/unallocated = total minus both groups. C33 services outside BTiGE goods scope.' if kind == 'exports' else 'Same-year joins; A–T sector coverage; employed persons, not FTEs. Nominal productivity is not PPP-adjusted or per hour.'
        fig.text(.055, .06, note, fontsize=10, color='#526777')
        fig.text(.055, .03, ('Sector medians: unweighted across the six selected economies. ' if kind == 'sector' else '') + 'Basque Country is a region within Spain. Source values and rounding are retained in the downloads.', fontsize=10, color='#526777')
        for ext in ['png', 'svg', 'pdf']:
            path = ROOT / 'output' / f'sector_{kind}_{year}.{ext}'
            fig.savefig(path, dpi=180, facecolor='white')
        plt.close(fig)
    print('Rendered all five examples in PNG, SVG and PDF.')


if __name__ == '__main__':
    build()
