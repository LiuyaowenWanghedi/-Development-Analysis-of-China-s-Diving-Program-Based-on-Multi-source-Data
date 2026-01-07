import pandas as pd
import numpy as np
from sqlalchemy import create_engine, text
import os
from datetime import datetime
import hashlib

# 数据库连接
DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "root123456",
    "database": "OlympicDiving",
    "charset": "utf8mb4"
}

# 获取当前脚本所在目录
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


def create_sqlalchemy_engine():
    """创建SQLAlchemy引擎"""
    return create_engine(
        f"mysql+pymysql://{DB_CONFIG['user']}:{DB_CONFIG['password']}@{DB_CONFIG['host']}/{DB_CONFIG['database']}"
    )


def get_olympic_tables(engine):
    """获取所有汇总表名"""
    query = text("""
    SELECT TABLE_NAME 
    FROM INFORMATION_SCHEMA.TABLES 
    WHERE TABLE_SCHEMA = 'OlympicDiving' 
    AND TABLE_NAME LIKE '%Women10m%'
    AND TABLE_NAME LIKE '%Athlete_Rankings%'
    ORDER BY 
        CAST(SUBSTRING(TABLE_NAME, 1, 4) AS UNSIGNED),
        CASE 
            WHEN TABLE_NAME LIKE '%SEMIFINAL%' THEN 1
            WHEN TABLE_NAME LIKE '%FINAL%' THEN 2
            ELSE 3
        END
    """)

    with engine.connect() as conn:
        result = conn.execute(query)
        tables = [row[0] for row in result]

    return tables


def process_table(table_name, engine):
    """处理单个表"""
    print(f"处理表: {table_name}")

    # 读取数据
    df = pd.read_sql(f"SELECT * FROM `{table_name}`", engine)

    # 提取信息
    olympic_year = int(table_name[:4])

    if 'SEMIFINAL' in table_name:
        phase = 'SEMIFINAL'
        city = table_name.split('_')[1]
    else:
        phase = 'FINAL'
        city = table_name.split('_')[1]

    olympic_event = f"{olympic_year}_{city}"

    # 确定跳水次数
    if phase == 'SEMIFINAL' and olympic_year in [2000, 2004]:
        dive_count = 4
    else:
        dive_count = 5

    # 清洗数据
    df_clean = df.copy()

    # 重命名列以确保一致性
    column_mapping = {}
    for col in df_clean.columns:
        col_lower = str(col).lower()
        if 'athlete' in col_lower:
            column_mapping[col] = 'athlete_name'
        elif 'country' in col_lower or 'nation' in col_lower:
            column_mapping[col] = 'country'
        elif 'age' in col_lower:
            column_mapping[col] = 'age'
        elif 'rank' in col_lower:
            column_mapping[col] = 'rank'
        elif 'point' in col_lower or 'score' in col_lower:
            column_mapping[col] = 'total_points'

    df_clean = df_clean.rename(columns=column_mapping)

    # 清洗总分
    def clean_score(x):
        if pd.isna(x):
            return None

        x_str = str(x).strip()

        if isinstance(x, str) and 'Qualified' in x_str:
            import re
            match = re.search(r'(\d+\.?\d*)', x_str)
            return float(match.group(1)) if match else None
        else:
            try:
                return float(x_str)
            except:
                cleaned = ''.join(c for c in x_str if c.isdigit() or c == '.')
                try:
                    return float(cleaned) if cleaned else None
                except:
                    return None

    if 'total_points' in df_clean.columns:
        df_clean['total_score'] = df_clean['total_points'].apply(clean_score)
    else:
        print(f"  警告: 表 {table_name} 没有总分列")
        df_clean['total_score'] = None

    # 确保必要的列存在
    required_columns = ['athlete_name', 'country', 'rank', 'age', 'total_score']
    for col in required_columns:
        if col not in df_clean.columns:
            print(f"  警告: 表 {table_name} 缺少列 {col}")
            df_clean[col] = None

    # 类型转换
    df_clean['rank'] = pd.to_numeric(df_clean['rank'], errors='coerce')
    df_clean['age'] = pd.to_numeric(df_clean['age'], errors='coerce').astype('Int64')

    # 清理国家代码
    def clean_country(country):
        if pd.isna(country):
            return None
        country_str = str(country).strip().upper()
        return country_str[:3] if len(country_str) >= 3 else country_str

    df_clean['country'] = df_clean['country'].apply(clean_country)

    # 生成结果DataFrame
    result_df = pd.DataFrame({
        'athlete_name': df_clean['athlete_name'],
        'country': df_clean['country'],
        'olympic_year': olympic_year,
        'olympic_event': olympic_event,
        'competition_phase': phase,
        'age': df_clean['age'],
        'total_score': df_clean['total_score'],
        'overall_rank': df_clean['rank'],
        'dive_count': dive_count,
        'data_source': table_name
    })

    # 移除空记录
    result_df = result_df.dropna(subset=['athlete_name', 'total_score'])

    # 生成选手ID
    def generate_athlete_id(name, country):
        if pd.isna(name) or pd.isna(country):
            return None
        id_str = f"{name}_{country}".encode('utf-8')
        return hashlib.md5(id_str).hexdigest()[:8]

    result_df['athlete_id'] = result_df.apply(
        lambda row: generate_athlete_id(row['athlete_name'], row['country']),
        axis=1
    )

    print(f"  成功处理: {table_name} - {len(result_df)} 条有效记录")
    return result_df


