import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats
import pymysql
import re
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import mean_absolute_error, r2_score, accuracy_score, roc_auc_score, confusion_matrix
from sklearn.ensemble import RandomForestRegressor, RandomForestClassifier
import xgboost as xgb
import lightgbm as lgb
from sklearn.inspection import PartialDependenceDisplay

# 设置样式
plt.rcParams['font.sans-serif'] = ['Arial', 'DejaVu Sans', 'Helvetica']
plt.rcParams['axes.unicode_minus'] = False
sns.set_style("whitegrid")
plt.rcParams['figure.figsize'] = (12, 6)

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
            '2004_Athens_Women10m_FINAL_Athlete_Rankings',
            '2008_Beijing_Women10m_FINAL_Athlete_Rankings',
            '2012_London_Women10m_FINAL_Athlete_Rankings',
            '2016_Rio_Women10m_FINAL_Athlete_Rankings',
            '2020_Tokyo_Women10m_FINAL_Athlete_Rankings',
            '2024_Paris_Women10m_FINAL_Athlete_Rankings',
            '2000_Sydney_Women10m_SEMIFINAL_Athlete_Rankings',
            '2004_Athens_Women10m_SEMIFINAL_Athlete_Rankings',
            '2008_Beijing_Women10m_SEMIFINAL_Athlete_Rankings',
            '2012_London_Women10m_SEMIFINAL_Athlete_Rankings',
            '2016_Rio_Women10m_SEMIFINAL_Athlete_Rankings',
            '2020_Tokyo_Women10m_SEMIFINAL_Athlete_Rankings',
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


def prepare_features(df):
    """准备机器学习特征"""
    final_data = df[df['phase'] == 'FINAL'].copy()

    # 计算首次参赛年龄
    athlete_first_age = final_data.sort_values(['athlete_name', 'year']).groupby('athlete_name')['age'].first()
    final_data['first_age'] = final_data['athlete_name'].map(athlete_first_age)
    final_data['current_age'] = final_data['age']
    final_data['age_diff'] = final_data['current_age'] - final_data['first_age']

    # 年龄分组
    def categorize_age(age):
        if pd.isna(age):
            return 'Unknown'
        elif age < 18:
            return '<18'
        elif age < 22:
            return '18-21'
        elif age < 26:
            return '22-25'
        elif age < 30:
            return '26-29'
        else:
            return '30+'

    final_data['age_group'] = final_data['current_age'].apply(categorize_age)

    # 是否中国选手
    final_data['is_china'] = (final_data['country'] == 'CHN').astype(int)

    # 是否获奖牌
    final_data['won_medal'] = (final_data['rank'] <= 3).astype(int)

    # 运动员经验
    athlete_comp_count = final_data.groupby('athlete_name')['year'].count()
    final_data['comp_count'] = final_data['athlete_name'].map(athlete_comp_count)

    # 历史平均成绩
    athlete_avg_score = final_data.groupby('athlete_name')['total_points'].mean()
    final_data['avg_score'] = final_data['athlete_name'].map(athlete_avg_score)

    # 年份标准化
    final_data['year_norm'] = (final_data['year'] - 2000) / 24

    return final_data


def prepare_model_data(final_data):
    """准备模型数据"""
    # 特征列表
    numeric_features = ['first_age', 'current_age', 'age_diff', 'is_china', 'comp_count', 'avg_score', 'year_norm']

    # 处理缺失值
    X_numeric = final_data[numeric_features].fillna(0).values

    # 编码分类特征
    categorical_features = ['age_group']
    encoder = OneHotEncoder(sparse_output=False, drop='first')
    X_categorical = encoder.fit_transform(final_data[categorical_features].fillna('Unknown'))

    # 合并特征
    X = np.hstack([X_numeric, X_categorical])

    # 特征名称
    feature_names = numeric_features.copy()
    if hasattr(encoder, 'categories_'):
        for i, feature in enumerate(categorical_features):
            categories = encoder.categories_[i][1:]
            feature_names.extend([f"{feature}_{cat}" for cat in categories])

    # 回归目标
    y_reg = final_data['total_points'].values

    # 分类目标
    y_cls = final_data['won_medal'].values

    return X, y_reg, y_cls, feature_names, final_data


