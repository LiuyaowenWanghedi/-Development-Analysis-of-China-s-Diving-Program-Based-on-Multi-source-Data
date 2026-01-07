import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats
import pymysql
import warnings
import re
from matplotlib.patches import Patch
from matplotlib.lines import Line2D

warnings.filterwarnings('ignore')

# 设置样式
plt.rcParams['font.sans-serif'] = ['Arial', 'DejaVu Sans', 'Helvetica']
plt.rcParams['axes.unicode_minus'] = False
sns.set_style("whitegrid")
plt.rcParams['figure.figsize'] = (14, 8)
plt.rcParams['savefig.dpi'] = 300
plt.rcParams['font.size'] = 10

# 数据库配置
DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "root123456",
    "database": "OlympicDiving",
    "charset": "utf8mb4"
}


def fetch_all_data():
    """提取所有运动员排名数据"""
    try:
        connection = pymysql.connect(**DB_CONFIG)

        tables = [
            '2000_Sydney_Women10m_FINAL_Athlete_Rankings',
            '2000_Sydney_Women10m_SEMIFINAL_Athlete_Rankings',
            '2004_Athens_Women10m_FINAL_Athlete_Rankings',
            '2004_Athens_Women10m_SEMIFINAL_Athlete_Rankings',
            '2008_Beijing_Women10m_FINAL_Athlete_Rankings',
            '2008_Beijing_Women10m_SEMIFINAL_Athlete_Rankings',
            '2012_London_Women10m_FINAL_Athlete_Rankings',
            '2012_London_Women10m_SEMIFINAL_Athlete_Rankings',
            '2016_Rio_Women10m_FINAL_Athlete_Rankings',
            '2016_Rio_Women10m_SEMIFINAL_Athlete_Rankings',
            '2020_Tokyo_Women10m_FINAL_Athlete_Rankings',
            '2020_Tokyo_Women10m_SEMIFINAL_Athlete_Rankings',
            '2024_Paris_Women10m_FINAL_Athlete_Rankings',
            '2024_Paris_Women10m_SEMIFINAL_Athlete_Rankings'
        ]

        all_data = []

        for table in tables:
            try:
                query = f"SELECT * FROM `{table}`"
                df = pd.read_sql(query, connection)

                df = df.rename(columns={
                    'Athlete': 'athlete_name',
                    'Age': 'age',
                    'Country': 'country',
                    'Total_Points': 'total_points',
                    'Rank': 'rank',
                    'Competition_Phase': 'phase',
                    'Olympic_Games': 'olympic_games'
                })

                needed_cols = ['athlete_name', 'age', 'country', 'total_points', 'rank', 'phase', 'olympic_games']
                df = df[needed_cols]

                all_data.append(df)

            except Exception:
                continue

        connection.close()

        if all_data:
            combined_df = pd.concat(all_data, ignore_index=True)

            def clean_total_points(x):
                if pd.isna(x):
                    return np.nan
                try:
                    x_str = str(x).replace('Qualified', '').strip()
                    match = re.search(r'[\d\.]+', x_str)
                    if match:
                        return float(match.group())
                except:
                    pass
                return np.nan

            combined_df['total_points'] = combined_df['total_points'].apply(clean_total_points)
            combined_df['age'] = pd.to_numeric(combined_df['age'], errors='coerce')
            combined_df['rank'] = pd.to_numeric(combined_df['rank'], errors='coerce')

            combined_df['year'] = combined_df['olympic_games'].str.extract(r'(\d{4})').astype(int)
            combined_df = combined_df.drop_duplicates(subset=['athlete_name', 'year', 'phase'])

            return combined_df
        else:
            return None

    except Exception as e:
        print(f"Database error: {e}")
        return None


