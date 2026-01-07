import time
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import warnings

warnings.filterwarnings('ignore')

print("=== 2025 World Cup Women's 10m Platform Final Data Extraction ===")

# Configure Chrome Driver
CHROME_DRIVER_PATH = r'D:\chromedriver\chromedriver.exe'

chrome_options = Options()
chrome_options.add_argument('--headless')  # Headless mode, no browser window
chrome_options.add_argument('--disable-gpu')
chrome_options.add_argument('--no-sandbox')
chrome_options.add_argument('--disable-dev-shm-usage')
chrome_options.add_argument('--log-level=3')

# 如果您想要看到浏览器界面，注释掉下面的headless选项
# chrome_options.add_argument('--headless')

service = Service(CHROME_DRIVER_PATH)
driver = webdriver.Chrome(service=service, options=chrome_options)

# 2025年世界杯分站赛 URL - 更新为新的URL
url = "https://www.worldaquatics.com/competitions/4783/world-aquatics-diving-world-cup-2025/results?event=d011fbc4-8cd9-4294-a97a-96139f8c8b75&unit=finals"

print(f"🌐 Extracting data from: 2025 World Cup Women's 10m Platform FINAL")
print(f"🔗 URL: {url}")
print(f"🚀 ChromeDriver路径: {CHROME_DRIVER_PATH}")
print(f"📅 Competition: World Aquatics Diving World Cup 2025")
print(f"🏆 Event: Women's 10m Platform - FINAL")

