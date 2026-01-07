# -Development-Analysis-of-China-s-Diving-Program-Based-on-Multi-source-Data
This project focuses on the women's 10-meter platform event. It extracts the patterns and advantages of Chinese diving by combining machine learning and time-series analysis from four dimensions: age, stability, athlete comparison, and difficulty.



## 目录
- [Part 1: Age Analysis 年龄分析](#part-1-age-analysis-年龄分析)
- [Part 2: Performance Stability Analysis 表现稳定性分析](#part-2-performance-stability-analysis-表现稳定性分析)
- [Part 3: Multi-person Comparative Analysis 多人对比分析](#part-3多人对比分析multi-person-comparative-analysis)
- [Part 4: Temporal Analysis of Difficulty 难度时序分析](#part4-难度时序分析以及难度-扣分关系探究)


## Part 1: Age Analysis 年龄分析

1. 年龄相关特征分析
总结了 3 类运动员职业生涯轨迹（长期成长型、中期突破型、早期巅峰型），并结合具体运动员案例展示了年龄、得分、动作难度的变化规律；
对比了中国与其他国家运动员的 “首次参赛年龄”，发现中国采用 “低龄选拔策略”（中国运动员首赛平均年龄 15.7 岁，远低于其他国家的～21 岁）；
分析了年龄与成绩的关系：呈现 “先降后升” 的非线性趋势，最佳参赛年龄约 25.2 岁；同时低龄组（<18 岁）成绩中位数最高，体现 “低龄优势”。
2. 表现 / 夺牌的关键影响因素
通过模型（XGBoost、LightGBM、RandomForest）分析特征重要性：
预测得分的核心特征：历史平均得分（avg_score） 是最关键因素，年龄相关特征（当前年龄 / 首赛年龄）排名第二；
预测夺牌的核心特征：历史平均得分、首赛年龄 是前两大因素，“是否为中国运动员” 也进入前 5，与中国的低龄选拔策略相关。
3. 预测模型的性能评估
得分预测（回归模型）：XGBoost 表现最佳，可解释 75% 的得分波动，平均预测误差约 26 分；
夺牌预测（分类模型）：RandomForest 表现最佳，准确率 88.2%，区分夺牌 / 未夺牌的能力较强（AUC=0.769）。
1. Analysis of Age-Related Characteristics
Summarized three career trajectories among athletes (long-term growth, mid-career breakthrough, early peak), illustrating patterns in age, scores, and difficulty levels through specific athlete case studies;
Compared the “age of first competition” between Chinese and international athletes, revealing China's “early selection strategy” (average debut age of 15.7 years, significantly lower than the ~21 years observed in other countries);
Analyzed the relationship between age and performance: a nonlinear “decline-then-rise” trend emerged, with the optimal competition age around 25.2 years; simultaneously, the median performance score was highest in the younger age group (<18 years), demonstrating a “youth advantage.”
2. Key Influencing Factors for Performance/Medal Acquisition
Feature importance analyzed via models (XGBoost, LightGBM, RandomForest):
Core features for predicting scores: Historical average score (avg_score) is the most critical factor, followed by age-related features (current age / age at first competition);
Core features for predicting medals: Historical average score and age at first competition rank as the top two factors, while “whether the athlete is Chinese” also enters the top 5, aligning with China's early selection strategy.
3. Performance Evaluation of Predictive Models
Score Prediction (Regression Model): XGBoost performs best, explaining 75% of score variation with an average prediction error of approximately 26 points.
Medal Prediction (Classification Model): RandomForest performs best with 88.2% accuracy, demonstrating strong ability to distinguish medalists from non-medalists (AUC=0.769).


---

## Part 2: Performance Stability Analysis 表现稳定性分析

1. 使用的数据
陈芋汐从2019年到2025年参加过的所有十米女子单人跳台的国际A级赛事
Data Used
All international A-level competitions in the women's 10-meter individual platform diving event that Chen Yuxi participated in from 2019 to 2025

2. 项目描述
本研究从技术细节和整体表现两个维度对运动员陈芋汐的赛事稳定性进行分析。首先，选取高难度系数（3.3）的207C跳水动作为具体观察点，该动作因挑战性高、易在比赛中出现表现波动，其完成质量可有效反映运动员的技术稳定性。其次，通过评估单场比赛中最高分与最低分之差，选取最稳定与最不稳定的两场比赛进行对比分析，以直观呈现其整体发挥的波动情况及其潜在原因。研究方法上，借助XGBoost模型分别对207C动作表现及完整比赛数据进行了关键稳定性指标的计算，同时通过模型检测异常跳水结果，进一步探讨了表现波动的影响因素。
Project Description
This study analyzes athlete Chen Yuxi's competition stability from two dimensions: technical details and overall performance. First, the 207C diving maneuver with a high difficulty coefficient (3.3) was selected as the focal point. Due to its high challenge level and susceptibility to performance fluctuations during competitions, its execution quality effectively reflects the athlete's technical consistency. Second, by evaluating the difference between the highest and lowest scores within a single competition, the most stable and least stable events were selected for comparative analysis. This approach visually illustrates fluctuations in overall performance and identifies potential underlying causes. Methodologically, the XGBoost model was employed to calculate key stability metrics for both the 207C dive performance and complete competition data. Additionally, the model detected anomalous diving results, enabling further exploration of factors influencing performance variability.

3. 研究目标
量化评估跳水运动员的技术稳定性指标
识别影响表现稳定性的关键因素
探索运动员成长过程中的稳定性演变规律
验证XGBoost模型在体育数据分析中的有效性
Research Objectives
- Quantitatively evaluate technical stability metrics for diving athletes
- Identify key factors influencing performance stability
- Explore patterns of stability evolution throughout athletes' development
- Validate the effectiveness of XGBoost models in sports data analysis


---

## Part 3: Multi-person Comparative Analysis 多人对比分析
1. 用的什么数据、时间What data and time were used?
使用的数据是单人女子10米跳台项目的赛事记录，涵盖了不同时期的国际赛事：
其中一部分是陈若琳在2007-2013年间的参赛数据，涉及2007、2009、2011、2013年的世锦赛，2008（北京）、2012（伦敦）年的奥运会，以及2008、2010、2012年的世界杯赛事。
另一部分是近年赛事数据，覆盖2020-2025年，包含2020（东京）、2024（巴黎）年的奥运会，2022、2023、2024年的世锦赛，还有2022、2023（分站及超级决赛）、2024（分站及超级决赛）、2025（分站）年的世界杯赛事。
The data used are the competition records of the women's individual 10m platform event, covering international competitions from different periods:
One part is Chen Ruolin's participation data from 2007 to 2013, involving the World Championships in 2007, 2009, 2011, and 2013, the Olympic Games in 2008 (Beijing) and 2012 (London), as well as the World Cup events in 2008, 2010, and 2012.
The other part is the data from recent competitions, covering 2020-2025, including the Olympic Games in 2020 (Tokyo) and 2024 (Paris), the World Championships in 2022, 2023, and 2024, as well as the World Cup events in 2022, 2023 (leg events and super finals), 2024 (leg events and super finals), and 2025 (leg events).

2. 主要完成的工作Main work completed
围绕女子 10 米跳台项目完成了两类赛事数据分析工作：一方面是陈芋汐与全红婵的多人横向对比，从难度动作、回归模型、成绩可视化、因素相关性等维度展开，分析了两人的动作选择差异、难度与得分的关联度、成绩波动特点及裁判打分影响等内容；另一方面是老将与新将的代际纵向对比，基于 160 条单跳数据，借助随机森林模型、核心统计、难度分布等方法，对比了不同代际运动员的难度水平、得分稳定性等特征，也呈现了陈若琳等老将与新将在难度波动、得分表现上的差异。
Two types of competition data analysis work have been completed focusing on the women's 10m platform event: on the one hand, a multi-person horizontal comparison between Chen Yuxi and Quan Hongchan, which was carried out from the dimensions of difficult movements, regression models, score visualization, and factor correlation, analyzing the differences in movement selection between the two, the correlation between difficulty and scores, the characteristics of score fluctuations, and the impact of judges' scoring; on the other hand, a generational vertical comparison between veteran and new athletes. Based on 160 individual jump data, with the help of random forest models, core statistics, difficulty distribution and other methods, the characteristics such as difficulty levels and scoring stability of athletes from different generations were compared, and the differences in difficulty fluctuations and scoring performance between veteran athletes like Chen Ruolin and new athletes were also presented.


---

## Part 4: Temporal Analysis of Difficulty 难度时序分析
Temporal Analysis of Difficulty and Exploration of the Difficulty-Deduction Relationship

1. 使用的数据
2003-2025 年世锦赛、世界杯女子单人 10 米台预赛与决赛的全量数据（含预赛、决赛成套、单跳难度系数、裁判打分、得分等核心指标）
Complete Dataset of the Women's 10m Platform Preliminary and Final Rounds from the 2003-2025 World Championships and World Cup (Including key metrics for preliminary and final rounds such as overall routine and individual dive difficulty coefficients, judges' scores, actual scores, etc.)
聚焦2022-2025 年世锦赛决赛数据，开展难度与扣分关系探究，数据覆盖重点参赛国家和顶尖运动员。
Focusing on the 2022–2025 World Championship final data, this study explores the relationship between difficulty and deductions, covering key participating countries and top athletes.

2. 主要完成的工作
时序层面：针对预赛、决赛的不同数据特征，分别适配指数平滑、ARIMA (0,1,1) 模型，解析 2003-2025 年难度系数的长期稳定特征，并完成 2026-2029 年难度趋势的短期预测，明确了难度发展的时间规律。
Temporal Dimension: Based on the distinct data characteristics of preliminary and final rounds, exponential smoothing and ARIMA (0,1,1) models were respectively applied to analyze the long-term stability of difficulty coefficients from 2003 to 2025. Short-term predictions for the 2026–2029 difficulty trend were made, clarifying the temporal patterns in difficulty evolution.

关系探究层面：通过相关性分析、可视化对比，量化验证了 “单跳难度系数与动作扣分率无显著线性关联”。基于难度和扣分率的双维度行业标准，完成国家竞争梯队和运动员能力类型的精准分类可视化不同主体的竞争力特征。 
Relationship Exploration Dimension: Through correlation analysis and visual comparisons, it was quantitatively verified that "there is no significant linear relationship between single-dive difficulty coefficients and movement deduction rates." Using a dual-dimensional industry standard based on difficulty and deduction rates, precise classification of national competitive tiers and athlete capability types was achieved, visually illustrating the competitive characteristics of different entities.