def plot_first_competition_analysis(df):
    """图1：首次参赛年龄分析"""
    print("生成图表1：首次参赛年龄分析...")

    first_comp = df.sort_values(['athlete_name', 'year']).groupby('athlete_name').first().reset_index()
    first_comp = first_comp[['athlete_name', 'age', 'country', 'year']]

    # 计算各国平均年龄
    country_stats = first_comp.groupby('country')['age'].agg(['mean', 'count']).reset_index()
    country_stats = country_stats[country_stats['count'] >= 3]
    country_stats = country_stats.sort_values('mean')

    # 识别中国选手
    first_comp['is_china'] = first_comp['country'] == 'CHN'

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 7))

    # 左图：年龄分布
    overall_data = first_comp['age'].dropna()

    # 绘制直方图
    n, bins, patches = ax1.hist(overall_data, bins=12, color='lightblue',
                                alpha=0.7, edgecolor='black', density=False)

    # 中国选手分布
    china_data = first_comp[first_comp['is_china']]
    if not china_data.empty:
        ax1.hist(china_data['age'], bins=bins, color='red', alpha=0.6,
                 edgecolor='darkred', density=False, label='Chinese athletes')

    # 添加均值和中位数线
    mean_age = overall_data.mean()
    median_age = overall_data.median()
    ax1.axvline(mean_age, color='green', linestyle='-', linewidth=2,
                alpha=0.8, label=f'Mean: {mean_age:.1f}')
    ax1.axvline(median_age, color='orange', linestyle='--', linewidth=2,
                alpha=0.8, label=f'Median: {median_age:.1f}')

    ax1.set_title('A: First Competition Age Distribution',
                  fontsize=13, fontweight='bold', pad=12)
    ax1.set_xlabel('Age (years)', fontsize=11)
    ax1.set_ylabel('Number of Athletes', fontsize=11)
    ax1.legend(loc='upper right', fontsize=9)
    ax1.grid(True, alpha=0.3)

    # 统计信息
    stats_text = f'Total Athletes: {len(first_comp)}\n'
    stats_text += f'Age Range: {overall_data.min():.0f}-{overall_data.max():.0f}\n'
    stats_text += f'Std Dev: {overall_data.std():.1f}'

    if not china_data.empty:
        stats_text += f'\n\nChinese Athletes (n={len(china_data)}):\n'
        stats_text += f'Mean: {china_data["age"].mean():.1f}\n'
        stats_text += f'Range: {china_data["age"].min():.0f}-{china_data["age"].max():.0f}'

    ax1.text(0.02, 0.98, stats_text, transform=ax1.transAxes,
             fontsize=9, verticalalignment='top',
             bbox=dict(boxstyle='round', facecolor='white', alpha=0.9, pad=0.5))

    # 右图：各国平均年龄
    # 为每个国家设置颜色
    colors = ['red' if country == 'CHN' else 'lightgray'
              for country in country_stats['country']]

    y_pos = np.arange(len(country_stats))
    bars = ax2.barh(y_pos, country_stats['mean'],
                    color=colors, edgecolor='black', height=0.7)

    # 添加样本数
    for i, (bar, count) in enumerate(zip(bars, country_stats['count'])):
        ax2.text(bar.get_width() + 0.15, bar.get_y() + bar.get_height() / 2,
                 f'n={count}', va='center', fontsize=9, fontweight='bold')

    ax2.set_yticks(y_pos)
    ax2.set_yticklabels(country_stats['country'], fontsize=10)

    ax2.set_title('B: Mean First Competition Age by Country\n(Minimum 3 Athletes)',
                  fontsize=13, fontweight='bold', pad=12)
    ax2.set_xlabel('Mean Age (years)', fontsize=11)
    ax2.set_ylabel('Country', fontsize=11)
    ax2.grid(True, alpha=0.3, axis='x')

    # 设置x轴范围
    max_mean = country_stats['mean'].max()
    ax2.set_xlim(0, max_mean * 1.15)

    # 图例
    china_patch = Patch(facecolor='red', edgecolor='black', label='China')
    other_patch = Patch(facecolor='lightgray', edgecolor='black', label='Other Countries')
    ax2.legend(handles=[china_patch, other_patch], loc='lower right', fontsize=9)

    plt.suptitle('First Competition Age Analysis', fontsize=15, fontweight='bold', y=0.98)
    plt.tight_layout()
    plt.savefig('1_first_competition_age.png', dpi=300, bbox_inches='tight')
    plt.show()
    plt.close(fig)

    return first_comp


