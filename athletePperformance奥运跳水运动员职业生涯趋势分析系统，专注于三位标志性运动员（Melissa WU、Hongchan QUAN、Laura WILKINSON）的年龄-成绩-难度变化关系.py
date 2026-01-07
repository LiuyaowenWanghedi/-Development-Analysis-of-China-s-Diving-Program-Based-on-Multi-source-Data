import mysql.connector
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import re

# 数据库配置
DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "root123456",
    "database": "OlympicDiving"
}

# 运动员参赛年份映射
ATHLETE_YEARS = {
    "Melissa WU": [2008, 2012, 2016, 2020, 2024],
    "Hongchan QUAN": [2020, 2024],
    "Laura WILKINSON": [2000, 2004, 2008]
}


def get_all_tables():
    """获取数据库中所有表名"""
    connection = None
    tables = []
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        cursor = connection.cursor()
        cursor.execute("SHOW TABLES")
        tables = [table[0] for table in cursor.fetchall()]
    except mysql.connector.Error as err:
        print(f"数据库错误: {err}")
    finally:
        if connection and connection.is_connected():
            cursor.close()
            connection.close()
    return tables


def find_tables_by_year_and_type(year, table_type):
    """根据年份和表类型查找表名"""
    all_tables = get_all_tables()
    matching_tables = []

    for table in all_tables:
        if str(year) in table:
            if table_type == 'ranking' and 'Athlete_Ranking' in table and 'FINAL' in table:
                matching_tables.append(table)
            elif table_type == 'score' and 'Detailed_Score' in table and 'FINAL' in table:
                matching_tables.append(table)

    return matching_tables


def fetch_athlete_data(athlete_name, years):
    """从数据库获取数据"""
    data_by_year = {}

    for year in years:
        ranking_tables = find_tables_by_year_and_type(year, 'ranking')
        if not ranking_tables:
            continue
        ranking_table = ranking_tables[0]

        score_tables = find_tables_by_year_and_type(year, 'score')
        if not score_tables:
            continue
        score_table = score_tables[0]

        connection = None
        try:
            connection = mysql.connector.connect(**DB_CONFIG)
            cursor = connection.cursor(dictionary=True)

            query_rank = f"SELECT * FROM `{ranking_table}` WHERE Athlete = %s"
            cursor.execute(query_rank, (athlete_name,))
            rank_data = cursor.fetchone()

            if not rank_data:
                continue

            query_score = f"SELECT * FROM `{score_table}` WHERE Athlete_Name = %s ORDER BY Dive_Number"
            cursor.execute(query_score, (athlete_name,))
            score_rows = cursor.fetchall()

            if not score_rows:
                continue

            score_df = pd.DataFrame(score_rows)
            score_df['Dive_Points'] = pd.to_numeric(score_df['Dive_Points'], errors='coerce')
            score_df['Difficulty_Degree'] = pd.to_numeric(score_df['Difficulty_Degree'], errors='coerce')

            age = rank_data.get('Age')
            total_points = rank_data.get('Total_Points')

            if isinstance(total_points, str):
                try:
                    numbers = re.findall(r'\d+\.?\d*', total_points)
                    if numbers:
                        total_points = float(numbers[0])
                    else:
                        total_points = score_df['Dive_Points'].sum()
                except:
                    total_points = score_df['Dive_Points'].sum()
            else:
                total_points = float(total_points) if total_points is not None else score_df['Dive_Points'].sum()

            if age is not None:
                age = int(age)
            else:
                age = 0

            data_by_year[year] = {
                'age': age,
                'total_score': total_points,
                'score_details': score_df
            }

        except Exception:
            continue
        finally:
            if connection and connection.is_connected():
                cursor.close()
                connection.close()

    return data_by_year


