import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import xgboost as xgb
from sklearn.metrics import mean_absolute_error
import warnings
import os

warnings.filterwarnings('ignore')

# 设置图表样式
plt.rcParams['font.sans-serif'] = ['Arial', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False
sns.set_style("whitegrid")
plt.rcParams['figure.figsize'] = [12, 8]


class SingleCompetitionAnalyzer:
    def __init__(self, competition_data):
        """
        单场比赛稳定性分析器

        Parameters:
        competition_data: 单场比赛的5跳数据DataFrame
        """
        self.data = competition_data.copy()
        self.competition_name = competition_data['Event'].iloc[0]
        self.athlete = competition_data['Athlete'].iloc[0]

        # 确保数据按跳次排序
        self.data = self.data.sort_values('Dive_Number').reset_index(drop=True)
        print(f"Analyzing competition: {self.competition_name}")
        print(f"Athlete: {self.athlete}")
        print(f"Total dives: {len(self.data)}")

    def calculate_basic_stability(self):
        """计算基础稳定性指标"""
        scores = self.data['Dive_Points'].values
        difficulties = self.data['Difficulty_Degree'].values

        if len(scores) == 0:
            return {}

        metrics = {
            'competition': self.competition_name,
            'athlete': self.athlete,

            # 基本得分统计
            'total_score': np.sum(scores),
            'avg_score': np.mean(scores),
            'score_std': np.std(scores),
            'score_cv': (np.std(scores) / np.mean(scores)) * 100 if np.mean(scores) > 0 else 0,
            'score_range': np.max(scores) - np.min(scores),
            'max_score': np.max(scores),
            'min_score': np.min(scores),

            # 四分位统计
            'q1': np.percentile(scores, 25),
            'median': np.median(scores),
            'q3': np.percentile(scores, 75),
            'iqr': np.percentile(scores, 75) - np.percentile(scores, 25),

            # 难度信息
            'avg_difficulty': np.mean(difficulties),
            'total_difficulty': np.sum(difficulties),
            'max_difficulty': np.max(difficulties),
            'min_difficulty': np.min(difficulties),

            # 难度调整指标
            'adjusted_scores': scores / difficulties,
            'adjusted_avg': np.mean(scores / difficulties),
            'adjusted_std': np.std(scores / difficulties),
            'adjusted_cv': (np.std(scores / difficulties) / np.mean(scores / difficulties) * 100
                            if np.mean(scores / difficulties) > 0 else 0),
        }

        # 稳定性评级
        cv = metrics['score_cv']
        if cv < 8:
            metrics['stability_rating'] = 'Excellent'
            metrics['stability_score'] = 10
        elif cv < 12:
            metrics['stability_rating'] = 'Good'
            metrics['stability_score'] = 8
        elif cv < 18:
            metrics['stability_rating'] = 'Average'
            metrics['stability_score'] = 6
        elif cv < 25:
            metrics['stability_rating'] = 'Below Average'
            metrics['stability_score'] = 4
        else:
            metrics['stability_rating'] = 'Poor'
            metrics['stability_score'] = 2

        return metrics

    def analyze_temporal_pattern(self):
        """分析时序模式"""
        scores = self.data['Dive_Points'].values
        dive_numbers = self.data['Dive_Number'].values

        if len(scores) == 0:
            return {}

        # 计算趋势
        if len(scores) > 1:
            slope, intercept = np.polyfit(dive_numbers, scores, 1)
            trend = 'Improving' if slope > 0.5 else 'Declining' if slope < -0.5 else 'Stable'
        else:
            slope, intercept, trend = 0, 0, 'N/A'

        # 阶段分析
        if len(scores) >= 2:
            opening_stability = np.mean(scores[:2])
            closing_stability = np.mean(scores[-2:]) if len(scores) >= 4 else scores[-1]
        else:
            opening_stability = closing_stability = scores[0] if len(scores) > 0 else 0

        # 波动分析
        if len(scores) > 1:
            score_changes = np.diff(scores)
            max_increase = np.max(score_changes) if len(score_changes) > 0 else 0
            max_decrease = abs(np.min(score_changes)) if len(score_changes) > 0 else 0
            avg_change = np.mean(np.abs(score_changes)) if len(score_changes) > 0 else 0
        else:
            max_increase = max_decrease = avg_change = 0

        temporal_metrics = {
            'trend_slope': slope,
            'trend_intercept': intercept,
            'trend_direction': trend,
            'opening_stability': opening_stability,
            'closing_stability': closing_stability,
            'max_score_increase': max_increase,
            'max_score_decrease': max_decrease,
            'avg_score_change': avg_change,
            'score_changes': score_changes.tolist() if len(scores) > 1 else [],

            # 关键跳分析（通常第3跳是关键）
            'key_dive_performance': scores[2] if len(scores) > 2 else 0,
            'key_dive_vs_avg': scores[2] - np.mean(scores) if len(scores) > 2 else 0,

            # 首尾跳对比
            'first_last_difference': scores[-1] - scores[0] if len(scores) > 1 else 0,
        }

        return temporal_metrics

    def analyze_difficulty_consistency(self):
        """分析难度与表现的一致性"""
        scores = self.data['Dive_Points'].values
        difficulties = self.data['Difficulty_Degree'].values
        dive_codes = self.data['Dive_Code'].values

        if len(scores) < 2:
            return {}

        # 计算每难度单位的得分
        scores_per_difficulty = scores / difficulties

        # 难度-得分相关性
        if len(scores) > 1:
            difficulty_score_corr = np.corrcoef(difficulties, scores)[0, 1]
        else:
            difficulty_score_corr = 0

        # 分析不同难度段的表现
        high_difficulty_mask = difficulties > np.mean(difficulties)
        low_difficulty_mask = difficulties <= np.mean(difficulties)

        if np.sum(high_difficulty_mask) > 0:
            high_diff_avg = np.mean(scores[high_difficulty_mask])
            high_diff_std = np.std(scores[high_difficulty_mask])
        else:
            high_diff_avg = high_diff_std = 0

        if np.sum(low_difficulty_mask) > 0:
            low_diff_avg = np.mean(scores[low_difficulty_mask])
            low_diff_std = np.std(scores[low_difficulty_mask])
        else:
            low_diff_avg = low_diff_std = 0

        # 找到最稳定和最不稳定的一跳
        most_consistent_dive = self._find_most_consistent_dive(scores, difficulties, dive_codes)
        least_consistent_dive = self._find_least_consistent_dive(scores, difficulties, dive_codes)

        difficulty_metrics = {
            'difficulty_score_correlation': difficulty_score_corr,
            'avg_score_per_difficulty': np.mean(scores_per_difficulty),
            'std_score_per_difficulty': np.std(scores_per_difficulty),

            'high_difficulty_avg': high_diff_avg,
            'low_difficulty_avg': low_diff_avg,
            'high_difficulty_std': high_diff_std,
            'low_difficulty_std': low_diff_std,
            'difficulty_consistency_gap': abs(high_diff_std - low_diff_std),

            # 难度策略评估
            'difficulty_strategy': self._evaluate_difficulty_strategy(difficulties, scores),

            # 最稳定/最不稳定动作
            'most_consistent_dive': most_consistent_dive,
            'least_consistent_dive': least_consistent_dive,

            # 难度效率（每难度单位得分）
            'difficulty_efficiency': np.mean(scores_per_difficulty),
            'difficulty_efficiency_std': np.std(scores_per_difficulty),
        }

        return difficulty_metrics

    def _evaluate_difficulty_strategy(self, difficulties, scores):
        """评估难度策略"""
        if len(difficulties) < 2:
            return "Insufficient data"

        # 检查难度安排模式
        diff_changes = np.diff(difficulties)
        increasing = np.all(diff_changes >= 0)
        decreasing = np.all(diff_changes <= 0)

        if increasing:
            return "Progressive difficulty increase (保守策略)"
        elif decreasing:
            return "Progressive difficulty decrease (冒险策略)"
        else:
            return "Variable difficulty strategy (混合策略)"

    def _find_most_consistent_dive(self, scores, difficulties, dive_codes):
        """找到最稳定的一跳（相对于难度期望）"""
        if len(scores) == 0:
            return None

        # 计算每跳的标准化残差（实际得分 vs 难度期望）
        expected_scores = difficulties * np.mean(scores / difficulties)
        residuals = scores - expected_scores
        if np.std(residuals) > 0:
            normalized_residuals = residuals / np.std(residuals)
        else:
            normalized_residuals = residuals

        # 最接近期望值的一跳
        most_consistent_idx = np.argmin(np.abs(normalized_residuals))

        return {
            'dive_number': most_consistent_idx + 1,
            'dive_code': dive_codes[most_consistent_idx],
            'difficulty': difficulties[most_consistent_idx],
            'score': scores[most_consistent_idx],
            'expected_score': expected_scores[most_consistent_idx],
            'residual': normalized_residuals[most_consistent_idx],
            'consistency_level': 'Most Consistent',
        }

    def _find_least_consistent_dive(self, scores, difficulties, dive_codes):
        """找到最不稳定的一跳"""
        if len(scores) == 0:
            return None

        expected_scores = difficulties * np.mean(scores / difficulties)
        residuals = scores - expected_scores
        if np.std(residuals) > 0:
            normalized_residuals = residuals / np.std(residuals)
        else:
            normalized_residuals = residuals

        # 偏离期望最远的一跳
        least_consistent_idx = np.argmax(np.abs(normalized_residuals))

        return {
            'dive_number': least_consistent_idx + 1,
            'dive_code': dive_codes[least_consistent_idx],
            'difficulty': difficulties[least_consistent_idx],
            'score': scores[least_consistent_idx],
            'expected_score': expected_scores[least_consistent_idx],
            'residual': normalized_residuals[least_consistent_idx],
            'deviation_type': 'Overperformance' if normalized_residuals[
                                                       least_consistent_idx] > 0 else 'Underperformance',
            'consistency_level': 'Least Consistent',
        }

    def analyze_judge_consistency(self):
        """分析裁判一致性"""
        judge_cols = ['Judge1', 'Judge2', 'Judge3', 'Judge4', 'Judge5', 'Judge6', 'Judge7']

        if not all(col in self.data.columns for col in judge_cols):
            return None

        judge_data = self.data[judge_cols].values
        judge_consistency = {
            'avg_judge_score_per_dive': np.mean(judge_data, axis=1).tolist(),
            'judge_std_per_dive': np.std(judge_data, axis=1).tolist(),
            'avg_judge_std': np.mean(np.std(judge_data, axis=1)),
            'max_judge_std': np.max(np.std(judge_data, axis=1)),
            'min_judge_std': np.min(np.std(judge_data, axis=1)),

            # 裁判整体表现
            'overall_judge_avg': np.mean(judge_data),
            'overall_judge_std': np.std(judge_data),

            # 最一致/最不一致的裁判
            'judge_means': np.mean(judge_data, axis=0).tolist(),
            'judge_stds': np.std(judge_data, axis=0).tolist(),
        }

        # 找到最严格和最宽松的裁判
        judge_means = np.mean(judge_data, axis=0)
        strictest_idx = np.argmin(judge_means)
        most_lenient_idx = np.argmax(judge_means)

        judge_consistency['strictest_judge'] = {
            'judge_number': strictest_idx + 1,
            'average_score': judge_means[strictest_idx],
        }

        judge_consistency['most_lenient_judge'] = {
            'judge_number': most_lenient_idx + 1,
            'average_score': judge_means[most_lenient_idx],
        }

        return judge_consistency

    def build_xgboost_model(self):
        """构建XGBoost模型进行异常检测和预测"""
        if len(self.data) < 3:
            print("Insufficient data for XGBoost modeling (need at least 3 dives)")
            return None

        # 准备特征：基于历史数据预测每一跳
        features = []
        targets = []

        for i in range(len(self.data)):
            if i == 0:
                continue  # 跳过第一跳，没有历史数据

            # 特征：前几跳的表现
            prev_scores = self.data.iloc[:i]['Dive_Points'].values
            prev_difficulties = self.data.iloc[:i]['Difficulty_Degree'].values

            feature_dict = {
                'dive_number': i + 1,
                'current_difficulty': self.data.iloc[i]['Difficulty_Degree'],

                # 历史表现统计
                'prev_avg_score': np.mean(prev_scores) if len(prev_scores) > 0 else 0,
                'prev_std_score': np.std(prev_scores) if len(prev_scores) > 0 else 0,
                'prev_trend': self._calculate_mini_trend(prev_scores),

                # 难度特征
                'difficulty_change': self.data.iloc[i]['Difficulty_Degree'] - self.data.iloc[i - 1][
                    'Difficulty_Degree'],
                'cumulative_difficulty': np.sum(prev_difficulties),

                # 比赛进程
                'progress_ratio': i / len(self.data),
                'is_final_dive': 1 if i == len(self.data) - 1 else 0,
            }

            # 如果有裁判数据，添加裁判一致性
            judge_cols = ['Judge1', 'Judge2', 'Judge3', 'Judge4', 'Judge5', 'Judge6', 'Judge7']
            if all(col in self.data.columns for col in judge_cols):
                prev_judge_stds = []
                for j in range(i):
                    prev_judges = self.data.iloc[j][judge_cols]
                    prev_judge_stds.append(prev_judges.std())
                feature_dict['prev_judge_consistency'] = np.mean(prev_judge_stds) if prev_judge_stds else 0

            features.append(feature_dict)
            targets.append(self.data.iloc[i]['Dive_Points'])

        if len(features) < 2:
            print("Insufficient features for XGBoost modeling")
            return None

        # 转换为DataFrame
        X = pd.DataFrame(features)
        y = np.array(targets)

        # 训练XGBoost模型
        model = xgb.XGBRegressor(
            n_estimators=100,
            max_depth=3,
            learning_rate=0.1,
            random_state=42,
            objective='reg:squarederror'
        )

        # 由于数据少，使用留一法交叉验证
        predictions = []
        residuals = []

        for i in range(len(X)):
            # 留一法
            train_idx = [j for j in range(len(X)) if j != i]
            test_idx = [i]

            X_train, X_test = X.iloc[train_idx], X.iloc[test_idx]
            y_train, y_test = y[train_idx], y[test_idx]

            model.fit(X_train, y_train)
            pred = model.predict(X_test)[0]

            predictions.append(pred)
            residuals.append(y_test[0] - pred)

        # 计算预测误差
        predictions = np.array(predictions)
        residuals = np.array(residuals)
        if np.std(residuals) > 0:
            std_residuals = residuals / np.std(residuals)
        else:
            std_residuals = residuals

        # 识别异常跳（1.5个标准差）
        anomalies = np.abs(std_residuals) > 1.5

        xgboost_results = {
            'predictions': predictions.tolist(),
            'actual_scores': y.tolist(),
            'residuals': residuals.tolist(),
            'std_residuals': std_residuals.tolist(),
            'anomalies': anomalies.tolist(),
            'mae': mean_absolute_error(y, predictions),
            'rmse': np.sqrt(np.mean(np.square(residuals))),

            'anomalous_dives': [
                {
                    'dive_number': i + 2,  # +1 for 0-index, +1 for skipping first dive
                    'actual_score': y[i],
                    'predicted_score': predictions[i],
                    'residual': residuals[i],
                    'std_residual': std_residuals[i],
                    'type': 'Overperformance' if residuals[i] > 0 else 'Underperformance',
                }
                for i in range(len(anomalies)) if anomalies[i]
            ],
        }

        return xgboost_results

    def _calculate_mini_trend(self, scores):
        """计算微型趋势"""
        if len(scores) < 2:
            return 0
        x = np.arange(len(scores))
        slope = np.polyfit(x, scores, 1)[0]
        return slope

    def create_visualizations(self):
        """创建综合可视化图表"""
        fig = plt.figure(figsize=(20, 15))

        # 创建子图布局
        gs = fig.add_gridspec(3, 3, hspace=0.3, wspace=0.3)

        # 1. 得分趋势图
        ax1 = fig.add_subplot(gs[0, 0])
        self._plot_score_trend(ax1)

        # 2. 难度-得分散点图
        ax2 = fig.add_subplot(gs[0, 1])
        self._plot_difficulty_score_scatter(ax2)

        # 3. 稳定性指标条形图（替代雷达图）
        ax3 = fig.add_subplot(gs[0, 2])
        self._plot_stability_barchart(ax3)

        # 4. 得分分布箱线图
        ax4 = fig.add_subplot(gs[1, 0])
        self._plot_score_distribution(ax4)

        # 5. 时序波动图
        ax5 = fig.add_subplot(gs[1, 1])
        self._plot_temporal_fluctuation(ax5)

        # 6. 裁判一致性分析
        ax6 = fig.add_subplot(gs[1, 2])
        self._plot_judge_consistency(ax6)

        # 7. XGBoost预测对比图
        ax7 = fig.add_subplot(gs[2, 0])
        self._plot_xgboost_predictions(ax7)

        # 8. 难度效率图
        ax8 = fig.add_subplot(gs[2, 1])
        self._plot_difficulty_efficiency(ax8)

        # 9. 综合指标展示
        ax9 = fig.add_subplot(gs[2, 2])
        self._plot_summary_metrics(ax9)

        plt.suptitle(
            f'Competition Analysis: {self.competition_name} - {self.athlete} (Age: {self.data["Age"].iloc[0]})',
            fontsize=16, fontweight='bold', y=0.98)

        return fig

    def _plot_score_trend(self, ax):
        """绘制得分趋势图"""
        dive_numbers = self.data['Dive_Number'].values
        scores = self.data['Dive_Points'].values
        difficulties = self.data['Difficulty_Degree'].values
        dive_codes = self.data['Dive_Code'].values

        # 绘制得分线
        line = ax.plot(dive_numbers, scores, 'o-', linewidth=3, markersize=10,
                       color='royalblue', label='Score')

        # 添加难度和动作代码标注
        for i, (dive_num, score, diff, code) in enumerate(zip(dive_numbers, scores, difficulties, dive_codes)):
            ax.annotate(f'{code}\n(D{diff})', (dive_num, score),
                        textcoords="offset points", xytext=(0, 10),
                        ha='center', fontsize=9, color='darkred')

        # 添加平均线
        avg_score = np.mean(scores)
        ax.axhline(y=avg_score, color='red', linestyle='--',
                   alpha=0.7, label=f'Avg: {avg_score:.1f}')

        # 添加±1标准差范围
        std_score = np.std(scores)
        ax.fill_between(dive_numbers,
                        avg_score - std_score,
                        avg_score + std_score,
                        alpha=0.2, color='gray', label='±1 Std Dev')

        ax.set_xlabel('Dive Number')
        ax.set_ylabel('Score')
        ax.set_title('Score Trend During Competition')
        ax.legend(loc='best')
        ax.grid(True, alpha=0.3)
        ax.set_xticks(dive_numbers)
        ax.set_xlim(0.5, len(dive_numbers) + 0.5)

    def _plot_difficulty_score_scatter(self, ax):
        """绘制难度-得分散点图"""
        scores = self.data['Dive_Points'].values
        difficulties = self.data['Difficulty_Degree'].values
        dive_numbers = self.data['Dive_Number'].values
        dive_codes = self.data['Dive_Code'].values

        # 散点图
        scatter = ax.scatter(difficulties, scores, c=dive_numbers,
                             cmap='viridis', s=150, alpha=0.8, edgecolors='black')

        # 添加回归线
        if len(scores) > 1:
            z = np.polyfit(difficulties, scores, 1)
            p = np.poly1d(z)
            x_range = np.linspace(min(difficulties) - 0.1, max(difficulties) + 0.1, 100)
            ax.plot(x_range, p(x_range), 'r--', alpha=0.7,
                    label=f'Fit: y={z[0]:.2f}x+{z[1]:.2f}')

        # 标注每一点
        for i, (diff, score, dive_num, code) in enumerate(zip(difficulties, scores, dive_numbers, dive_codes)):
            ax.annotate(f'#{dive_num}: {code}', (diff, score),
                        textcoords="offset points", xytext=(0, 10),
                        ha='center', fontsize=9)

        ax.set_xlabel('Difficulty Degree')
        ax.set_ylabel('Score')
        ax.set_title('Difficulty vs Score Relationship')
        ax.legend(loc='best')
        ax.grid(True, alpha=0.3)

        # 添加颜色条
        plt.colorbar(scatter, ax=ax, label='Dive Number')

    def _plot_stability_barchart(self, ax):
        """绘制稳定性指标条形图（替代雷达图）"""
        metrics = self.calculate_basic_stability()
        temporal_metrics = self.analyze_temporal_pattern()

        if not metrics:
            ax.text(0.5, 0.5, 'No data for stability analysis',
                    ha='center', va='center', transform=ax.transAxes, fontsize=12)
            ax.set_title('Stability Analysis')
            return

        # 创建稳定性指标
        categories = ['Total Score', 'Avg Score', 'Score STD', 'CV (%)', 'Stability Score']

        # 计算归一化值（0-1）
        total_norm = min(metrics.get('total_score', 0) / 500, 1)  # 假设500分为满分
        avg_norm = min(metrics.get('avg_score', 0) / 100, 1)  # 假设100分为满分
        std_norm = 1 - min(metrics.get('score_std', 0) / 30, 1)  # STD越小越好
        cv_norm = 1 - min(metrics.get('score_cv', 0) / 30, 1)  # CV越小越好
        stability_norm = metrics.get('stability_score', 0) / 10  # 0-10分制

        values = [total_norm, avg_norm, std_norm, cv_norm, stability_norm]

        # 确保所有值都在0-1范围内
        values = [max(0, min(1, v)) for v in values]

        colors = plt.cm.RdYlBu(np.linspace(0.2, 0.8, len(categories)))
        bars = ax.barh(categories, values, color=colors, alpha=0.7, edgecolor='black')

        # 添加原始值标签
        raw_values = [
            f"{metrics.get('total_score', 0):.1f}",
            f"{metrics.get('avg_score', 0):.1f}",
            f"{metrics.get('score_std', 0):.1f}",
            f"{metrics.get('score_cv', 0):.1f}%",
            f"{metrics.get('stability_score', 0)}/10"
        ]

        for bar, value, raw_value in zip(bars, values, raw_values):
            ax.text(value + 0.02, bar.get_y() + bar.get_height() / 2,
                    f'{raw_value} (norm: {value:.2f})', ha='left', va='center', fontsize=9)

        ax.set_xlim(0, 1.2)
        ax.set_xlabel('Normalized Value (0-1)')
        ax.set_title('Stability Metrics Overview')
        ax.grid(True, alpha=0.3, axis='x')

    def _plot_score_distribution(self, ax):
        """绘制得分分布箱线图"""
        scores = self.data['Dive_Points'].values

        # 箱线图
        box = ax.boxplot(scores, patch_artist=True, widths=0.6)
        box['boxes'][0].set_facecolor('lightblue')
        box['boxes'][0].set_alpha(0.7)

        # 添加散点显示每跳得分
        for i, score in enumerate(scores):
            ax.scatter(1, score, color='red', s=100, alpha=0.7,
                       edgecolors='black', zorder=3)
            ax.annotate(f'#{i + 1}: {score:.1f}', (1, score), textcoords="offset points",
                        xytext=(5, 0), ha='left', fontsize=9, fontweight='bold')

        # 添加统计线
        ax.axhline(y=np.mean(scores), color='red', linestyle='--', alpha=0.7,
                   label=f'Mean: {np.mean(scores):.1f}')
        ax.axhline(y=np.median(scores), color='green', linestyle=':', alpha=0.7,
                   label=f'Median: {np.median(scores):.1f}')

        ax.set_ylabel('Score')
        ax.set_title('Score Distribution Analysis')
        ax.set_xticklabels(['All Dives'])
        ax.legend(loc='best')
        ax.grid(True, alpha=0.3, axis='y')

    def _plot_temporal_fluctuation(self, ax):
        """绘制时序波动图"""
        scores = self.data['Dive_Points'].values

        if len(scores) > 1:
            changes = np.diff(scores)
            dive_pairs = [f'{i + 1}→{i + 2}' for i in range(len(changes))]

            # 条形图显示变化
            colors = ['green' if c > 0 else 'red' for c in changes]
            bars = ax.bar(dive_pairs, changes, color=colors, alpha=0.7, edgecolor='black')

            # 添加数值
            for bar, change in zip(bars, changes):
                height = bar.get_height()
                va = 'bottom' if height > 0 else 'top'
                y_offset = 0.5 if height > 0 else -0.5
                ax.text(bar.get_x() + bar.get_width() / 2., height + y_offset,
                        f'{change:+.1f}', ha='center', va=va, fontsize=10, fontweight='bold')

            ax.axhline(y=0, color='black', linestyle='-', alpha=0.3, linewidth=2)
            ax.set_xlabel('Dive Transitions')
            ax.set_ylabel('Score Change')
            ax.set_title('Score Fluctuation Between Dives')
            ax.grid(True, alpha=0.3, axis='y')

            # 计算平均波动
            avg_fluctuation = np.mean(np.abs(changes))
            ax.text(0.02, 0.98, f'Avg Change: {avg_fluctuation:.2f}',
                    transform=ax.transAxes, fontsize=10,
                    verticalalignment='top',
                    bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
        else:
            ax.text(0.5, 0.5, 'Insufficient data\nfor fluctuation analysis',
                    ha='center', va='center', transform=ax.transAxes, fontsize=12)
            ax.set_title('Score Fluctuation')

    def _plot_judge_consistency(self, ax):
        """绘制裁判一致性分析图"""
        judge_consistency = self.analyze_judge_consistency()

        if judge_consistency is None:
            ax.text(0.5, 0.5, 'No judge data available',
                    ha='center', va='center', transform=ax.transAxes, fontsize=12)
            ax.set_title('Judge Consistency Analysis')
            return

        judge_stds = judge_consistency['judge_std_per_dive']
        dive_numbers = self.data['Dive_Number'].values

        # 绘制每跳的裁判标准差
        bars = ax.bar(dive_numbers, judge_stds, color='lightcoral', alpha=0.7, edgecolor='darkred')

        # 添加平均线
        avg_std = judge_consistency['avg_judge_std']
        ax.axhline(y=avg_std, color='red', linestyle='--',
                   label=f'Avg Std: {avg_std:.3f}')

        # 标注每跳
        for bar, dive_num, std in zip(bars, dive_numbers, judge_stds):
            ax.text(bar.get_x() + bar.get_width() / 2., bar.get_height() + 0.01,
                    f'{std:.3f}', ha='center', va='bottom', fontsize=9)

        ax.set_xlabel('Dive Number')
        ax.set_ylabel('Judge Standard Deviation')
        ax.set_title('Judge Consistency per Dive')
        ax.legend(loc='best')
        ax.set_xticks(dive_numbers)
        ax.grid(True, alpha=0.3, axis='y')

    def _plot_xgboost_predictions(self, ax):
        """绘制XGBoost预测对比图"""
        xgboost_results = self.build_xgboost_model()

        if xgboost_results and len(xgboost_results['actual_scores']) > 0:
            actual = xgboost_results['actual_scores']
            predicted = xgboost_results['predictions']
            anomalies = xgboost_results['anomalies']

            dive_numbers = list(range(2, len(actual) + 2))  # 从第2跳开始

            # 绘制实际值和预测值
            ax.scatter(dive_numbers, actual, color='blue', s=100,
                       label='Actual', alpha=0.8, edgecolors='black', zorder=3)
            ax.scatter(dive_numbers, predicted, color='red', s=100,
                       marker='s', label='Predicted', alpha=0.8, edgecolors='black', zorder=3)

            # 连接线显示误差
            for i, (act, pred) in enumerate(zip(actual, predicted)):
                color = 'green' if abs(act - pred) < 3 else 'orange' if abs(act - pred) < 5 else 'red'
                ax.plot([dive_numbers[i], dive_numbers[i]], [act, pred],
                        color=color, alpha=0.5, linewidth=2)

            # 高亮异常点
            if any(anomalies):
                anomaly_indices = np.where(anomalies)[0]
                anomaly_dives = [dive_numbers[i] for i in anomaly_indices]
                anomaly_actual = [actual[i] for i in anomaly_indices]

                ax.scatter(anomaly_dives, anomaly_actual, color='gold',
                           s=200, marker='*', label='Anomaly', edgecolors='black', zorder=5)

            ax.set_xlabel('Dive Number')
            ax.set_ylabel('Score')
            ax.set_title(f'XGBoost Predictions (MAE: {xgboost_results["mae"]:.2f})')
            ax.legend(loc='best')
            ax.grid(True, alpha=0.3)
            ax.set_xticks(dive_numbers)
        else:
            ax.text(0.5, 0.5, 'XGBoost analysis\nrequires at least 3 dives',
                    ha='center', va='center', transform=ax.transAxes, fontsize=12)
            ax.set_title('XGBoost Prediction Analysis')

    def _plot_difficulty_efficiency(self, ax):
        """绘制难度效率图"""
        scores = self.data['Dive_Points'].values
        difficulties = self.data['Difficulty_Degree'].values
        dive_codes = self.data['Dive_Code'].values

        # 计算每难度单位得分
        efficiency_scores = scores / difficulties

        # 绘制条形图
        x_pos = np.arange(len(dive_codes))
        bars = ax.bar(x_pos, efficiency_scores, color='lightgreen', alpha=0.7, edgecolor='darkgreen')

        # 添加平均线
        avg_efficiency = np.mean(efficiency_scores)
        ax.axhline(y=avg_efficiency, color='green', linestyle='--',
                   label=f'Avg: {avg_efficiency:.2f}')

        # 标注每跳
        for i, (bar, code, eff) in enumerate(zip(bars, dive_codes, efficiency_scores)):
            ax.text(bar.get_x() + bar.get_width() / 2., bar.get_height() + 0.1,
                    f'{eff:.2f}', ha='center', va='bottom', fontsize=9)
            ax.text(bar.get_x() + bar.get_width() / 2., -0.5,
                    code, ha='center', va='top', fontsize=9, rotation=45)

        ax.set_xlabel('Dive Code')
        ax.set_ylabel('Score per Difficulty Unit')
        ax.set_title('Dive Efficiency Analysis')
        ax.legend(loc='best')
        ax.set_xticks([])  # 移除x轴刻度，使用下面的标注
        ax.grid(True, alpha=0.3, axis='y')

    def _plot_summary_metrics(self, ax):
        """绘制综合指标展示"""
        # 计算所有指标
        basic_metrics = self.calculate_basic_stability()
        temporal_metrics = self.analyze_temporal_pattern()
        difficulty_metrics = self.analyze_difficulty_consistency()
        judge_consistency = self.analyze_judge_consistency()

        # 准备展示文本
        age = self.data['Age'].iloc[0] if 'Age' in self.data.columns else 'N/A'

        summary_text = f"""
        COMPETITION ANALYSIS SUMMARY
        ============================
        Competition: {basic_metrics['competition']}
        Athlete: {basic_metrics['athlete']} (Age: {age})

        SCORE ANALYSIS
        --------------
        Total Score: {basic_metrics['total_score']:.1f}
        Average Score: {basic_metrics['avg_score']:.1f}
        Score Range: {basic_metrics['min_score']:.1f} - {basic_metrics['max_score']:.1f}
        Score STD: {basic_metrics['score_std']:.1f}
        CV: {basic_metrics['score_cv']:.1f}%
        Stability: {basic_metrics['stability_rating']} ({basic_metrics['stability_score']}/10)

        TEMPORAL PATTERN
        -----------------
        Trend: {temporal_metrics['trend_direction']}
        Opening (Dives 1-2): {temporal_metrics['opening_stability']:.1f}
        Key Dive (#3): {temporal_metrics['key_dive_performance']:.1f}
        Closing (Last 2): {temporal_metrics['closing_stability']:.1f}
        Avg Change: {temporal_metrics['avg_score_change']:.1f}
        """

        if difficulty_metrics:
            summary_text += f"""
        DIFFICULTY CONSISTENCY
        -----------------------
        Diff-Score Correlation: {difficulty_metrics.get('difficulty_score_correlation', 0):.3f}
        Avg Score/Difficulty: {difficulty_metrics.get('avg_score_per_difficulty', 0):.2f}
        Strategy: {difficulty_metrics.get('difficulty_strategy', 'N/A')}
        """

        if judge_consistency:
            summary_text += f"""
        JUDGE CONSISTENCY
        ------------------
        Avg Judge STD: {judge_consistency['avg_judge_std']:.3f}
        Most Consistent Dive: Min STD {judge_consistency['min_judge_std']:.3f}
        Least Consistent Dive: Max STD {judge_consistency['max_judge_std']:.3f}
        """

        # 显示文本
        ax.text(0.02, 0.98, summary_text, transform=ax.transAxes,
                fontsize=8.5, verticalalignment='top', fontfamily='monospace',
                bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.3))

        ax.axis('off')
        ax.set_title('Comprehensive Analysis Summary', fontsize=12, fontweight='bold')


def analyze_2019_world_series(df):
    """
    专门分析2019年世界系列赛（精确匹配'2019_world_series'，不包括'2019_world_series1'）
    """
    print("=" * 80)
    print("ANALYSIS OF 2019 WORLD SERIES - CHEN YUXI")
    print("=" * 80)

    # 精确筛选2019_world_series（不包括2019_world_series1）
    # 使用精确字符串匹配
    competition_mask = df['Event'] == '2019_world_series'
    competition_data = df[competition_mask].copy()

    if len(competition_data) == 0:
        print("Error: No data found for '2019_world_series'")
        print("\nAvailable competitions:")
        print(df['Event'].unique())
        return None

    print(f"Found {len(competition_data)} dives for 2019 World Series")
    print("\nDive Details:")
    print("-" * 60)
    print(competition_data[['Event', 'Dive_Number', 'Dive_Code', 'Difficulty_Degree', 'Dive_Points']].to_string(
        index=False))

    # 初始化分析器
    analyzer = SingleCompetitionAnalyzer(competition_data)

    # 计算各项指标
    print("\n" + "=" * 80)
    print("1. CALCULATING BASIC STABILITY METRICS")
    print("=" * 80)
    basic_metrics = analyzer.calculate_basic_stability()

    print("\nBasic Stability Metrics:")
    print("-" * 40)
    for key, value in basic_metrics.items():
        if isinstance(value, (int, float, np.integer, np.floating)):
            if 'cv' in key.lower() or 'corr' in key.lower():
                print(f"{key:25s}: {value:.3f}")
            elif 'score' in key.lower():
                print(f"{key:25s}: {value:.1f}")
            else:
                print(f"{key:25s}: {value:.2f}")
        else:
            print(f"{key:25s}: {value}")

    print("\n" + "=" * 80)
    print("2. ANALYZING TEMPORAL PATTERNS")
    print("=" * 80)
    temporal_metrics = analyzer.analyze_temporal_pattern()

    print("\nTemporal Pattern Analysis:")
    print("-" * 40)
    for key, value in temporal_metrics.items():
        if isinstance(value, (int, float, np.integer, np.floating)):
            if 'slope' in key.lower() or 'intercept' in key.lower():
                print(f"{key:25s}: {value:.3f}")
            else:
                print(f"{key:25s}: {value:.1f}")
        elif isinstance(value, list):
            if len(value) > 0:
                print(f"{key:25s}: {value}")
        else:
            print(f"{key:25s}: {value}")

    print("\n" + "=" * 80)
    print("3. ANALYZING DIFFICULTY CONSISTENCY")
    print("=" * 80)
    difficulty_metrics = analyzer.analyze_difficulty_consistency()

    if difficulty_metrics:
        print("\nDifficulty Consistency Analysis:")
        print("-" * 40)
        for key, value in difficulty_metrics.items():
            if key in ['most_consistent_dive', 'least_consistent_dive']:
                print(f"\n{key}:")
                if value:
                    for sub_key, sub_value in value.items():
                        if isinstance(sub_value, (int, float, np.integer, np.floating)):
                            print(f"  {sub_key:20s}: {sub_value:.3f}")
                        else:
                            print(f"  {sub_key:20s}: {sub_value}")
            elif isinstance(value, (int, float, np.integer, np.floating)):
                if 'correlation' in key.lower():
                    print(f"{key:30s}: {value:.3f}")
                else:
                    print(f"{key:30s}: {value:.2f}")
            else:
                print(f"{key:30s}: {value}")

    print("\n" + "=" * 80)
    print("4. ANALYZING JUDGE CONSISTENCY")
    print("=" * 80)
    judge_metrics = analyzer.analyze_judge_consistency()

    if judge_metrics:
        print("\nJudge Consistency Analysis:")
        print("-" * 40)
        important_judge_metrics = ['avg_judge_std', 'max_judge_std', 'min_judge_std',
                                   'strictest_judge', 'most_lenient_judge']
        for key in important_judge_metrics:
            if key in judge_metrics:
                value = judge_metrics[key]
                if isinstance(value, dict):
                    print(f"{key}:")
                    for sub_key, sub_value in value.items():
                        if isinstance(sub_value, (int, float, np.integer, np.floating)):
                            print(f"  {sub_key:20s}: {sub_value:.3f}")
                        else:
                            print(f"  {sub_key:20s}: {sub_value}")
                elif isinstance(value, (int, float, np.integer, np.floating)):
                    print(f"{key:25s}: {value:.3f}")
                else:
                    print(f"{key:25s}: {value}")

    print("\n" + "=" * 80)
    print("5. XGBOOST ANOMALY DETECTION")
    print("=" * 80)
    xgboost_results = analyzer.build_xgboost_model()

    if xgboost_results:
        print(f"\nXGBoost Model Performance:")
        print(f"  MAE: {xgboost_results['mae']:.2f}")
        print(f"  RMSE: {xgboost_results['rmse']:.2f}")

        if xgboost_results['anomalous_dives']:
            print(f"\nAnomalous Dives Detected:")
            for anomaly in xgboost_results['anomalous_dives']:
                print(f"  Dive #{anomaly['dive_number']}: {anomaly['type']} "
                      f"(Actual: {anomaly['actual_score']:.1f}, "
                      f"Predicted: {anomaly['predicted_score']:.1f}, "
                      f"Residual: {anomaly['residual']:.1f})")
        else:
            print("\nNo anomalous dives detected (all within normal range)")
    else:
        print("\nXGBoost analysis not possible with current data")

    # 创建可视化
    print("\n" + "=" * 80)
    print("6. CREATING COMPREHENSIVE VISUALIZATION")
    print("=" * 80)

    fig = analyzer.create_visualizations()

    # 保存图表
    output_filename = "2019_world_series_chen_yuxi_analysis.png"
    fig.savefig(output_filename, dpi=300, bbox_inches='tight')
    print(f"\nVisualization saved to: {output_filename}")

    # 显示图表
    plt.show()

    # 生成详细报告
    print("\n" + "=" * 80)
    print("7. GENERATING DETAILED ANALYSIS REPORT")
    print("=" * 80)

    # 关键发现总结
    print("\nKEY FINDINGS:")
    print("-" * 40)

    # 稳定性评估
    cv = basic_metrics['score_cv']
    if cv < 10:
        stability_assessment = "EXCELLENT stability - very consistent performance"
    elif cv < 15:
        stability_assessment = "GOOD stability - relatively consistent"
    elif cv < 20:
        stability_assessment = "AVERAGE stability - some variability"
    else:
        stability_assessment = "BELOW AVERAGE stability - high variability"

    print(f"1. Stability Assessment: {stability_assessment}")
    print(f"   • Coefficient of Variation: {cv:.1f}%")
    print(f"   • Score Range: {basic_metrics['min_score']:.1f} - {basic_metrics['max_score']:.1f}")
    print(f"   • Standard Deviation: {basic_metrics['score_std']:.1f}")
    print(f"   • Age at competition: {competition_data['Age'].iloc[0]} years old")

    # 趋势分析
    trend = temporal_metrics['trend_direction']
    if trend == 'Improving':
        trend_assessment = "Performance improved throughout the competition"
    elif trend == 'Declining':
        trend_assessment = "Performance declined throughout the competition"
    else:
        trend_assessment = "Performance remained stable throughout the competition"

    print(f"\n2. Temporal Pattern: {trend_assessment}")
    print(f"   • Trend Direction: {trend}")
    print(f"   • Opening Stability: {temporal_metrics['opening_stability']:.1f}")
    print(f"   • Key Dive Performance: {temporal_metrics['key_dive_performance']:.1f}")
    print(f"   • Closing Stability: {temporal_metrics['closing_stability']:.1f}")
    print(f"   • Average Score Change: {temporal_metrics['avg_score_change']:.1f}")

    # 难度一致性
    if difficulty_metrics:
        diff_corr = difficulty_metrics['difficulty_score_correlation']
        if diff_corr > 0.3:
            diff_assessment = "Strong positive correlation - higher difficulty leads to higher scores"
        elif diff_corr > 0:
            diff_assessment = "Weak positive correlation"
        elif diff_corr < -0.3:
            diff_assessment = "Strong negative correlation - higher difficulty leads to lower scores"
        elif diff_corr < 0:
            diff_assessment = "Weak negative correlation"
        else:
            diff_assessment = "No clear correlation between difficulty and score"

        print(f"\n3. Difficulty Consistency: {diff_assessment}")
        print(f"   • Difficulty-Score Correlation: {diff_corr:.3f}")
        print(f"   • Strategy: {difficulty_metrics['difficulty_strategy']}")

        # 最稳定和最不稳定跳
        if 'most_consistent_dive' in difficulty_metrics and difficulty_metrics['most_consistent_dive']:
            mc = difficulty_metrics['most_consistent_dive']
            print(f"   • Most Consistent Dive: #{mc['dive_number']} {mc['dive_code']} "
                  f"(Score: {mc['score']:.1f}, Expected: {mc['expected_score']:.1f})")

        if 'least_consistent_dive' in difficulty_metrics and difficulty_metrics['least_consistent_dive']:
            lc = difficulty_metrics['least_consistent_dive']
            print(f"   • Least Consistent Dive: #{lc['dive_number']} {lc['dive_code']} "
                  f"(Score: {lc['score']:.1f}, Expected: {lc['expected_score']:.1f}, "
                  f"Type: {lc['deviation_type']})")

    # 裁判一致性
    if judge_metrics:
        avg_std = judge_metrics['avg_judge_std']
        if avg_std < 0.3:
            judge_assessment = "Excellent judge consistency"
        elif avg_std < 0.5:
            judge_assessment = "Good judge consistency"
        elif avg_std < 0.7:
            judge_assessment = "Average judge consistency"
        else:
            judge_assessment = "Poor judge consistency - high variability in scoring"

        print(f"\n4. Judge Consistency: {judge_assessment}")
        print(f"   • Average Judge STD: {avg_std:.3f}")
        print(f"   • Most Consistent Dive STD: {judge_metrics['min_judge_std']:.3f}")
        print(f"   • Least Consistent Dive STD: {judge_metrics['max_judge_std']:.3f}")

    # 特别关注207C动作
    print("\n" + "=" * 80)
    print("SPECIAL FOCUS: 207C ACTION PERFORMANCE")
    print("=" * 80)

    # 查找207C动作
    dive_207c = competition_data[competition_data['Dive_Code'] == '207C']
    if len(dive_207c) > 0:
        print(f"\n207C Action Details:")
        print("-" * 40)
        for _, row in dive_207c.iterrows():
            print(f"  • Competition: {row['Event']}")
            print(f"  • Dive Number: {row['Dive_Number']}")
            print(f"  • Difficulty: {row['Difficulty_Degree']}")
            print(f"  • Score: {row['Dive_Points']:.1f}")
            print(f"  • Judges: {row['Judge1']}, {row['Judge2']}, {row['Judge3']}, "
                  f"{row['Judge4']}, {row['Judge5']}, {row['Judge6']}, {row['Judge7']}")

            # 分析207C的得分情况
            score = row['Dive_Points']
            if score < 60:
                assessment = "POOR performance - significant issues"
            elif score < 70:
                assessment = "BELOW AVERAGE performance"
            elif score < 80:
                assessment = "AVERAGE performance"
            elif score < 90:
                assessment = "GOOD performance"
            else:
                assessment = "EXCELLENT performance"

            print(f"  • Performance Assessment: {assessment}")

            # 与平均分比较
            avg_score = basic_metrics['avg_score']
            diff_from_avg = score - avg_score
            if diff_from_avg < -5:
                comparison = "Significantly below competition average"
            elif diff_from_avg < 0:
                comparison = "Slightly below competition average"
            elif diff_from_avg > 5:
                comparison = "Significantly above competition average"
            else:
                comparison = "Close to competition average"

            print(f"  • Comparison to Avg: {comparison} (diff: {diff_from_avg:+.1f})")
    else:
        print("\nNo 207C action found in this competition data")

    # 训练建议
    print("\n" + "=" * 80)
    print("TRAINING RECOMMENDATIONS:")
    print("=" * 80)

    recommendations = []

    # 基于稳定性
    if cv > 15:
        recommendations.append("Focus on consistency training for high-variability dives")

    # 基于年龄（年轻运动员）
    age = competition_data['Age'].iloc[0]
    if age <= 14:
        recommendations.append("Young athlete - focus on fundamental technique development")

    # 基于趋势
    if trend == 'Declining':
        recommendations.append("Work on maintaining performance throughout competition")
    elif trend == 'Improving':
        recommendations.append("Good competitive adaptation - maintain this pattern")

    # 基于难度一致性
    if difficulty_metrics and difficulty_metrics.get('difficulty_score_correlation', 0) < 0:
        recommendations.append("Review high-difficulty dives - ensure technical execution matches difficulty level")

    # 基于异常检测
    if xgboost_results and xgboost_results['anomalous_dives']:
        for anomaly in xgboost_results['anomalous_dives']:
            if anomaly['type'] == 'Underperformance':
                recommendations.append(f"Analyze dive #{anomaly['dive_number']} for potential technical issues")
            elif anomaly['type'] == 'Overperformance':
                recommendations.append(f"Study dive #{anomaly['dive_number']} for best practice replication")

    # 特别针对207C的建议
    if len(dive_207c) > 0:
        score_207c = dive_207c['Dive_Points'].iloc[0]
        if score_207c < 70:
            recommendations.append("207C action needs significant improvement - focus on technique refinement")
        elif score_207c < 80:
            recommendations.append("207C action has room for improvement - work on consistency")

    if not recommendations:
        recommendations.append("Good overall performance for early career - continue current training regimen")

    for i, rec in enumerate(recommendations, 1):
        print(f"{i}. {rec}")

    print("\n" + "=" * 80)
    print("CONTEXTUAL ANALYSIS:")
    print("=" * 80)
    print(f"• This was an EARLY CAREER competition (Age: {age})")
    print(f"• World Series events are important development competitions")
    print(f"• Performance here sets the foundation for future success")
    print(f"• Compare with later competitions to track development progress")

    print("\n" + "=" * 80)

    return {
        'analyzer': analyzer,
        'basic_metrics': basic_metrics,
        'temporal_metrics': temporal_metrics,
        'difficulty_metrics': difficulty_metrics,
        'judge_metrics': judge_metrics,
        'xgboost_results': xgboost_results,
    }


# 主程序
if __name__ == "__main__":
    # 加载数据
    file_path = "Yuxi CHEN__data.xlsx"

    try:
        if not os.path.exists(file_path):
            print(f"Error: File '{file_path}' not found")
            print("Please ensure the Excel file is in the current directory")
            print("\nCurrent directory contents:")
            print(os.listdir('.'))
        else:
            print(f"Loading data from: {file_path}")
            df = pd.read_excel(file_path)

            # 专门分析2019年世界系列赛
            results = analyze_2019_world_series(df)

            if results:
                print("\nAnalysis completed successfully!")
                print(f"Check the generated visualization: 2019_world_series_chen_yuxi_analysis.png")

    except Exception as e:
        print(f"Error during analysis: {e}")
        import traceback

        traceback.print_exc()