import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime
import xgboost as xgb
from sklearn.model_selection import train_test_split, TimeSeriesSplit, cross_val_score
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import warnings
import os

warnings.filterwarnings('ignore')

# 设置图表样式
plt.rcParams['font.sans-serif'] = ['Arial', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False
sns.set_style("whitegrid")
plt.rcParams['figure.figsize'] = [12, 8]


# 1. 数据处理和准备
class Dive207CAnalyzer:
    def __init__(self, data_path=None, df=None):
        """
        Initialize 207C action analyzer

        Parameters:
        data_path: data file path
        df: loaded DataFrame
        """
        if df is not None:
            self.df = df
        elif data_path:
            self.df = pd.read_excel(data_path)
        else:
            raise ValueError("Must provide data path or DataFrame")

        # Data preprocessing
        self._prepare_data()

    def _prepare_data(self):
        """Data preprocessing"""
        # Ensure Date column (extract year from Event column)
        self.df['Year'] = self.df['Event'].str.extract(r'(\d{4})').astype(int)

        # Create Date column (assuming January 1st as base for each year)
        self.df['Date'] = pd.to_datetime(self.df['Year'].astype(str) + '-01-01')

        # Extract event type in English
        def extract_event_type(event):
            event_lower = str(event).lower()
            if 'olympic' in event_lower or 'tokyo' in event_lower or 'paris' in event_lower:
                return 'Olympic Games'
            elif 'world_championship' in event_lower or 'world_championships' in event_lower:
                return 'World Championships'
            elif 'world_cup' in event_lower or 'world_series' in event_lower:
                return 'World Cup/Series'
            else:
                return 'Other'

        self.df['Event_Type'] = self.df['Event'].apply(extract_event_type)

        # Filter 207C actions
        self.df_207c = self.df[self.df['Dive_Code'] == '207C'].copy()

        if len(self.df_207c) == 0:
            raise ValueError("No 207C action records found in data")

        print(f"Found {len(self.df_207c)} 207C action records")

    def calculate_stability_metrics(self):
        """Calculate stability metrics"""
        metrics = {}

        # Basic statistics
        metrics['Total Count'] = len(self.df_207c)
        metrics['Average Score'] = self.df_207c['Dive_Points'].mean()
        metrics['Highest Score'] = self.df_207c['Dive_Points'].max()
        metrics['Lowest Score'] = self.df_207c['Dive_Points'].min()
        metrics['Median Score'] = self.df_207c['Dive_Points'].median()
        metrics['Standard Deviation'] = self.df_207c['Dive_Points'].std()

        # Stability metrics
        metrics['Coefficient of Variation (%)'] = (metrics['Standard Deviation'] / metrics['Average Score']) * 100
        metrics['Score Range'] = metrics['Highest Score'] - metrics['Lowest Score']

        # Interquartile Range (IQR)
        q1 = self.df_207c['Dive_Points'].quantile(0.25)
        q3 = self.df_207c['Dive_Points'].quantile(0.75)
        metrics['IQR'] = q3 - q1

        # Stability rating (0-10 points, higher is more stable)
        cv = metrics['Coefficient of Variation (%)']
        if cv < 5:
            metrics['Stability Rating'] = 10
        elif cv < 10:
            metrics['Stability Rating'] = 9
        elif cv < 15:
            metrics['Stability Rating'] = 8
        elif cv < 20:
            metrics['Stability Rating'] = 7
        elif cv < 25:
            metrics['Stability Rating'] = 6
        else:
            metrics['Stability Rating'] = 5

        # Calculate by event type
        event_metrics = {}
        for event_type in self.df_207c['Event_Type'].unique():
            event_data = self.df_207c[self.df_207c['Event_Type'] == event_type]
            event_metrics[event_type] = {
                'Count': len(event_data),
                'Average Score': event_data['Dive_Points'].mean(),
                'Standard Deviation': event_data['Dive_Points'].std(),
                'Coefficient of Variation (%)': (event_data['Dive_Points'].std() / event_data[
                    'Dive_Points'].mean()) * 100 if event_data['Dive_Points'].mean() > 0 else 0
            }

        return metrics, event_metrics

    def prepare_features_for_prediction(self):
        """Prepare features for XGBoost prediction"""
        features_df = self.df_207c.copy()

        # Sort by time
        features_df = features_df.sort_values('Date').reset_index(drop=True)

        # Feature engineering
        X_list = []
        y_list = []

        for i in range(len(features_df)):
            if i < 3:  # Need at least 3 historical records
                continue

            # Target variable: current 207C score
            y = features_df.loc[i, 'Dive_Points']

            # Features: historical performance
            prev_data = features_df.iloc[max(0, i - 3):i]

            feature_dict = {
                'index': i,
                'Athlete': features_df.loc[i, 'Athlete'],
                'Event': features_df.loc[i, 'Event'],
                'Event_Type': features_df.loc[i, 'Event_Type'],
                'Year': features_df.loc[i, 'Year'],
                'Age': features_df.loc[i, 'Age'],

                # Historical performance features
                'prev_avg_score': prev_data['Dive_Points'].mean(),
                'prev_std_score': prev_data['Dive_Points'].std(),
                'prev_max_score': prev_data['Dive_Points'].max(),
                'prev_min_score': prev_data['Dive_Points'].min(),
                'prev_trend': self._calculate_trend(prev_data['Dive_Points']),

                # Time features
                'years_since_first': features_df.loc[i, 'Year'] - features_df['Year'].min(),
                'age': features_df.loc[i, 'Age'],
                'season_progress': (features_df.loc[i, 'Year'] - features_df['Year'].min()) /
                                   (features_df['Year'].max() - features_df['Year'].min()),

                # Competition context features (if available)
                'dive_number': features_df.loc[i, 'Dive_Number'],
                'difficulty': features_df.loc[i, 'Difficulty_Degree'],
            }

            # Add judge consistency features
            judge_cols = ['Judge1', 'Judge2', 'Judge3', 'Judge4', 'Judge5', 'Judge6', 'Judge7']
            if all(col in features_df.columns for col in judge_cols):
                current_judges = features_df.loc[i, judge_cols]
                feature_dict['judge_avg_current'] = current_judges.mean()
                feature_dict['judge_std_current'] = current_judges.std()

                # Historical judge consistency
                prev_judge_stds = []
                for j in range(max(0, i - 3), i):
                    prev_judges = features_df.loc[j, judge_cols]
                    prev_judge_stds.append(prev_judges.std())
                feature_dict['prev_judge_std_avg'] = np.mean(prev_judge_stds) if prev_judge_stds else 0

            X_list.append(feature_dict)
            y_list.append(y)

        X_df = pd.DataFrame(X_list)
        y_array = np.array(y_list)

        return X_df, y_array

    def _calculate_trend(self, scores):
        """Calculate score trend"""
        if len(scores) < 2:
            return 0
        x = np.arange(len(scores))
        slope = np.polyfit(x, scores, 1)[0]
        return slope

    def build_prediction_model(self):
        """Build and train XGBoost prediction model"""
        # Prepare features
        X, y = self.prepare_features_for_prediction()

        if len(X) < 10:
            print("Insufficient data to train reliable model")
            return None, None, None, None

        # Encode categorical variables
        X_encoded = X.copy()
        le_event_type = LabelEncoder()
        X_encoded['Event_Type_encoded'] = le_event_type.fit_transform(X_encoded['Event_Type'])

        # Select features
        feature_cols = [
            'Age', 'prev_avg_score', 'prev_std_score', 'prev_max_score',
            'prev_min_score', 'prev_trend', 'years_since_first', 'season_progress',
            'Event_Type_encoded', 'dive_number'
        ]

        # Add judge features (if available)
        if 'judge_avg_current' in X_encoded.columns:
            feature_cols.extend(['judge_avg_current', 'judge_std_current', 'prev_judge_std_avg'])

        # Ensure all features exist
        feature_cols = [col for col in feature_cols if col in X_encoded.columns]

        X_features = X_encoded[feature_cols]

        # Split train and test sets (time series split)
        split_idx = int(len(X_features) * 0.8)
        X_train = X_features.iloc[:split_idx]
        X_test = X_features.iloc[split_idx:]
        y_train = y[:split_idx]
        y_test = y[split_idx:]

        # Train XGBoost model
        model = xgb.XGBRegressor(
            n_estimators=200,
            max_depth=4,
            learning_rate=0.05,
            subsample=0.8,
            colsample_bytree=0.8,
            random_state=42,
            objective='reg:squarederror',
            eval_metric='mae'
        )

        # Train model
        model.fit(
            X_train, y_train,
            eval_set=[(X_train, y_train), (X_test, y_test)],
            verbose=False
        )

        # Predictions
        y_pred_train = model.predict(X_train)
        y_pred_test = model.predict(X_test)

        # Calculate metrics
        train_mae = mean_absolute_error(y_train, y_pred_train)
        test_mae = mean_absolute_error(y_test, y_pred_test)
        train_r2 = r2_score(y_train, y_pred_train)
        test_r2 = r2_score(y_test, y_pred_test)

        metrics = {
            'Train MAE': train_mae,
            'Test MAE': test_mae,
            'Train R²': train_r2,
            'Test R²': test_r2
        }

        # Feature importance
        feature_importance = pd.DataFrame({
            'Feature': feature_cols,
            'Importance': model.feature_importances_
        }).sort_values('Importance', ascending=False)

        return model, X_test, y_test, y_pred_test, metrics, feature_importance, X_encoded.iloc[split_idx:].copy()

    def predict_next_dive(self, model, X_encoded):
        """Predict next 207C score"""
        if model is None or len(X_encoded) == 0:
            return None

        # Get features from last record
        last_features = X_encoded.iloc[-1:].copy()

        # Prepare feature columns
        feature_cols = model.get_booster().feature_names

        # Ensure feature match
        if not all(col in last_features.columns for col in feature_cols):
            print("Feature mismatch, cannot predict")
            return None

        X_last = last_features[feature_cols]

        # Prediction
        prediction = model.predict(X_last)[0]

        # Calculate prediction interval (based on test set error)
        y_test = model.evals_result()['validation_1']['mae']
        if len(y_test) > 0:
            error_std = np.std(y_test)
            lower_bound = max(0, prediction - 1.96 * error_std)
            upper_bound = prediction + 1.96 * error_std
        else:
            lower_bound = prediction - 5
            upper_bound = prediction + 5

        return {
            'Predicted Score': prediction,
            '95% Confidence Interval': (lower_bound, upper_bound),
            'Last Actual Score': self.df_207c.iloc[-1]['Dive_Points'],
            'Last Competition': self.df_207c.iloc[-1]['Event'],
            'Advice': self._generate_advice(prediction, self.df_207c.iloc[-1]['Dive_Points'])
        }

    def _generate_advice(self, predicted_score, last_score):
        """Generate advice"""
        if predicted_score > last_score + 5:
            return "Expected significant improvement, continue current training"
        elif predicted_score > last_score + 2:
            return "Expected slight improvement, current training direction is correct"
        elif abs(predicted_score - last_score) <= 2:
            return "Expected stable performance, maintain current level"
        elif predicted_score < last_score - 5:
            return "Attention needed, possible decline in performance, consider adjusting training"
        else:
            return "Expected slight fluctuation, within normal range"

    def create_visualizations(self, model=None, feature_importance=None, event_metrics=None):
        """Create visualization charts"""
        fig, axes = plt.subplots(2, 3, figsize=(18, 12))

        # 1. 207C Score Time Series Chart
        ax1 = axes[0, 0]
        self.df_207c_sorted = self.df_207c.sort_values('Date')
        ax1.plot(range(len(self.df_207c_sorted)), self.df_207c_sorted['Dive_Points'],
                 marker='o', linewidth=2, markersize=8, color='royalblue')
        ax1.axhline(y=self.df_207c['Dive_Points'].mean(), color='red',
                    linestyle='--', alpha=0.7, label=f'Avg: {self.df_207c["Dive_Points"].mean():.1f}')
        ax1.fill_between(range(len(self.df_207c_sorted)),
                         self.df_207c['Dive_Points'].mean() - self.df_207c['Dive_Points'].std(),
                         self.df_207c['Dive_Points'].mean() + self.df_207c['Dive_Points'].std(),
                         alpha=0.2, color='gray', label='±1 Std Dev')
        ax1.set_xlabel('Competition Sequence')
        ax1.set_ylabel('207C Score')
        ax1.set_title('Yuxi CHEN - 207C Score Time Series')
        ax1.legend()
        ax1.grid(True, alpha=0.3)

        # 2. Score Distribution Histogram
        ax2 = axes[0, 1]
        ax2.hist(self.df_207c['Dive_Points'], bins=12, alpha=0.7, color='lightseagreen',
                 edgecolor='black', density=True)
        ax2.axvline(x=self.df_207c['Dive_Points'].mean(), color='red',
                    linestyle='--', linewidth=2, label=f'Mean: {self.df_207c["Dive_Points"].mean():.1f}')
        ax2.axvline(x=self.df_207c['Dive_Points'].median(), color='orange',
                    linestyle=':', linewidth=2, label=f'Median: {self.df_207c["Dive_Points"].median():.1f}')
        ax2.set_xlabel('207C Score')
        ax2.set_ylabel('Frequency')
        ax2.set_title('207C Score Distribution')
        ax2.legend()

        # 3. Different Event Types Box Plot Comparison
        ax3 = axes[0, 2]
        event_types_data = []
        event_types_labels = []

        for event_type in self.df_207c['Event_Type'].unique():
            event_data = self.df_207c[self.df_207c['Event_Type'] == event_type]['Dive_Points']
            if len(event_data) > 1:  # At least 2 data points
                event_types_data.append(event_data.values)
                event_types_labels.append(f"{event_type}\n(n={len(event_data)})")

        if event_types_data:
            box = ax3.boxplot(event_types_data, labels=event_types_labels, patch_artist=True)
            colors = ['lightblue', 'lightgreen', 'lightcoral']
            for patch, color in zip(box['boxes'], colors[:len(event_types_data)]):
                patch.set_facecolor(color)
            ax3.set_ylabel('207C Score')
            ax3.set_title('207C Score by Competition Type')
            ax3.grid(True, alpha=0.3, axis='y')

        # 4. Age vs Score Relationship
        ax4 = axes[1, 0]
        scatter = ax4.scatter(self.df_207c['Age'], self.df_207c['Dive_Points'],
                              c=self.df_207c['Year'], cmap='viridis', s=100, alpha=0.7)
        ax4.set_xlabel('Age')
        ax4.set_ylabel('207C Score')
        ax4.set_title('Age vs 207C Score')
        plt.colorbar(scatter, ax=ax4, label='Year')

        # Add trend line
        if len(self.df_207c) > 1:
            z = np.polyfit(self.df_207c['Age'], self.df_207c['Dive_Points'], 1)
            p = np.poly1d(z)
            ax4.plot(self.df_207c['Age'].sort_values(), p(self.df_207c['Age'].sort_values()),
                     "r--", alpha=0.8, label=f'Trend: y={z[0]:.2f}x+{z[1]:.2f}')
            ax4.legend()

        # 5. Feature Importance (if model exists)
        ax5 = axes[1, 1]
        if feature_importance is not None and len(feature_importance) > 0:
            # Take top 10 features
            top_features = feature_importance.head(10)

            # Ensure length matches
            n_features = len(top_features)

            # Generate correct length color array
            if n_features > 0:
                colors = plt.cm.RdYlBu(np.linspace(0, 1, n_features))

                # Create horizontal bar chart
                y_pos = np.arange(n_features)
                bars = ax5.barh(y_pos, top_features['Importance'], color=colors)

                # Set y-axis labels
                ax5.set_yticks(y_pos)
                ax5.set_yticklabels(top_features['Feature'])
                ax5.invert_yaxis()  # Most important at top
                ax5.set_xlabel('Feature Importance')
                ax5.set_title('XGBoost Feature Importance')

                # Add values on bars
                for i, (bar, importance) in enumerate(zip(bars, top_features['Importance'])):
                    ax5.text(importance + 0.001, bar.get_y() + bar.get_height() / 2,
                             f'{importance:.3f}', ha='left', va='center')
            else:
                ax5.text(0.5, 0.5, 'No valid feature data',
                         ha='center', va='center', transform=ax5.transAxes, fontsize=12)
                ax5.set_title('Feature Importance (No Data)')
        else:
            ax5.text(0.5, 0.5, 'No model feature importance data',
                     ha='center', va='center', transform=ax5.transAxes, fontsize=12)
            ax5.set_title('Feature Importance')

        # 6. Prediction vs Actual Comparison (if model and test data exist)
        ax6 = axes[1, 2]
        if hasattr(self, 'y_test') and hasattr(self, 'y_pred_test') and len(self.y_test) > 0:
            ax6.scatter(range(len(self.y_test)), self.y_test,
                        alpha=0.6, label='Actual', s=80)
            ax6.scatter(range(len(self.y_pred_test)), self.y_pred_test,
                        alpha=0.6, label='Predicted', s=80, marker='x')
            ax6.plot(range(len(self.y_test)), self.y_test, 'b-', alpha=0.3)
            ax6.plot(range(len(self.y_pred_test)), self.y_pred_test, 'r--', alpha=0.3)
            ax6.set_xlabel('Test Sample Index')
            ax6.set_ylabel('207C Score')
            ax6.set_title('Model Predictions vs Actual Scores')
            ax6.legend()
            ax6.grid(True, alpha=0.3)
        else:
            # Display stability metrics
            ax6.text(0.1, 0.8, f"Total Attempts: {len(self.df_207c)}", fontsize=12)
            ax6.text(0.1, 0.7, f"Avg Score: {self.df_207c['Dive_Points'].mean():.1f}", fontsize=12)
            ax6.text(0.1, 0.6, f"Std Dev: {self.df_207c['Dive_Points'].std():.1f}", fontsize=12)
            ax6.text(0.1, 0.5,
                     f"CV: {self.df_207c['Dive_Points'].std() / self.df_207c['Dive_Points'].mean() * 100:.1f}%",
                     fontsize=12)
            ax6.text(0.1, 0.4, f"Range: {self.df_207c['Dive_Points'].max() - self.df_207c['Dive_Points'].min():.1f}",
                     fontsize=12)
            ax6.axis('off')
            ax6.set_title('Stability Metrics Summary')

        plt.tight_layout()
        return fig


# 2. Main execution function
def analyze_chen_yuxi_207c_from_file(file_path):
    """
    Main function to analyze Chen Yuxi's 207C action from file

    Parameters:
    file_path: Excel file path
    """

    print("=" * 60)
    print("Chen Yuxi - 207C Action Stability Analysis")
    print("=" * 60)

    # Load data
    print(f"Loading data from file: {file_path}")
    df = pd.read_excel(file_path)

    # Initialize analyzer
    analyzer = Dive207CAnalyzer(df=df)

    # Calculate stability metrics
    print("\n1. Calculating stability metrics...")
    metrics, event_metrics = analyzer.calculate_stability_metrics()

    print("\nOverall Stability Metrics:")
    print("-" * 40)
    for key, value in metrics.items():
        if isinstance(value, float):
            print(f"{key}: {value:.2f}")
        else:
            print(f"{key}: {value}")

    print("\nAnalysis by Competition Type:")
    print("-" * 40)
    for event_type, stats in event_metrics.items():
        print(f"\n{event_type}:")
        for stat_key, stat_value in stats.items():
            if isinstance(stat_value, float):
                print(f"  {stat_key}: {stat_value:.2f}")
            else:
                print(f"  {stat_key}: {stat_value}")

    # Build prediction model
    print("\n2. Building XGBoost prediction model...")
    model, X_test, y_test, y_pred_test, model_metrics, feature_importance, X_encoded_test = analyzer.build_prediction_model()

    if model is not None:
        # Save test data for visualization
        analyzer.y_test = y_test
        analyzer.y_pred_test = y_pred_test

        print("\nModel Performance Metrics:")
        print("-" * 40)
        for key, value in model_metrics.items():
            if isinstance(value, float):
                print(f"{key}: {value:.4f}")
            else:
                print(f"{key}: {value}")

        print("\nFeature Importance Ranking (Top 10):")
        print("-" * 40)
        print(feature_importance.head(10).to_string(index=False))

        # Predict next 207C score
        print("\n3. Predicting next 207C performance...")
        print("-" * 40)
        next_dive_prediction = analyzer.predict_next_dive(model, X_encoded_test)

        if next_dive_prediction:
            for key, value in next_dive_prediction.items():
                if isinstance(value, tuple):
                    print(f"{key}: {value[0]:.1f} - {value[1]:.1f}")
                elif isinstance(value, float):
                    print(f"{key}: {value:.1f}")
                else:
                    print(f"{key}: {value}")

    # Create visualizations
    print("\n4. Generating analysis charts...")
    fig = analyzer.create_visualizations(model, feature_importance, event_metrics)

    # Save chart to same directory
    base_name = os.path.splitext(os.path.basename(file_path))[0]
    output_filename = f"{base_name}_207c_analysis.png"
    output_path = os.path.join(os.path.dirname(file_path), output_filename)

    fig.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"\nCharts saved to: {output_path}")

    # Display charts
    plt.show()

    # Generate analysis report
    print("\n5. Generating comprehensive analysis report...")
    print("=" * 60)
    print("Chen Yuxi - 207C Action Comprehensive Analysis Report")
    print("=" * 60)

    print(f"\nI. Data Overview:")
    print(f"   • Analysis Period: {analyzer.df_207c['Year'].min()} - {analyzer.df_207c['Year'].max()}")
    print(f"   • Total Records: {metrics['Total Count']}")
    print(f"   • Age Range: {analyzer.df_207c['Age'].min()} - {analyzer.df_207c['Age'].max()} years")

    print(f"\nII. Stability Analysis:")
    print(f"   • Average Score: {metrics['Average Score']:.1f}")
    print(f"   • Score Variability: {metrics['Standard Deviation']:.1f}")
    cv_status = 'Very Stable' if metrics['Coefficient of Variation (%)'] < 10 else 'Relatively Stable' if metrics[
                                                                                                              'Coefficient of Variation (%)'] < 20 else 'Highly Variable'
    print(f"   • Coefficient of Variation: {metrics['Coefficient of Variation (%)']:.1f}% ({cv_status})")
    print(f"   • Stability Rating: {metrics['Stability Rating']}/10")

    print(f"\nIII. Competition Type Analysis:")
    best_event = max(event_metrics.items(), key=lambda x: x[1]['Average Score'])[0]
    most_stable_event = min(event_metrics.items(), key=lambda x: x[1]['Coefficient of Variation (%)'])[0]

    print(f"   • Highest Avg Score: {best_event} ({event_metrics[best_event]['Average Score']:.1f})")
    print(
        f"   • Most Stable: {most_stable_event} (CV: {event_metrics[most_stable_event]['Coefficient of Variation (%)']:.1f}%)")

    print(f"\nIV. Age Trend Analysis:")
    age_corr = analyzer.df_207c['Age'].corr(analyzer.df_207c['Dive_Points'])
    trend = "Increasing" if age_corr > 0 else "Decreasing" if age_corr < 0 else "Stable"
    print(f"   • Age-Score Correlation: {age_corr:.3f} ({trend} trend)")

    if model is not None:
        print(f"\nV. Prediction Analysis:")
        print(f"   • Model Accuracy: MAE = {model_metrics['Test MAE']:.2f}")
        print(f"   • Model Explanation: R² = {model_metrics['Test R²']:.3f}")

        if next_dive_prediction:
            print(f"   • Next 207C Prediction: {next_dive_prediction['Predicted Score']:.1f}")
            print(
                f"   • 95% Confidence Interval: {next_dive_prediction['95% Confidence Interval'][0]:.1f} - {next_dive_prediction['95% Confidence Interval'][1]:.1f}")
            print(
                f"   • vs Last Performance: {next_dive_prediction['Last Actual Score']:.1f} → Predicted {next_dive_prediction['Predicted Score']:.1f}")
            print(f"   • Analysis Advice: {next_dive_prediction['Advice']}")

    print(f"\nVI. Key Findings:")
    stability_level = 'Very Stable' if metrics['Coefficient of Variation (%)'] < 10 else 'Stable'
    print(f"   1. Chen Yuxi's 207C action is overall {stability_level}")
    print(f"   2. Most stable performance in {most_stable_event}")

    if age_corr > 0.1:
        print(f"   3. Scores show increasing trend with age")
    elif age_corr < -0.1:
        print(f"   3. Scores show decreasing trend with age")
    else:
        print(f"   3. Age has minimal impact on scores")

    if model is not None and feature_importance is not None and len(feature_importance) > 0:
        top_feature = feature_importance.iloc[0]['Feature']
        print(f"   4. Most important prediction factor: {top_feature}")

    print("\n" + "=" * 60)

    # Save detailed report to text file
    report_filename = f"{base_name}_207c_analysis_report.txt"
    report_path = os.path.join(os.path.dirname(file_path), report_filename)

    with open(report_path, 'w', encoding='utf-8') as f:
        f.write("=" * 60 + "\n")
        f.write("Chen Yuxi - 207C Action Comprehensive Analysis Report\n")
        f.write("=" * 60 + "\n\n")

        f.write("I. Data Overview:\n")
        f.write(f"   • Analysis Period: {analyzer.df_207c['Year'].min()} - {analyzer.df_207c['Year'].max()}\n")
        f.write(f"   • Total Records: {metrics['Total Count']}\n")
        f.write(f"   • Age Range: {analyzer.df_207c['Age'].min()} - {analyzer.df_207c['Age'].max()} years\n\n")

        f.write("II. Stability Analysis:\n")
        f.write(f"   • Average Score: {metrics['Average Score']:.1f}\n")
        f.write(f"   • Score Variability: {metrics['Standard Deviation']:.1f}\n")
        f.write(f"   • Coefficient of Variation: {metrics['Coefficient of Variation (%)']:.1f}% ({cv_status})\n")
        f.write(f"   • Stability Rating: {metrics['Stability Rating']}/10\n\n")

        f.write("III. Competition Type Analysis:\n")
        f.write(f"   • Highest Avg Score: {best_event} ({event_metrics[best_event]['Average Score']:.1f})\n")
        f.write(
            f"   • Most Stable: {most_stable_event} (CV: {event_metrics[most_stable_event]['Coefficient of Variation (%)']:.1f}%)\n\n")

        f.write("IV. Age Trend Analysis:\n")
        f.write(f"   • Age-Score Correlation: {age_corr:.3f} ({trend} trend)\n\n")

        if model is not None:
            f.write("V. Prediction Analysis:\n")
            f.write(f"   • Model Accuracy: MAE = {model_metrics['Test MAE']:.2f}\n")
            f.write(f"   • Model Explanation: R² = {model_metrics['Test R²']:.3f}\n\n")

            if next_dive_prediction:
                f.write(f"   • Next 207C Prediction: {next_dive_prediction['Predicted Score']:.1f}\n")
                f.write(
                    f"   • 95% Confidence Interval: {next_dive_prediction['95% Confidence Interval'][0]:.1f} - {next_dive_prediction['95% Confidence Interval'][1]:.1f}\n")
                f.write(f"   • Analysis Advice: {next_dive_prediction['Advice']}\n\n")

        f.write("VI. Key Findings:\n")
        f.write(f"   1. Chen Yuxi's 207C action is overall {stability_level}\n")
        f.write(f"   2. Most stable performance in {most_stable_event}\n")

        if age_corr > 0.1:
            f.write(f"   3. Scores show increasing trend with age\n")
        elif age_corr < -0.1:
            f.write(f"   3. Scores show decreasing trend with age\n")
        else:
            f.write(f"   3. Age has minimal impact on scores\n")

    print(f"\nDetailed report saved to: {report_path}")

    return analyzer, model, metrics, event_metrics