def main():
    """主函数"""
    print(f"脚本运行目录: {SCRIPT_DIR}")

    # 创建数据库连接
    engine = create_sqlalchemy_engine()

    # 获取所有汇总表
    tables = get_olympic_tables(engine)
    print(f"找到 {len(tables)} 个汇总表")

    # 处理所有表
    all_records = []
    for table in tables:
        try:
            df_result = process_table(table, engine)
            all_records.append(df_result)
        except Exception as e:
            print(f"  处理失败: {table} - 错误: {e}")
            import traceback
            traceback.print_exc()

    if not all_records:
        print("没有处理任何数据")
        return

    # 合并所有数据
    combined_df = pd.concat(all_records, ignore_index=True, sort=False)

    print(f"\n合并后总记录数: {len(combined_df)}")

    # 数据验证
    print("\n数据验证:")
    print(f"选手姓名缺失: {combined_df['athlete_name'].isna().sum()}")
    print(f"总分缺失: {combined_df['total_score'].isna().sum()}")
    print(f"年龄缺失: {combined_df['age'].isna().sum()}")
    print(f"排名缺失: {combined_df['overall_rank'].isna().sum()}")

    # 确保数据类型正确
    combined_df['overall_rank'] = pd.to_numeric(combined_df['overall_rank'], errors='coerce').astype('Int64')
    combined_df['age'] = pd.to_numeric(combined_df['age'], errors='coerce').astype('Int64')
    combined_df['total_score'] = pd.to_numeric(combined_df['total_score'], errors='coerce')

    # 更新奖牌状态
    def get_medal_status(row):
        if row['competition_phase'] == 'FINAL':
            if pd.isna(row['overall_rank']):
                return 'none'
            if row['overall_rank'] == 1:
                return 'gold'
            elif row['overall_rank'] == 2:
                return 'silver'
            elif row['overall_rank'] == 3:
                return 'bronze'
        return 'none'

    combined_df['medal_status'] = combined_df.apply(get_medal_status, axis=1)

    # 更新 reached_final 状态
    # 先找出进入决赛的选手
    finalists = combined_df[
        combined_df['competition_phase'] == 'FINAL'
        ][['athlete_id', 'olympic_year']].drop_duplicates()
    finalists['is_finalist'] = 1

    combined_df = pd.merge(
        combined_df,
        finalists,
        on=['athlete_id', 'olympic_year'],
        how='left'
    )

    def get_reached_final(row):
        if row['competition_phase'] == 'FINAL':
            return 1
        elif pd.notna(row['is_finalist']):
            return 1
        else:
            return 0

    combined_df['reached_final'] = combined_df.apply(get_reached_final, axis=1)
    combined_df = combined_df.drop('is_finalist', axis=1)

    # 重新排列列顺序
    column_order = [
        'record_id',
        'athlete_id',
        'athlete_name',
        'country',
        'olympic_year',
        'olympic_event',
        'competition_phase',
        'reached_final',
        'age',
        'total_score',
        'overall_rank',
        'medal_status',
        'dive_count',
        'data_source'
    ]

    combined_df = combined_df.reset_index(drop=True)
    combined_df.insert(0, 'record_id', combined_df.index + 1)

    # 重新排序列
    combined_df = combined_df[column_order]

    # 保存到数据库
    print(f"\n保存到数据库...")
    try:
        with engine.begin() as conn:
            # 如果表已存在，先删除
            conn.execute(text("DROP TABLE IF EXISTS athlete_olympic_records"))

            # 创建表（精简版）
            create_table_sql = text("""
            CREATE TABLE athlete_olympic_records (
                record_id INT PRIMARY KEY,
                athlete_id VARCHAR(50) NOT NULL,
                athlete_name VARCHAR(100) NOT NULL,
                country VARCHAR(3) NOT NULL,
                olympic_year INT NOT NULL,
                olympic_event VARCHAR(50) NOT NULL,
                competition_phase ENUM('SEMIFINAL', 'FINAL') NOT NULL,
                reached_final TINYINT(1) DEFAULT 0,
                age INT,
                total_score DECIMAL(8,2) NOT NULL,
                overall_rank INT,
                medal_status ENUM('gold', 'silver', 'bronze', 'none') DEFAULT 'none',
                dive_count INT NOT NULL,
                data_source VARCHAR(100),
                INDEX idx_athlete_id (athlete_id),
                INDEX idx_year_phase (olympic_year, competition_phase),
                INDEX idx_age (age),
                INDEX idx_country (country)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """)
            conn.execute(create_table_sql)

        # 插入数据
        combined_df.to_sql('athlete_olympic_records', engine,
                           if_exists='append', index=False)
        print("数据库保存成功！")

    except Exception as e:
        print(f"数据库保存失败: {e}")
        import traceback
        traceback.print_exc()

    # 保存到CSV文件
    try:
        # 主数据表
        csv_path = os.path.join(SCRIPT_DIR, 'athlete_olympic_records.csv')
        combined_df.to_csv(csv_path, index=False, encoding='utf-8-sig')
        print(f"主数据表已保存到: {csv_path}")

        # 选手映射表
        athlete_mapping = combined_df[['athlete_id', 'athlete_name', 'country']].drop_duplicates()
        mapping_path = os.path.join(SCRIPT_DIR, 'athlete_mapping.csv')
        athlete_mapping.to_csv(mapping_path, index=False, encoding='utf-8-sig')
        print(f"选手映射表已保存到: {mapping_path}")

        # 年龄分析数据（决赛数据）
        age_analysis_df = combined_df[combined_df['competition_phase'] == 'FINAL'][
            ['athlete_id', 'athlete_name', 'country', 'olympic_year', 'age',
             'total_score', 'overall_rank', 'medal_status', 'reached_final']
        ].copy()
        age_analysis_path = os.path.join(SCRIPT_DIR, 'age_analysis_data.csv')
        age_analysis_df.to_csv(age_analysis_path, index=False, encoding='utf-8-sig')
        print(f"年龄分析数据已保存到: {age_analysis_path}")

        # 简要的统计报告
        stats_report_path = os.path.join(SCRIPT_DIR, 'data_statistics.txt')
        with open(stats_report_path, 'w', encoding='utf-8') as f:
            f.write("奥运会女子10米跳台数据整合统计报告\n")
            f.write("=" * 50 + "\n\n")
            f.write(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

            f.write("数据概览:\n")
            f.write(f"  总记录数: {len(combined_df)}\n")
            f.write(f"  唯一选手数: {combined_df['athlete_id'].nunique()}\n")
            f.write(f"  年份范围: {combined_df['olympic_year'].min()} - {combined_df['olympic_year'].max()}\n")

            phase_counts = combined_df['competition_phase'].value_counts()
            f.write(f"  半决赛记录: {phase_counts.get('SEMIFINAL', 0)}\n")
            f.write(f"  决赛记录: {phase_counts.get('FINAL', 0)}\n")

            final_participants = combined_df[combined_df['reached_final'] == 1]['athlete_id'].nunique()
            f.write(f"  进入过决赛的选手数: {final_participants}\n")

            # 字段说明
            f.write("\n字段说明:\n")
            f.write("  reached_final: 是否进入决赛 (0=否, 1=是)\n")
            f.write("    对于半决赛记录: 0=未进决赛, 1=进入决赛\n")
            f.write("    对于决赛记录: 固定为1\n")

            # 奖牌统计
            f.write("\n奖牌统计:\n")
            medal_stats = combined_df[combined_df['competition_phase'] == 'FINAL']['medal_status'].value_counts()
            for medal in ['gold', 'silver', 'bronze']:
                count = medal_stats.get(medal, 0)
                f.write(f"  {medal}: {count}\n")

            # 年龄统计
            f.write("\n年龄分布统计 (决赛):\n")
            final_ages = combined_df[combined_df['competition_phase'] == 'FINAL']['age']
            if not final_ages.empty:
                f.write(f"  最小年龄: {final_ages.min()} 岁\n")
                f.write(f"  最大年龄: {final_ages.max()} 岁\n")
                f.write(f"  平均年龄: {final_ages.mean():.1f} 岁\n")
                f.write(f"  年龄中位数: {final_ages.median()} 岁\n")

            # 文件列表
            f.write("\n生成的文件:\n")
            f.write(f"  1. athlete_olympic_records.csv - 主数据表\n")
            f.write(f"  2. athlete_mapping.csv - 选手映射表\n")
            f.write(f"  3. age_analysis_data.csv - 年龄分析数据\n")
            f.write(f"  4. data_statistics.txt - 本统计报告\n")

        print(f"统计报告已保存到: {stats_report_path}")

    except Exception as e:
        print(f"CSV保存失败: {e}")
        import traceback
        traceback.print_exc()

    # 显示最终统计信息
    print(f"\n最终数据统计:")
    print(f"总记录数: {len(combined_df)}")
    print(f"唯一选手数: {combined_df['athlete_id'].nunique()}")
    print(f"年份范围: {combined_df['olympic_year'].min()} - {combined_df['olympic_year'].max()}")

    phase_counts = combined_df['competition_phase'].value_counts()
    print(f"半决赛记录: {phase_counts.get('SEMIFINAL', 0)}")
    print(f"决赛记录: {phase_counts.get('FINAL', 0)}")

    final_participants = combined_df[combined_df['reached_final'] == 1]['athlete_id'].nunique()
    print(f"进入过决赛的选手数: {final_participants}")

    # 奖牌统计
    medal_stats = combined_df[combined_df['competition_phase'] == 'FINAL']['medal_status'].value_counts()
    print(f"\n奖牌统计:")
    for medal in ['gold', 'silver', 'bronze']:
        count = medal_stats.get(medal, 0)
        print(f"  {medal}: {count}")

    # 年龄分布统计
    print(f"\n年龄分布统计 (决赛):")
    final_ages = combined_df[combined_df['competition_phase'] == 'FINAL']['age']
    if not final_ages.empty:
        print(f"  最小年龄: {final_ages.min()} 岁")
        print(f"  最大年龄: {final_ages.max()} 岁")
        print(f"  平均年龄: {final_ages.mean():.1f} 岁")
        print(f"  年龄中位数: {final_ages.median()} 岁")

        # 年龄分组统计
        age_groups = pd.cut(final_ages,
                            bins=[0, 16, 20, 25, 30, 100],
                            labels=['≤16', '17-20', '21-25', '26-30', '>30'])
        age_group_counts = age_groups.value_counts().sort_index()
        print(f"\n  年龄分组:")
        for group, count in age_group_counts.items():
            print(f"    {group}: {count} 人 ({count / len(final_ages) * 100:.1f}%)")

    print(f"\n所有文件已保存到脚本所在目录: {SCRIPT_DIR}")

    engine.dispose()


if __name__ == "__main__":
    main()