def plot_age_trends_integrated(df):
    """图2：年龄趋势分析"""
    print("生成图表2：年龄趋势分析...")

    final_data = df[df['phase'] == 'FINAL'].copy()

    fig, ax = plt.subplots(figsize=(14, 8))

    # 准备数据
    years = sorted(final_data['year'].unique())
    box_data = []

    for year in years:
        year_data = final_data[final_data['year'] == year]['age'].dropna()
        box_data.append(year_data.values)

    # 箱线图
    box = ax.boxplot(box_data, positions=range(len(years)),
                     patch_artist=True, widths=0.6,
                     medianprops={'color': 'red', 'linewidth': 2},
                     boxprops={'facecolor': 'lightblue', 'alpha': 0.7},
                     whiskerprops={'linewidth': 1.5},
                     capprops={'linewidth': 1.5},
                     showfliers=True)

    # 均值趋势线
    yearly_means = final_data.groupby('year')['age'].mean()
    ax.plot(range(len(years)), yearly_means.values, 's-',
            color='darkblue', linewidth=3, markersize=8,
            markerfacecolor='yellow', markeredgecolor='black',
            label='Mean Age', zorder=5)

    # 标注均值
    for i, (year, mean_val) in enumerate(yearly_means.items()):
        ax.text(i, mean_val + 0.2, f'{mean_val:.1f}',
                ha='center', va='bottom', fontweight='bold', fontsize=9)

    # 回归分析
    if len(years) >= 2:
        slope, intercept, r_value, p_value, std_err = stats.linregress(
            years, yearly_means.values
        )

        # 回归线
        x_fit = np.array([min(years), max(years)])
        y_fit = intercept + slope * x_fit

        # 转换x坐标用于绘图
        x_plot = [years.index(min(years)), years.index(max(years))]
        ax.plot(x_plot, y_fit, 'r--', linewidth=3, alpha=0.8,
                label=f'Regression line', zorder=4)

        # 回归统计
        reg_text = f'Regression Analysis:\n'
        reg_text += f'Slope: {slope:.3f} years/cycle\n'
        reg_text += f'R² = {r_value ** 2:.3f}\n'
        reg_text += f'p = {p_value:.3f}'

        if p_value < 0.05:
            reg_text += ' *\n'
            reg_text += 'Significant trend'
        else:
            reg_text += ' (ns)\nNo significant trend'

        ax.text(0.02, 0.98, reg_text, transform=ax.transAxes,
                fontsize=10, verticalalignment='top',
                bbox=dict(boxstyle='round', facecolor='white', alpha=0.9, pad=0.5))

    # 设置图表属性
    ax.set_xticks(range(len(years)))
    ax.set_xticklabels(years, fontsize=11)
    ax.set_xlabel('Olympic Year', fontsize=12)
    ax.set_ylabel('Age (years)', fontsize=12)
    ax.set_title('Age Trends in Women\'s 10m Platform Final',
                 fontsize=15, fontweight='bold', pad=15)
    ax.legend(loc='upper left', fontsize=10)
    ax.grid(True, alpha=0.3)

    # 总体统计
    overall_stats = f"Overall Statistics:\n"
    overall_stats += f"N = {len(final_data)} athletes\n"
    overall_stats += f"Mean: {final_data['age'].mean():.1f} ± {final_data['age'].std():.1f}\n"
    overall_stats += f"Range: {final_data['age'].min():.0f}-{final_data['age'].max():.0f}"

    ax.text(0.98, 0.02, overall_stats, transform=ax.transAxes,
            fontsize=9, verticalalignment='bottom', horizontalalignment='right',
            bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.8, pad=0.5))

    plt.tight_layout()
    plt.savefig('2_age_trends.png', dpi=300, bbox_inches='tight')
    plt.show()
    plt.close(fig)