try:
    # 测试ChromeDriver是否正常工作
    print("🔄 正在启动Chrome浏览器...")

    # 网页数据提取部分
    driver.get(url)
    print("✅ 页面加载中...")

    # 增加等待时间确保页面完全加载
    time.sleep(10)

    # 使用显式等待确保页面元素加载完成
    try:
        wait = WebDriverWait(driver, 15)
        wait.until(EC.presence_of_element_located((By.CLASS_NAME, "results-table__row")))
        print("✅ 比赛数据表格加载成功")
    except Exception as e:
        print(f"⚠️ 等待表格超时，继续执行: {e}")

    print("✅ 页面加载成功，正在执行JavaScript提取数据...")

    # Execute JavaScript to expand all rows and extract data
    js_code = """
    // 1. First expand all rows
    var expandButtons = document.querySelectorAll('button.results-table__expand-btn.js-results-row-expand');
    console.log('Found ' + expandButtons.length + ' expand buttons');

    for (var i = 0; i < expandButtons.length; i++) {
        try {
            expandButtons[i].click();
        } catch(e) {
            console.log('Error clicking button ' + i + ': ' + e);
        }
    }

    // Wait for expansion to complete
    await new Promise(resolve => setTimeout(resolve, 3000));

    // 2. Extract all data including competition info
    var allData = [];

    // Extract competition information
    var competitionInfo = {
        title: document.querySelector('h1.competition-header__title')?.textContent?.trim() || '',
        location: document.querySelector('.competition-header__location')?.textContent?.trim() || '',
        date: document.querySelector('.competition-header__date')?.textContent?.trim() || ''
    };

    // Get all athlete rows
    var athleteRows = document.querySelectorAll('tr.results-table__row.js-results-table-row');

    for (var i = 0; i < athleteRows.length; i++) {
        var athleteRow = athleteRows[i];
        var athleteData = {};

        // Extract basic information
        athleteData.rank = athleteRow.querySelector('td.results-table__cell.bold')?.textContent?.trim() || '';
        athleteData.country = athleteRow.querySelector('.results-table__country')?.textContent?.trim() || '';

        // Extract age - 修正后的方法
        athleteData.age = '';
        var tds = athleteRow.querySelectorAll('td');
        if (tds.length > 3) {
            var ageCandidate = tds[3]?.textContent?.trim() || '';
            // 验证它看起来像年龄（数字，且在合理范围内）
            if (/^\\d+$/.test(ageCandidate)) {
                var ageNum = parseInt(ageCandidate);
                if (ageNum >= 10 && ageNum <= 50) {
                    athleteData.age = ageCandidate;
                }
            }
        }

        var firstName = athleteRow.querySelector('.results-table__athlete-first')?.textContent?.trim() || '';
        var lastName = athleteRow.querySelector('.results-table__athlete-last')?.textContent?.trim() || '';
        athleteData.athlete = (firstName + ' ' + lastName).trim();

        athleteData.points = athleteRow.querySelector('td.results-table__cell.results-table__cell--highlight.black')?.textContent?.trim() || '';

        // Find corresponding detailed data row
        var expandableRow = athleteRow.nextElementSibling;
        var diveDetails = [];

        if (expandableRow && expandableRow.classList.contains('results-table__expandable')) {
            // Extract diving action data
            var diveRows = expandableRow.querySelectorAll('tr.results-table__sub-row.results-table__sub-header-row--border');

            for (var j = 0; j < diveRows.length; j++) {
                var diveRow = diveRows[j];
                var diveData = {};

                diveData.diveNum = diveRow.querySelector('td.results-table__sub-cell.results-table__sub-cell--dive')?.textContent?.trim() || '';
                diveData.diveCode = diveRow.querySelector('td.results-table__sub-cell:nth-child(2)')?.textContent?.trim() || '';
                diveData.dd = diveRow.querySelector('td.results-table__sub-cell.u-text-left')?.textContent?.trim() || '';

                // Extract judge scores (7 judges)
                var judgeCells = diveRow.querySelectorAll('td.results-table__sub-cell.u-hide-tablet');
                var scores = [];
                for (var k = 0; k < Math.min(7, judgeCells.length); k++) {
                    scores.push(judgeCells[k]?.textContent?.trim() || '');
                }
                diveData.judgeScores = scores;

                // Extract other information
                var cells = diveRow.querySelectorAll('td.results-table__sub-cell');
                if (cells.length >= 14) {
                    diveData.divePoints = cells[10]?.textContent?.trim() || '';
                    diveData.totalPoints = cells[11]?.textContent?.trim() || '';
                    diveData.diveRank = cells[12]?.textContent?.trim() || '';
                    diveData.ovRank = cells[13]?.textContent?.trim() || '';
                    diveData.pointsBehind = cells[14]?.textContent?.trim() || '';
                }

                diveDetails.push(diveData);
            }
        }

        athleteData.diveDetails = diveDetails;
        allData.push(athleteData);
    }

    return {
        competitionInfo: competitionInfo,
        athleteData: allData
    };
    """

    # Execute JavaScript
    print("🔄 正在执行JavaScript代码...")
    result = driver.execute_script(js_code)

    competition_info = result.get('competitionInfo', {})
    all_data = result.get('athleteData', [])

    if all_data:
        print(f"\n🏆 比赛信息:")
        print(f"   • 赛事名称: {competition_info.get('title', 'N/A')}")
        print(f"   • 比赛地点: {competition_info.get('location', 'N/A')}")
        print(f"   • 比赛时间: {competition_info.get('date', 'N/A')}")

        print(f"\n✅ 成功提取 {len(all_data)} 位运动员的2025世界杯分站赛数据")

        # 从比赛信息中提取分站信息
        competition_title = competition_info.get('title', '')
        stop_number = 'Stop2'  # 默认值

        # 尝试从比赛标题中提取分站信息
        if 'Stop' in competition_title:
            import re

            stop_match = re.search(r'Stop\s*(\d+)', competition_title)
            if stop_match:
                stop_number = f"Stop{stop_match.group(1)}"

        # 也可以从URL中判断
        if '4783' in url:  # 根据URL中的ID判断
            stop_number = 'Stop2'

        # Process data
        athlete_list = []
        dive_list = []

        for athlete in all_data:
            # Save athlete information (包含Age字段)
            athlete_list.append({
                'Rank': athlete.get('rank', ''),
                'Athlete': athlete.get('athlete', ''),
                'Age': athlete.get('age', ''),
                'Country': athlete.get('country', ''),
                'Total_Points': athlete.get('points', ''),
                'Competition': competition_info.get('title', '2025 World Cup'),
                'Stop': stop_number,
                'Location': competition_info.get('location', 'N/A'),
                'Date': competition_info.get('date', 'N/A')
            })

            # Save detailed diving information
            for dive in athlete.get('diveDetails', []):
                dive_list.append({
                    'Athlete_Rank': athlete.get('rank', ''),
                    'Athlete_Name': athlete.get('athlete', ''),
                    'Country': athlete.get('country', ''),
                    'Dive_Number': dive.get('diveNum', ''),
                    'Dive_Code': dive.get('diveCode', ''),
                    'Difficulty_Degree': dive.get('dd', ''),
                    'Judge1': dive.get('judgeScores', [])[0] if len(dive.get('judgeScores', [])) > 0 else '',
                    'Judge2': dive.get('judgeScores', [])[1] if len(dive.get('judgeScores', [])) > 1 else '',
                    'Judge3': dive.get('judgeScores', [])[2] if len(dive.get('judgeScores', [])) > 2 else '',
                    'Judge4': dive.get('judgeScores', [])[3] if len(dive.get('judgeScores', [])) > 3 else '',
                    'Judge5': dive.get('judgeScores', [])[4] if len(dive.get('judgeScores', [])) > 4 else '',
                    'Judge6': dive.get('judgeScores', [])[5] if len(dive.get('judgeScores', [])) > 5 else '',
                    'Judge7': dive.get('judgeScores', [])[6] if len(dive.get('judgeScores', [])) > 6 else '',
                    'Dive_Points': dive.get('divePoints', ''),
                    'Cumulative_Total': dive.get('totalPoints', ''),
                    'Dive_Rank': dive.get('diveRank', ''),
                    'Overall_Rank': dive.get('ovRank', ''),
                    'Points_Behind': dive.get('pointsBehind', ''),
                    'Competition': competition_info.get('title', '2025 World Cup'),
                    'Stop': stop_number,
                    'Location': competition_info.get('location', 'N/A'),
                    'Date': competition_info.get('date', 'N/A')
                })

        # Save to CSV files - 2025 World Cup
        if athlete_list:
            df_athletes = pd.DataFrame(athlete_list)
            # 更新文件名，使用分站信息
            athletes_filename = f"2025_WorldCup_Women10m_{stop_number}_Athlete_Rankings.csv"
            df_athletes.to_csv(athletes_filename, index=False, encoding='utf-8-sig')
            print(f"\n✅ 2025世界杯分站赛运动员排名已保存为CSV: {athletes_filename}")
            print(f"📋 CSV列名: {df_athletes.columns.tolist()}")
            print(f"📊 示例数据:")
            print(df_athletes[['Rank', 'Athlete', 'Age', 'Country', 'Total_Points', 'Stop']].head())

        if dive_list:
            df_dives = pd.DataFrame(dive_list)
            # 更新文件名，使用分站信息
            dives_filename = f"2025_WorldCup_Women10m_{stop_number}_Detailed_Scores.csv"
            df_dives.to_csv(dives_filename, index=False, encoding='utf-8-sig')
            print(f"✅ 2025世界杯分站赛详细跳水分数已保存为CSV: {dives_filename}")
            print(f"📊 总计 {len(dive_list)} 条记录 ({len(all_data)} 位运动员 × 通常5次跳水)")

        # Display statistics
        print(f"\n📈 2025世界杯分站赛数据提取统计:")
        print(f"  🏊 运动员数量: {len(all_data)}")
        print(f"  💦 跳水动作总数: {len(dive_list)}")
        print(f"  📍 分站: {stop_number}")

        # 显示年龄统计
        ages = [a['Age'] for a in athlete_list if a['Age']]
        if ages:
            print(f"  📅 有年龄数据的运动员: {len(ages)}/{len(athlete_list)}")
            age_nums = [int(age) for age in ages if age.isdigit()]
            if age_nums:
                print(f"    • 最年轻运动员: {min(age_nums)} 岁")
                print(f"    • 最年长运动员: {max(age_nums)} 岁")
                print(f"    • 平均年龄: {sum(age_nums) / len(age_nums):.1f} 岁")

        # 显示总分统计
        try:
            valid_scores = []
            for a in athlete_list:
                if a['Total_Points']:
                    # 清理分数字符串，移除可能的中文字符或其他非数字字符
                    score_str = str(a['Total_Points']).strip()
                    # 提取数字和小数点
                    import re

                    match = re.search(r'[\d.]+', score_str)
                    if match:
                        try:
                            valid_scores.append(float(match.group()))
                        except:
                            continue

            if valid_scores:
                print(f"  🏆 总分统计:")
                print(f"    • 最高总分: {max(valid_scores):.1f}")
                print(f"    • 最低总分: {min(valid_scores):.1f}")
                print(f"    • 平均总分: {sum(valid_scores) / len(valid_scores):.1f}")

                # 显示奖牌获得者
                if len(athlete_list) >= 3:
                    print(f"\n🥇 奖牌获得者 ({stop_number}):")
                    for i in range(min(3, len(athlete_list))):
                        medal = ['🥇', '🥈', '🥉'][i]
                        athlete = athlete_list[i]
                        print(f"    {medal} {athlete['Athlete']} ({athlete['Country']}): {athlete['Total_Points']}")
        except Exception as e:
            print(f"  ⚠️ 分数统计错误: {e}")

        # 显示国家分布
        if athlete_list:
            from collections import Counter

            countries = Counter([a['Country'] for a in athlete_list])
            print(f"\n🌍 国家分布 ({len(countries)} 个国家):")
            for country, count in countries.most_common():
                print(f"    • {country}: {count} 位运动员")

        # 显示文件保存位置
        import os

        current_dir = os.getcwd()
        print(f"\n📁 输出文件保存位置:")
        print(f"    • 当前工作目录: {current_dir}")
        print(f"    • {athletes_filename}")
        print(f"    • {dives_filename}")

    else:
        print("❌ 未提取到2025世界杯分站赛数据")

except Exception as e:
    print(f"❌ 提取2025世界杯分站赛数据时出错: {e}")
    print(f"❌ 错误类型: {type(e).__name__}")

    # 如果是ChromeDriver相关错误，给出更多信息
    if "chromedriver" in str(e).lower() or "service" in str(e).lower():
        print("\n🔧 ChromeDriver问题排查:")
        print("   1. 确认ChromeDriver路径正确: D:\\chromedriver\\chromedriver.exe")
        print("   2. 确认Chrome浏览器已安装")
        print("   3. 确认ChromeDriver版本与Chrome浏览器版本匹配")
        print("   4. 尝试删除headless模式: 注释掉 chrome_options.add_argument('--headless')")
        print("   5. 检查ChromeDriver是否被其他程序占用")

    import traceback

    traceback.print_exc()

finally:
    # 关闭浏览器
    try:
        driver.quit()
        print("✅ 浏览器已关闭")
    except:
        pass

    print("\n🎉 2025世界杯女子10米跳台分站赛决赛数据提取完成!")
    print("=" * 60)