def create_minimal_dual_axis_chart(athlete_name, data_by_year):
    """创建极简双轴折线图：年龄-成绩趋势 + 难度系数"""
    if not data_by_year:
        return None

    # 准备数据
    sorted_years = sorted(data_by_year.keys())
    ages = [data_by_year[year]['age'] for year in sorted_years]
    scores = [data_by_year[year]['total_score'] for year in sorted_years]

    # 计算难度系数
    difficulties = []
    for year in sorted_years:
        score_df = data_by_year[year]['score_details']
        avg_diff = score_df['Difficulty_Degree'].mean()
        difficulties.append(round(avg_diff, 3))

    # 找出关键点
    peak_idx = np.argmax(scores)
    peak_age = ages[peak_idx]
    peak_year = sorted_years[peak_idx]
    peak_score = scores[peak_idx]

    # 创建图表 - 紧凑尺寸
    fig, ax1 = plt.subplots(figsize=(10, 6))

    # ====== 左轴：总分（蓝色） ======
    # 使用低饱和度蓝色
    color_score = '#1f77b4'

    # 绘制总分折线
    line1 = ax1.plot(ages, scores, 'o-', linewidth=2, markersize=8,
                     color=color_score, markerfacecolor='white',
                     markeredgewidth=2, label='Total Score')

    ax1.set_xlabel('Age (years)', fontsize=11, fontweight='bold')
    ax1.set_ylabel('Total Score', fontsize=11, fontweight='bold', color=color_score)
    ax1.tick_params(axis='y', labelcolor=color_score)

    # 设置Y轴范围 - 为标注留出空间
    score_min, score_max = min(scores), max(scores)
    score_range = score_max - score_min
    ax1.set_ylim(max(0, score_min - score_range * 0.15),
                 score_max + score_range * 0.2)

    # ====== 右轴：难度系数（橙色） ======
    # 使用低饱和度橙色
    color_diff = '#ff7f0e'
    ax2 = ax1.twinx()

    # 绘制难度折线
    line2 = ax2.plot(ages, difficulties, 's--', linewidth=1.5, markersize=6,
                     color=color_diff, markerfacecolor='white',
                     markeredgewidth=1.5, label='Difficulty')

    ax2.set_ylabel('Avg Difficulty', fontsize=11, fontweight='bold', color=color_diff)
    ax2.tick_params(axis='y', labelcolor=color_diff)

    # 设置难度轴范围
    diff_min, diff_max = min(difficulties), max(difficulties)
    diff_range = max(0.1, diff_max - diff_min)
    ax2.set_ylim(diff_min - diff_range * 0.15, diff_max + diff_range * 0.15)

    # ====== 数据点标注 ======
    for i, (age, score, year, diff) in enumerate(zip(ages, scores, sorted_years, difficulties)):
        # 标注年龄和总分（核心信息）
        if i == peak_idx:
            # 巅峰点标注 - 突出显示
            ax1.annotate(f'Age {age}\n{score:.1f}',
                         xy=(age, score), xytext=(0, 15),
                         textcoords='offset points',
                         fontsize=10, fontweight='bold', color='#d62728',
                         ha='center', va='bottom',
                         bbox=dict(boxstyle='round,pad=0.3',
                                   facecolor='white', edgecolor='#d62728',
                                   linewidth=1.5, alpha=0.9))

            # 添加年份标记
            ax1.annotate(f'{year} (Peak)', xy=(age, ax1.get_ylim()[0]),
                         xytext=(0, -35), textcoords='offset points',
                         fontsize=9, fontweight='bold', color='#d62728',
                         ha='center', va='top')
        else:
            # 普通点标注 - 简洁
            ax1.annotate(f'{score:.1f}',
                         xy=(age, score), xytext=(0, 8),
                         textcoords='offset points',
                         fontsize=9, color=color_score,
                         ha='center', va='bottom', alpha=0.8)

            # 年份标记在X轴下方
            ax1.annotate(str(year), xy=(age, ax1.get_ylim()[0]),
                         xytext=(0, -25), textcoords='offset points',
                         fontsize=8, color='#666666', ha='center', va='top')

    # ====== 趋势分析标注 ======
    # 计算趋势
    if len(scores) > 1:
        score_change = scores[-1] - scores[0]
        diff_change = difficulties[-1] - difficulties[0]

        # 在右上角添加趋势分析
        trend_text = f"Career Trend:\n"
        if score_change > 0:
            trend_text += f"Score: +{score_change:.1f}\n"
        else:
            trend_text += f"Score: {score_change:.1f}\n"

        if diff_change > 0:
            trend_text += f"Difficulty: +{diff_change:.3f}"
        else:
            trend_text += f"Difficulty: {diff_change:.3f}"

        ax1.text(0.98, 0.98, trend_text,
                 transform=ax1.transAxes, fontsize=9,
                 ha='right', va='top',
                 bbox=dict(boxstyle='round,pad=0.4', facecolor='#f8f8f8',
                           edgecolor='#ddd', alpha=0.8))

    # ====== 图例 ======
    # 合并两个图例
    lines = line1 + line2
    labels = [l.get_label() for l in lines]
    ax1.legend(lines, labels, loc='upper left', fontsize=10,
               frameon=True, framealpha=0.9)

    # ====== 设置标题 ======
    plt.title(f'{athlete_name}: Olympic 10m Platform Final Performance\n'
              f'Age vs Score with Difficulty Trend ({min(sorted_years)}-{max(sorted_years)})',
              fontsize=12, fontweight='bold', pad=15)

    # ====== 网格和样式 ======
    ax1.grid(True, alpha=0.2, linestyle='--', which='both')

    # 调整布局
    plt.tight_layout()

    # 保存图表
    output_filename = f"{athlete_name.replace(' ', '_')}_Minimal_Trend.png"
    plt.savefig(output_filename, dpi=300, facecolor='white', bbox_inches='tight')
    print(f"📈 极简趋势图已保存: {output_filename}")

    plt.show()

    return {
        'athlete': athlete_name,
        'peak_score': peak_score,
        'peak_year': peak_year,
        'peak_age': peak_age,
        'score_trend': score_change if len(scores) > 1 else 0,
        'diff_trend': diff_change if len(difficulties) > 1 else 0
    }