def plot_performance_by_age_integrated(df):
    """图3：年龄分组表现分析"""
    print("生成图表3：年龄分组表现分析...")

    final_data = df[df['phase'] == 'FINAL'].copy()

    # 年龄分组
    age_bins = [0, 18, 22, 26, 30, 100]
    age_labels = ['<18', '18-22', '23-26', '27-30', '30+']

    final_data['age_group'] = pd.cut(final_data['age'],
                                     bins=age_bins,
                                     labels=age_labels)

    # 奖牌获得率
    final_data['got_medal'] = final_data['rank'] <= 3
    medal_rate = final_data.groupby('age_group')['got_medal'].mean() * 100

    fig, ax1 = plt.subplots(figsize=(14, 8))

    # 左Y轴：成绩箱线图
    positions = range(len(age_labels))

    # 收集每组数据
    box_data = []
    for group in age_labels:
        group_data = final_data[final_data['age_group'] == group]['total_points'].dropna()
        box_data.append(group_data.values)

    # 绘制箱线图
    box = ax1.boxplot(box_data, positions=positions, widths=0.6,
                      patch_artist=True, showfliers=False,
                      medianprops={'color': 'red', 'linewidth': 2},
                      boxprops={'facecolor': 'lightblue', 'alpha': 0.7})

    # 添加散点
    for i, group in enumerate(age_labels):
        group_data = final_data[final_data['age_group'] == group]['total_points'].dropna()
        if len(group_data) > 0:
            jitter = np.random.normal(0, 0.05, size=len(group_data))
            ax1.scatter(np.ones(len(group_data)) * i + jitter, group_data,
                        alpha=0.4, color='darkblue', s=50, edgecolors='none', zorder=3)

    ax1.set_xlabel('Age Group', fontsize=12)
    ax1.set_ylabel('Total Points', fontsize=12, color='darkblue')
    ax1.tick_params(axis='y', labelcolor='darkblue')
    ax1.set_xticks(positions)
    ax1.set_xticklabels(age_labels, fontsize=11)
    ax1.grid(True, alpha=0.3, axis='y')

    # 标注中位数
    for i, group in enumerate(age_labels):
        median_val = final_data[final_data['age_group'] == group]['total_points'].median()
        ax1.text(i, median_val - 10, f'{median_val:.0f}',
                 ha='center', va='top', fontweight='bold', fontsize=9,
                 bbox=dict(boxstyle='round', facecolor='white', alpha=0.7))

    # 右Y轴：奖牌率折线图
    ax2 = ax1.twinx()
    ax2.plot(positions, medal_rate.values, 'ro-',
             linewidth=3, markersize=8, markerfacecolor='yellow',
             markeredgecolor='red', label='Medal Rate', zorder=4)

    # 标注奖牌率
    for i, rate in enumerate(medal_rate.values):
        ax2.text(i, rate + 2, f'{rate:.1f}%',
                 ha='center', va='bottom', fontweight='bold', fontsize=9,
                 color='red')

    ax2.set_ylabel('Medal Rate (%)', fontsize=12, color='red')
    ax2.tick_params(axis='y', labelcolor='red')
    ax2.set_ylim(0, max(medal_rate.values) * 1.3)

    # 标题
    ax1.set_title('Performance and Medal Rate by Age Group',
                  fontsize=15, fontweight='bold', pad=15)

    # 合并图例
    box_patch = Patch(facecolor='lightblue', alpha=0.7,
                      edgecolor='black', label='Score Distribution')
    scatter_patch = Line2D([0], [0], marker='o', color='w',
                           markerfacecolor='darkblue', markersize=8,
                           label='Individual Scores', alpha=0.4)
    line_patch = Line2D([0], [0], color='red', linewidth=3,
                        marker='o', markerfacecolor='yellow',
                        markeredgecolor='red', label='Medal Rate')

    ax1.legend(handles=[box_patch, scatter_patch, line_patch],
               loc='upper right', fontsize=10)

    # 统计信息
    stats_text = "Statistics by Age Group:\n"
    for i, group in enumerate(age_labels):
        group_data = final_data[final_data['age_group'] == group]
        n = len(group_data)
        if n > 0:
            mean_score = group_data['total_points'].mean()
            medal_count = group_data['got_medal'].sum()
            stats_text += f"{group}: N={n}, Mean={mean_score:.0f}, Medals={medal_count}\n"

    # ANOVA分析
    groups_data = []
    for group in age_labels:
        group_scores = final_data[final_data['age_group'] == group]['total_points'].dropna()
        if len(group_scores) > 0:
            groups_data.append(group_scores)

    if len(groups_data) >= 2:
        f_stat, p_value = stats.f_oneway(*groups_data)
        stats_text += f"\nANOVA: F={f_stat:.2f}, p={p_value:.3f}"
        if p_value < 0.05:
            stats_text += " *\nSignificant difference"
        else:
            stats_text += " (ns)\nNo significant difference"

    ax1.text(0.02, 0.02, stats_text, transform=ax1.transAxes,
             fontsize=9, verticalalignment='bottom',
             bbox=dict(boxstyle='round', facecolor='white', alpha=0.9, pad=0.5))

    plt.tight_layout()
    plt.savefig('3_performance_by_age.png', dpi=300, bbox_inches='tight')
    plt.show()
    plt.close(fig)