def train_and_evaluate_models(X, y_reg, y_cls, feature_names):
    """训练和评估模型"""
    results = {'regression': {}, 'classification': {}}
    models = {'regression': {}, 'classification': {}}

    # 划分训练测试集
    X_train_reg, X_test_reg, y_train_reg, y_test_reg = train_test_split(X, y_reg, test_size=0.2, random_state=42)
    X_train_cls, X_test_cls, y_train_cls, y_test_cls = train_test_split(X, y_cls, test_size=0.2, random_state=42,
                                                                        stratify=y_cls)

    # 标准化
    scaler = StandardScaler()
    X_train_reg_scaled = scaler.fit_transform(X_train_reg)
    X_test_reg_scaled = scaler.transform(X_test_reg)
    X_train_cls_scaled = scaler.fit_transform(X_train_cls)
    X_test_cls_scaled = scaler.transform(X_test_cls)

    # 回归模型
    print("训练回归模型...")
    reg_models = {
        'XGBoost': xgb.XGBRegressor(n_estimators=100, max_depth=5, learning_rate=0.1, random_state=42),
        'LightGBM': lgb.LGBMRegressor(n_estimators=100, max_depth=5, learning_rate=0.1, random_state=42, verbose=-1),
        'RandomForest': RandomForestRegressor(n_estimators=100, max_depth=5, random_state=42)
    }

    for name, model in reg_models.items():
        model.fit(X_train_reg_scaled, y_train_reg)
        y_pred = model.predict(X_test_reg_scaled)

        results['regression'][name] = {
            'mae': mean_absolute_error(y_test_reg, y_pred),
            'r2': r2_score(y_test_reg, y_pred),
            'model': model
        }
        models['regression'][name] = model

    # 分类模型
    print("训练分类模型...")
    cls_models = {
        'XGBoost': xgb.XGBClassifier(n_estimators=100, max_depth=5, learning_rate=0.1, random_state=42,
                                     use_label_encoder=False),
        'LightGBM': lgb.LGBMClassifier(n_estimators=100, max_depth=5, learning_rate=0.1, random_state=42, verbose=-1),
        'RandomForest': RandomForestClassifier(n_estimators=100, max_depth=5, random_state=42, class_weight='balanced')
    }

    for name, model in cls_models.items():
        model.fit(X_train_cls_scaled, y_train_cls)
        y_pred = model.predict(X_test_cls_scaled)
        y_proba = model.predict_proba(X_test_cls_scaled)[:, 1]

        results['classification'][name] = {
            'accuracy': accuracy_score(y_test_cls, y_pred),
            'auc': roc_auc_score(y_test_cls, y_proba),
            'model': model
        }
        models['classification'][name] = model

    return results, models, scaler


def plot_feature_importance(models_dict, feature_names, task_type):
    """绘制特征重要性"""
    fig, axes = plt.subplots(1, 3, figsize=(18, 6))

    for idx, (model_name, model) in enumerate(models_dict.items()):
        ax = axes[idx]

        if hasattr(model, 'feature_importances_'):
            importances = model.feature_importances_

            # 确保长度匹配
            if len(importances) > len(feature_names):
                importances = importances[:len(feature_names)]
            elif len(importances) < len(feature_names):
                feature_names = feature_names[:len(importances)]

            importance_df = pd.DataFrame({
                'feature': feature_names,
                'importance': importances
            }).sort_values('importance', ascending=True).tail(10)

            y_pos = np.arange(len(importance_df))
            ax.barh(y_pos, importance_df['importance'], color=plt.cm.viridis(np.linspace(0.3, 0.9, len(importance_df))))

            ax.set_yticks(y_pos)
            ax.set_yticklabels(importance_df['feature'])
            ax.set_title(f'{model_name}')
            ax.grid(True, alpha=0.3, axis='x')

    plt.suptitle(f'Feature Importance - {task_type}', fontsize=14, fontweight='bold')
    plt.tight_layout()
    filename = f'feature_importance_{task_type}.png'
    plt.savefig(filename, dpi=300, bbox_inches='tight')
    plt.show()
    print(f"已保存: {filename}")