def main():
    print("📊 奥运女子10米跳台 - 极简趋势分析")
    print("=" * 45)
    print("设计理念：聚焦年龄-成绩核心趋势，技术指标辅助")
    print("=" * 45)

    results = []

    for athlete, years in ATHLETE_YEARS.items():
        print(f"\n分析: {athlete}")
        print(f"年份: {years}")

        data = fetch_athlete_data(athlete, years)
        if not data:
            print(f"  未找到数据")
            continue

        print(f"  获取 {len(data)} 年数据")

        result = create_minimal_dual_axis_chart(athlete, data)
        if result:
            results.append(result)
            print(f"  • 巅峰: {result['peak_year']}年 ({result['peak_age']}岁)")
            print(f"  • 巅峰分: {result['peak_score']:.1f}")
            if result['score_trend'] != 0:
                trend = "↑" if result['score_trend'] > 0 else "↓"
                print(f"  • 趋势: 得分{trend}{abs(result['score_trend']):.1f}, "
                      f"难度{result['diff_trend']:+.3f}")

    # 生成对比分析
    if results:
        print(f"\n{'=' * 45}")
        print("对比分析")
        print(f"{'=' * 45}")

        print(f"\n{'运动员':<15} {'巅峰分':<10} {'巅峰年龄':<10} {'职业生涯':<12}")
        print("-" * 50)

        for result in sorted(results, key=lambda x: x['peak_score'], reverse=True):
            career_span = f"{min(years)}-{max(years)}"
            print(f"{result['athlete']:<15} {result['peak_score']:<10.1f} "
                  f"{result['peak_age']:<10} {career_span:<12}")

        print(f"\n📁 图表文件:")
        for result in results:
            filename = f"{result['athlete'].replace(' ', '_')}_Minimal_Trend.png"
            print(f"  • {filename}")


if __name__ == "__main__":
    main()