def plot_correlation_integrated(df):
    """图4：年龄-成绩相关性"""
    print("生成图表4：年龄-成绩相关性...")

    final_data = df[df['phase'] == 'FINAL'].copy()
    clean_data = final_data.dropna(subset=['age', 'total_points'])

    # 主要国家
    country_counts = clean_data['country'].value_counts()
    major_countries = country_counts[country_counts >= 3].index.tolist()

    fig, ax = plt.subplots(figsize=(14, 8))

    # 颜色映射
    if major_countries:
        color_palette = plt.cm.tab20(np.linspace(0, 1, len(major_countries)))
        color_map = {}
        for i, country in enumerate(major_countries):
            color_map[country] = color_palette[i]

        # 其他国家
        other_countries = [c for c in clean_data['country'].unique() if c not in major_countries]
        for country in other_countries:
            color_map[country] = 'lightgray'

        # 绘制散点
        for country in clean_data['country'].unique():
            country_data = clean_data[clean_data['country'] == country]
            if len(country_data) > 0:
                label = country if country in major_countries else None
                alpha = 0.8 if country in major_countries else 0.4
                s = 60 if country in major_countries else 40

                ax.scatter(country_data['age'], country_data['total_points'],
                           color=color_map[country], alpha=alpha, s=s,
                           edgecolors='black' if country in major_countries else 'none',
                           label=label, zorder=5 if country in major_countries else 3)
    else:
        # 如果样本不足，绘制所有点
        ax.scatter(clean_data['age'], clean_data['total_points'],
                   color='blue', alpha=0.6, s=50, edgecolors='black')

    # 总体回归分析
    if len(clean_data) >= 2:
        slope, intercept, r_value, p_value, std_err = stats.linregress(
            clean_data['age'], clean_data['total_points']
        )

        x_range = np.array([clean_data['age'].min(), clean_data['age'].max()])
        y_range = intercept + slope * x_range

        ax.plot(x_range, y_range, 'r-', linewidth=3, alpha=0.9,
                label=f'Overall trend', zorder=6)

        # 相关性统计
        pearson_corr, pearson_p = stats.pearsonr(clean_data['age'], clean_data['total_points'])

        stats_text = f'Correlation Analysis:\n\n'
        stats_text += f'Pearson\'s r = {pearson_corr:.3f}\n'
        stats_text += f'p = {pearson_p:.3f}\n\n'
        stats_text += f'Regression: y = {intercept:.1f} + {slope:.2f}x\n'
        stats_text += f'R² = {r_value ** 2:.3f}'

        if pearson_p < 0.05:
            if pearson_corr < 0:
                stats_text += '\n\n✓ Younger athletes score higher'
            else:
                stats_text += '\n\n✓ Older athletes score higher'
        else:
            stats_text += '\n\n✗ No significant correlation'

        ax.text(0.02, 0.98, stats_text, transform=ax.transAxes,
                fontsize=10, verticalalignment='top',
                bbox=dict(boxstyle='round', facecolor='white', alpha=0.9, pad=0.5))

    # 图表属性
    ax.set_xlabel('Age (years)', fontsize=12)
    ax.set_ylabel('Total Points', fontsize=12)
    ax.set_title('Age vs Performance Correlation',
                 fontsize=15, fontweight='bold', pad=15)
    ax.grid(True, alpha=0.3)

    # 图例（限制数量）
    handles, labels = ax.get_legend_handles_labels()
    if handles:
        if len(handles) > 6:
            handles = handles[:6]
            labels = labels[:5] + ['...']
        ax.legend(handles, labels, loc='upper right', fontsize=10)

    # 样本信息
    sample_text = f'Sample Size:\n'
    sample_text += f'N = {len(clean_data)}\n'
    sample_text += f'Countries: {clean_data["country"].nunique()}\n'
    sample_text += f'Age Range: {clean_data["age"].min():.0f}-{clean_data["age"].max():.0f}'

    ax.text(0.98, 0.02, sample_text, transform=ax.transAxes,
            fontsize=9, verticalalignment='bottom', horizontalalignment='right',
            bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.8, pad=0.5))

    plt.tight_layout()
    plt.savefig('4_correlation.png', dpi=300, bbox_inches='tight')
    plt.show()
    plt.close(fig)