def plot_age_performance_relationship(final_data):
    """绘制年龄与成绩关系图"""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))

    # 散点图
    scatter = ax1.scatter(final_data['current_age'], final_data['total_points'],
                          c=final_data['won_medal'], cmap='coolwarm',
                          s=60, alpha=0.7, edgecolors='black')

    # 二次拟合
    age_clean = final_data['current_age'].dropna()
    score_clean = final_data['total_points'].dropna()

    if len(age_clean) > 10:
        coeffs = np.polyfit(age_clean, score_clean, 2)
        poly = np.poly1d(coeffs)
        x_fit = np.linspace(age_clean.min(), age_clean.max(), 100)
        ax1.plot(x_fit, poly(x_fit), 'r-', linewidth=3, label=f'Quadratic fit')

        # 找到顶点
        vertex_x = -coeffs[1] / (2 * coeffs[0])
        vertex_y = poly(vertex_x)
        ax1.scatter([vertex_x], [vertex_y], color='yellow', s=200,
                    edgecolors='black', zorder=5, label=f'Peak: {vertex_x:.1f} years')

    ax1.set_xlabel('Age (years)')
    ax1.set_ylabel('Total Points')
    ax1.set_title('Age vs Performance')
    ax1.grid(True, alpha=0.3)
    ax1.legend()

    # 年龄分组箱线图
    age_groups = ['<18', '18-21', '22-25', '26-29', '30+']
    group_data = []

    for group in age_groups:
        if group == '<18':
            scores = final_data[final_data['current_age'] < 18]['total_points']
        elif group == '18-21':
            scores = final_data[(final_data['current_age'] >= 18) & (final_data['current_age'] < 22)]['total_points']
        elif group == '22-25':
            scores = final_data[(final_data['current_age'] >= 22) & (final_data['current_age'] < 26)]['total_points']
        elif group == '26-29':
            scores = final_data[(final_data['current_age'] >= 26) & (final_data['current_age'] < 30)]['total_points']
        else:
            scores = final_data[final_data['current_age'] >= 30]['total_points']

        if len(scores) > 0:
            group_data.append(scores.values)

    ax2.boxplot(group_data, labels=age_groups[:len(group_data)], patch_artist=True,
                boxprops={'facecolor': 'lightblue', 'alpha': 0.7})
    ax2.set_xlabel('Age Group')
    ax2.set_ylabel('Total Points')
    ax2.set_title('Performance by Age Group')
    ax2.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig('age_performance_analysis.png', dpi=300, bbox_inches='tight')
    plt.show()
    print("已保存: age_performance_analysis.png")


def plot_model_comparison(results):
    """绘制模型性能比较图"""
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))

    # 回归模型
    ax1 = axes[0]
    reg_models = list(results['regression'].keys())
    reg_r2 = [results['regression'][m]['r2'] for m in reg_models]
    reg_mae = [results['regression'][m]['mae'] for m in reg_models]

    x = np.arange(len(reg_models))
    width = 0.35

    bars1 = ax1.bar(x - width / 2, reg_r2, width, label='R²', color='lightblue', edgecolor='black')
    ax2 = ax1.twinx()
    bars2 = ax2.bar(x + width / 2, reg_mae, width, label='MAE', color='lightcoral', edgecolor='black')

    ax1.set_xlabel('Model')
    ax1.set_ylabel('R² (Higher better)', color='lightblue')
    ax2.set_ylabel('MAE (Lower better)', color='lightcoral')
    ax1.set_xticks(x)
    ax1.set_xticklabels(reg_models)
    ax1.set_title('Regression Models')
    ax1.grid(True, alpha=0.3)

    # 分类模型
    ax3 = axes[1]
    cls_models = list(results['classification'].keys())
    cls_acc = [results['classification'][m]['accuracy'] for m in cls_models]
    cls_auc = [results['classification'][m]['auc'] for m in cls_models]

    bars3 = ax3.bar(x - width / 2, cls_acc, width, label='Accuracy', color='lightgreen', edgecolor='black')
    ax4 = ax3.twinx()
    bars4 = ax4.bar(x + width / 2, cls_auc, width, label='AUC', color='gold', edgecolor='black')

    ax3.set_xlabel('Model')
    ax3.set_ylabel('Accuracy', color='lightgreen')
    ax4.set_ylabel('AUC', color='gold')
    ax3.set_xticks(x)
    ax3.set_xticklabels(cls_models)
    ax3.set_title('Classification Models')
    ax3.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig('model_comparison.png', dpi=300, bbox_inches='tight')
    plt.show()
    print("已保存: model_comparison.png")