# 3. Usage example
if __name__ == "__main__":
    # Set your Excel file path
    # Replace the path below with your actual file path
    file_path = "Yuxi CHEN__data.xlsx"  # Change to your actual file path

    try:
        # Check if file exists
        if not os.path.exists(file_path):
            print(f"Error: File '{file_path}' does not exist")
            print("Please ensure:")
            print(f"1. File '{file_path}' is in current directory")
            print("2. Or provide full file path")
            print("\nCurrent directory contents:")
            print(os.listdir('.'))
        else:
            print(f"File found: {file_path}")

            # Call main analysis function
            analyzer, model, metrics, event_metrics = analyze_chen_yuxi_207c_from_file(file_path)

            # Additional analysis: significance of differences between competition types
            print("\nAdditional Analysis: Significance of Differences")
            print("-" * 40)

            # Statistical tests (example)
            try:
                from scipy import stats

                for event_type in analyzer.df_207c['Event_Type'].unique():
                    event_data = analyzer.df_207c[analyzer.df_207c['Event_Type'] == event_type]['Dive_Points']
                    if len(event_data) > 2:
                        # t-test against overall mean
                        t_stat, p_value = stats.ttest_1samp(event_data, metrics['Average Score'])
                        significance = 'Significant' if p_value < 0.05 else 'Not Significant'
                        print(f"{event_type}: Difference from overall mean p-value={p_value:.4f} ({significance})")
            except ImportError:
                print("scipy not installed, skipping statistical tests")

    except Exception as e:
        print(f"Error during analysis: {e}")
        import traceback

        traceback.print_exc()