def print_summary_report(df, first_comp):
    """打印总结报告"""
    print("\n" + "=" * 60)
    print("SUMMARY REPORT")
    print("=" * 60)

    # 首次参赛年龄
    print(f"\n1. FIRST COMPETITION AGE:")
    print(f"   • Mean: {first_comp['age'].mean():.1f} years")
    print(f"   • Range: {first_comp['age'].min():.0f}-{first_comp['age'].max():.0f} years")

    china_first = first_comp[first_comp['country'] == 'CHN']
    if not china_first.empty:
        print(f"   • Chinese athletes: {china_first['age'].mean():.1f} years (n={len(china_first)})")

    # 年龄趋势
    final_data = df[df['phase'] == 'FINAL']
    yearly_means = final_data.groupby('year')['age'].mean()

    if len(yearly_means) >= 2:
        slope, intercept, r_value, p_value, std_err = stats.linregress(
            yearly_means.index, yearly_means.values
        )
        print(f"\n2. AGE TREND OVER TIME:")
        print(f"   • Slope: {slope:.3f} years per Olympic cycle")
        print(f"   • R²: {r_value ** 2:.3f}, p = {p_value:.3f}")

        if p_value < 0.05:
            print(f"   • Trend: {'Decreasing' if slope < 0 else 'Increasing'}")
        else:
            print(f"   • Trend: No significant change")

    # 年龄分组表现
    final_data['age_group'] = pd.cut(final_data['age'],
                                     bins=[0, 18, 22, 26, 30, 100],
                                     labels=['<18', '18-22', '23-26', '27-30', '30+'])

    performance_stats = final_data.groupby('age_group')['total_points'].mean()
    best_group = performance_stats.idxmax()

    final_data['got_medal'] = final_data['rank'] <= 3
    medal_rate = final_data.groupby('age_group')['got_medal'].mean() * 100
    best_medal_group = medal_rate.idxmax()

    print(f"\n3. PERFORMANCE BY AGE GROUP:")
    print(f"   • Highest scores: {best_group} ({performance_stats[best_group]:.1f} points)")
    print(f"   • Highest medal rate: {best_medal_group} ({medal_rate[best_medal_group]:.1f}%)")

    # 相关性
    clean_data = final_data.dropna(subset=['age', 'total_points'])
    if len(clean_data) >= 2:
        pearson_corr, pearson_p = stats.pearsonr(clean_data['age'], clean_data['total_points'])
        print(f"\n4. AGE-PERFORMANCE CORRELATION:")
        print(f"   • Pearson\'s r = {pearson_corr:.3f}")
        print(f"   • p-value = {pearson_p:.3f}")

        if pearson_p < 0.05:
            if pearson_corr < 0:
                print(f"   • Conclusion: Younger athletes achieve higher scores")
            else:
                print(f"   • Conclusion: Older athletes achieve higher scores")
        else:
            print(f"   • Conclusion: No significant correlation between age and performance")

    print("\n" + "=" * 60)


def main():
    """主函数"""
    print("OLYMPIC WOMEN'S 10M PLATFORM DIVING ANALYSIS")
    print("=" * 60)

    # 获取数据
    print("\nLoading data from database...")
    df = fetch_all_data()

    if df is None or df.empty:
        print("Error: No data available for analysis!")
        return

    print(f"✓ Data loaded successfully!")
    print(f"  • Total records: {len(df)}")
    print(f"  • Olympic editions: {len(df['year'].unique())}")
    print(f"  • Unique athletes: {df['athlete_name'].nunique()}")
    print(f"  • Countries: {df['country'].nunique()}")

    # 生成图表
    print("\nGenerating visualizations...")
    print("-" * 40)

    # 每生成一个图表后都显式关闭
    first_comp_data = plot_first_competition_analysis(df)
    plot_age_trends_integrated(df)
    plot_performance_by_age_integrated(df)
    plot_correlation_integrated(df)

    # 打印总结报告
    print_summary_report(df, first_comp_data)

    print("\n" + "=" * 60)
    print("ANALYSIS COMPLETE!")
    print("=" * 60)
    print("\nGenerated 4 integrated charts:")
    print("  1. 1_first_competition_age.png")
    print("  2. 2_age_trends.png")
    print("  3. 3_performance_by_age.png")
    print("  4. 4_correlation.png")
    print("\nAll charts saved to current directory.")


if __name__ == "__main__":
    main()