def export_results(results, final_data):
    """导出结果到Excel"""
    with pd.ExcelWriter('analysis_results.xlsx', engine='openpyxl') as writer:
        # 模型性能
        reg_df = pd.DataFrame([
            {'Model': name, 'R²': metrics['r2'], 'MAE': metrics['mae']}
            for name, metrics in results['regression'].items()
        ])
        reg_df.to_excel(writer, sheet_name='Regression_Performance', index=False)

        cls_df = pd.DataFrame([
            {'Model': name, 'Accuracy': metrics['accuracy'], 'AUC': metrics['auc']}
            for name, metrics in results['classification'].items()
        ])
        cls_df.to_excel(writer, sheet_name='Classification_Performance', index=False)

        # 数据统计
        stats_df = final_data[['current_age', 'total_points', 'won_medal', 'is_china']].describe()
        stats_df.to_excel(writer, sheet_name='Data_Statistics')

        # 年龄分组统计
        age_stats = []
        for age in [16, 18, 20, 22, 24, 26, 28, 30]:
            age_data = final_data[final_data['current_age'] >= age]
            if len(age_data) > 0:
                age_stats.append({
                    'Age_Threshold': age,
                    'Count': len(age_data),
                    'Avg_Score': age_data['total_points'].mean(),
                    'Medal_Rate': age_data['won_medal'].mean() * 100
                })

        age_df = pd.DataFrame(age_stats)
        age_df.to_excel(writer, sheet_name='Age_Analysis', index=False)

    print("已保存: analysis_results.xlsx")


def print_summary(results, final_data):
    """打印分析总结"""
    print("\n" + "=" * 60)
    print("分析总结")
    print("=" * 60)

    # 数据统计
    print(f"\n数据统计:")
    print(f"  • 总样本数: {len(final_data)}")
    print(f"  • 年龄范围: {final_data['current_age'].min():.0f} - {final_data['current_age'].max():.0f}")
    print(f"  • 平均年龄: {final_data['current_age'].mean():.1f}")
    print(f"  • 中国选手比例: {final_data['is_china'].mean():.2%}")
    print(f"  • 获奖牌比例: {final_data['won_medal'].mean():.2%}")

    # 最佳回归模型
    if results['regression']:
        best_reg = max(results['regression'].items(), key=lambda x: x[1]['r2'])
        print(f"\n最佳回归模型 ({best_reg[0]}):")
        print(f"  • R²: {best_reg[1]['r2']:.3f}")
        print(f"  • MAE: {best_reg[1]['mae']:.1f} points")

    # 最佳分类模型
    if results['classification']:
        best_cls = max(results['classification'].items(), key=lambda x: x[1]['auc'])
        print(f"\n最佳分类模型 ({best_cls[0]}):")
        print(f"  • AUC: {best_cls[1]['auc']:.3f}")
        print(f"  • 准确率: {best_cls[1]['accuracy']:.3f}")

    # 年龄分析
    print(f"\n年龄分析:")

    # 按年龄分组分析表现
    age_groups = {
        '<18': final_data[final_data['current_age'] < 18],
        '18-21': final_data[(final_data['current_age'] >= 18) & (final_data['current_age'] < 22)],
        '22-25': final_data[(final_data['current_age'] >= 22) & (final_data['current_age'] < 26)],
        '26+': final_data[final_data['current_age'] >= 26]
    }

    for group_name, group_data in age_groups.items():
        if len(group_data) > 0:
            print(f"  • {group_name} (n={len(group_data)}):")
            print(f"     平均分数: {group_data['total_points'].mean():.1f}")
            print(f"     奖牌率: {group_data['won_medal'].mean():.1%}")


def main():
    """主函数"""
    print("奥运会女子10米跳台机器学习分析")
    print("=" * 60)

    # 加载数据
    print("\n加载数据...")
    df = fetch_all_data()

    if df is None or df.empty:
        print("错误: 没有可用数据!")
        return

    print(f"✓ 加载成功! 总记录: {len(df)}")

    # 准备特征
    print("\n准备特征...")
    final_data = prepare_features(df)

    # 准备模型数据
    X, y_reg, y_cls, feature_names, final_data = prepare_model_data(final_data)

    # 训练和评估模型
    print("\n训练模型...")
    results, models, scaler = train_and_evaluate_models(X, y_reg, y_cls, feature_names)

    # 绘制特征重要性
    print("\n绘制特征重要性...")
    plot_feature_importance(models['regression'], feature_names, 'Regression')
    plot_feature_importance(models['classification'], feature_names, 'Classification')

    # 绘制年龄与成绩关系
    print("\n分析年龄与成绩关系...")
    plot_age_performance_relationship(final_data)

    # 绘制模型比较
    print("\n比较模型性能...")
    plot_model_comparison(results)

    # 导出结果
    print("\n导出结果...")
    export_results(results, final_data)

    # 打印总结
    print_summary(results, final_data)

    print("\n" + "=" * 60)
    print("分析完成!")
    print("=" * 60)


if __name__ == "__main__":
    main()