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

print("=== 2022 World Cup Women's 10m Platform Final Data Extraction ===")

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

# 2022年世界杯分站赛 URL
url = "https://www.worldaquatics.com/competitions/3012/fina-diving-world-cup-2022/results?event=fe8f025e-d2b2-498b-a433-8498527c5cee&unit=final"

print(f"🌐 Extracting data from: 2022 World Cup Women's 10m Platform FINAL")
print(f"🔗 URL: {url}")
print(f"🚀 ChromeDriver路径: {CHROME_DRIVER_PATH}")
print(f"📅 Competition: FINA Diving World Cup 2022")
print(f"🏆 Event: Women's 10m Platform - FINAL")
print(f"📝 注意: 2022年比赛仍使用FINA名称，后改为World Aquatics")

try:
    # 测试ChromeDriver是否正常工作
    print("🔄 正在启动Chrome浏览器...")

    # 网页数据提取部分
    driver.get(url)
    print("✅ 页面加载中...")

    # 增加等待时间确保页面完全加载
    time.sleep(15)  # 增加等待时间

    print("✅ 页面加载成功，正在执行JavaScript提取数据...")

    # 增强的JavaScript代码 - 直接提取所有数据
    js_code = """
    console.log("开始提取2022世界杯数据...");

    // 等待页面完全加载
    await new Promise(resolve => setTimeout(resolve, 2000));

    // 1. 首先尝试获取所有运动员行
    var athleteRows = [];

    // 方法1: 尝试多种选择器
    var selectors = [
        'tr.results-table__row.js-results-table-row',
        'tr.results-table__row',
        'tr[class*="results-table__row"]',
        'table tr:not(:first-child)'
    ];

    for (var sel of selectors) {
        var rows = document.querySelectorAll(sel);
        if (rows.length > 0) {
            console.log('使用选择器 "' + sel + '" 找到 ' + rows.length + ' 行');
            athleteRows = Array.from(rows);
            break;
        }
    }

    if (athleteRows.length === 0) {
        console.log('没有找到运动员行，尝试其他方法...');
        // 尝试查找包含运动员信息的表格
        var tables = document.querySelectorAll('table');
        for (var i = 0; i < tables.length; i++) {
            var tableRows = tables[i].querySelectorAll('tr');
            if (tableRows.length > 1) {
                athleteRows = Array.from(tableRows).slice(1); // 跳过标题行
                console.log('从表格 ' + i + ' 中找到 ' + athleteRows.length + ' 行');
                break;
            }
        }
    }

    // 2. 提取比赛信息
    var competitionInfo = {
        title: document.title || '',
        location: '',
        date: ''
    };

    // 尝试查找比赛信息
    var titleElements = document.querySelectorAll('h1, h2');
    for (var el of titleElements) {
        var text = el.textContent.trim();
        if (text.includes('World Cup') || text.includes('Diving') || text.includes('FINA')) {
            competitionInfo.title = text;
            break;
        }
    }

    // 特别查找FINA相关信息（2022年仍使用FINA名称）
    var finaElements = document.querySelectorAll('h3, h4, .competition-header, .event-title');
    for (var el of finaElements) {
        var text = el.textContent.trim();
        if (text.toLowerCase().includes('fina') || text.toLowerCase().includes('world cup')) {
            competitionInfo.title = text;
            console.log('找到比赛标题: ' + text);
            break;
        }
    }

    // 3. 提取运动员数据
    var allData = [];
    var seenAthletes = new Set(); // 用于去重

    for (var i = 0; i < athleteRows.length; i++) {
        var row = athleteRows[i];
        var rowText = row.textContent.trim();

        // 跳过空行
        if (!rowText || rowText.length < 5) continue;

        console.log('处理行 ' + i + ': ' + rowText.substring(0, 50) + '...');

        var athleteData = {};

        // 提取排名（通常是第一个单元格）
        var rankCell = row.querySelector('td:first-child');
        athleteData.rank = rankCell ? rankCell.textContent.trim() : '';

        // 提取运动员姓名
        athleteData.athlete = '';
        var nameSelectors = [
            '.results-table__athlete-first',
            '.athlete-name',
            'td:nth-child(2)',
            'td[class*="athlete"]'
        ];

        for (var sel of nameSelectors) {
            var nameElement = row.querySelector(sel);
            if (nameElement) {
                var nameText = nameElement.textContent.trim();
                if (nameText && !nameText.match(/^\\d+$/)) {
                    athleteData.athlete = nameText;
                    break;
                }
            }
        }

        // 如果还没找到，尝试从行文本中提取
        if (!athleteData.athlete) {
            var textParts = rowText.split(/\\s+/);
            for (var part of textParts) {
                if (part.match(/[A-Z][a-z]+/) && part.length > 2) {
                    athleteData.athlete = part;
                    break;
                }
            }
        }

        // 提取国家
        athleteData.country = '';
        var countrySelectors = [
            '.results-table__country',
            '.country-flag',
            'td:nth-child(3)',
            'img[src*="flag"]'
        ];

        for (var sel of countrySelectors) {
            var countryElement = row.querySelector(sel);
            if (countryElement) {
                athleteData.country = countryElement.textContent.trim() || 
                                     countryElement.getAttribute('alt') || 
                                     countryElement.getAttribute('title') || '';
                if (athleteData.country) break;
            }
        }

        // 提取年龄
        athleteData.age = '';
        var tds = row.querySelectorAll('td');
        for (var j = 0; j < tds.length; j++) {
            var cellText = tds[j].textContent.trim();
            if (/^\\d{1,2}$/.test(cellText)) {
                var ageNum = parseInt(cellText);
                if (ageNum >= 10 && ageNum <= 50) {
                    athleteData.age = cellText;
                    break;
                }
            }
        }

        // 提取总分
        athleteData.points = '';
        var pointsSelectors = [
            'td.results-table__cell.results-table__cell--highlight.black',
            'td.total-points',
            'td:last-child',
            'td:nth-last-child(1)',
            'td:nth-last-child(2)'
        ];

        for (var sel of pointsSelectors) {
            var pointsElement = row.querySelector(sel);
            if (pointsElement) {
                var pointsText = pointsElement.textContent.trim();
                if (pointsText.match(/[\\d.]+/)) {
                    athleteData.points = pointsText;
                    break;
                }
            }
        }

        // 去重：如果运动员姓名和排名相同，跳过
        var athleteKey = athleteData.rank + '_' + athleteData.athlete;
        if (seenAthletes.has(athleteKey) || !athleteData.athlete) {
            console.log('跳过重复或无效的行: ' + athleteKey);
            continue;
        }
        seenAthletes.add(athleteKey);

        // 尝试提取跳水详情（如果有展开行）
        athleteData.diveDetails = [];
        try {
            // 查找展开按钮并点击
            var expandBtn = row.querySelector('button.results-table__expand-btn');
            if (expandBtn) {
                expandBtn.click();
                await new Promise(resolve => setTimeout(resolve, 1000));

                // 查找展开的行
                var nextRow = row.nextElementSibling;
                if (nextRow && nextRow.classList.contains('results-table__expandable')) {
                    var diveRows = nextRow.querySelectorAll('tr.results-table__sub-row');
                    console.log('找到 ' + diveRows.length + ' 个跳水动作');

                    for (var j = 0; j < diveRows.length; j++) {
                        var diveRow = diveRows[j];
                        var diveData = {};

                        // 提取跳水信息
                        var diveCells = diveRow.querySelectorAll('td');
                        if (diveCells.length >= 10) {
                            diveData.diveNum = diveCells[0]?.textContent?.trim() || '';
                            diveData.diveCode = diveCells[1]?.textContent?.trim() || '';
                            diveData.dd = diveCells[2]?.textContent?.trim() || '';

                            // 裁判分数（可能有7个）
                            diveData.judgeScores = [];
                            for (var k = 3; k < Math.min(10, diveCells.length); k++) {
                                diveData.judgeScores.push(diveCells[k]?.textContent?.trim() || '');
                            }

                            // 其他信息
                            if (diveCells.length >= 15) {
                                diveData.divePoints = diveCells[10]?.textContent?.trim() || '';
                                diveData.totalPoints = diveCells[11]?.textContent?.trim() || '';
                                diveData.diveRank = diveCells[12]?.textContent?.trim() || '';
                                diveData.ovRank = diveCells[13]?.textContent?.trim() || '';
                                diveData.pointsBehind = diveCells[14]?.textContent?.trim() || '';
                            }

                            athleteData.diveDetails.push(diveData);
                        }
                    }
                }
            }
        } catch (e) {
            console.log('提取跳水详情时出错: ' + e);
        }

        console.log('提取完成: ' + athleteData.athlete + ' - 排名: ' + athleteData.rank + ' - 分数: ' + athleteData.points);
        allData.push(athleteData);
    }

    console.log('总共提取 ' + allData.length + ' 位运动员数据');
    console.log('比赛信息: ', competitionInfo);

    return {
        competitionInfo: competitionInfo,
        athleteData: allData
    };
    """

    # Execute JavaScript
    print("🔄 正在执行JavaScript代码...")
    result = driver.execute_script(js_code)

    if result is None:
        print("❌ JavaScript执行返回了None，尝试备用方案...")
        # 备用方案：直接解析页面
        page_source = driver.page_source

        # 保存页面源代码用于调试
        with open('2022_worldcup_page_source.html', 'w', encoding='utf-8') as f:
            f.write(page_source)
        print("✅ 2022年页面源代码已保存到 2022_worldcup_page_source.html")

        result = {'competitionInfo': {}, 'athleteData': []}

    competition_info = result.get('competitionInfo', {}) if result else {}
    all_data = result.get('athleteData', []) if result else []

    if all_data:
        print(f"\n🏆 比赛信息:")
        print(f"   • 赛事名称: {competition_info.get('title', 'FINA Diving World Cup 2022')}")
        print(f"   • 比赛地点: {competition_info.get('location', 'N/A')}")
        print(f"   • 比赛时间: {competition_info.get('date', 'N/A')}")

        print(f"\n✅ 成功提取 {len(all_data)} 位运动员的2022世界杯数据")

        # 从比赛信息中识别分站信息
        competition_title = competition_info.get('title', '').lower()
        competition_type = 'Unknown_Stop'  # 默认值

        # 根据标题判断分站
        if 'super final' in competition_title or 'super-final' in competition_title:
            competition_type = 'SuperFinal'
            print(f"🎯 识别为超级决赛")
        elif 'stop' in competition_title:
            import re

            stop_match = re.search(r'stop\s*(\d+)', competition_title, re.IGNORECASE)
            if stop_match:
                competition_type = f"Stop{stop_match.group(1)}"
        elif 'montréal' in competition_title or 'montreal' in competition_title:
            competition_type = 'Montreal'
        elif 'berlin' in competition_title:
            competition_type = 'Berlin'
        elif 'xi\'an' in competition_title or 'xian' in competition_title:
            competition_type = 'Xian'
        elif 'shanghai' in competition_title:
            competition_type = 'Shanghai'
        elif 'fukuoka' in competition_title:
            competition_type = 'Fukuoka'
        elif 'budapest' in competition_title:
            competition_type = 'Budapest'
        elif 'kyiv' in competition_title or 'kiev' in competition_title:
            competition_type = 'Kyiv'
        elif 'windsor' in competition_title:
            competition_type = 'Windsor'

        # 根据URL判断
        if '3012' in url:  # 2022年世界杯ID
            # 根据event ID进一步判断
            if 'fe8f025e-d2b2-498b-a433-8498527c5cee' in url:
                # 这是一个具体的分站，需要进一步判断是哪个分站
                competition_type = 'Stop1'  # 暂时设为分站1

        # Process data
        athlete_list = []
        dive_list = []

        for athlete in all_data:
            # 确保数据有效性
            if not athlete.get('athlete') or not athlete.get('rank'):
                print(f"跳过无效数据: {athlete}")
                continue

            # Save athlete information
            athlete_list.append({
                'Rank': athlete.get('rank', ''),
                'Athlete': athlete.get('athlete', ''),
                'Age': athlete.get('age', ''),
                'Country': athlete.get('country', ''),
                'Total_Points': athlete.get('points', ''),
                'Competition': competition_info.get('title', 'FINA Diving World Cup 2022'),
                'Competition_Type': competition_type,
                'Location': competition_info.get('location', 'N/A'),
                'Date': competition_info.get('date', 'N/A')
            })

            # Save detailed diving information
            dive_details = athlete.get('diveDetails', [])
            if dive_details:
                for dive in dive_details:
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
                        'Competition': competition_info.get('title', 'FINA Diving World Cup 2022'),
                        'Competition_Type': competition_type,
                        'Location': competition_info.get('location', 'N/A'),
                        'Date': competition_info.get('date', 'N/A')
                    })
            else:
                print(f"⚠️ 运动员 {athlete.get('athlete', '')} 没有提取到跳水详细数据")

        # 去重：删除重复的运动员数据
        unique_athletes = []
        seen = set()
        for athlete in athlete_list:
            key = (athlete['Rank'], athlete['Athlete'], athlete['Country'])
            if key not in seen:
                seen.add(key)
                unique_athletes.append(athlete)
            else:
                print(f"删除重复数据: {athlete['Athlete']} (排名: {athlete['Rank']})")

        athlete_list = unique_athletes

        # Save to CSV files
        athletes_filename = ""
        dives_filename = ""

        if athlete_list:
            df_athletes = pd.DataFrame(athlete_list)
            athletes_filename = f"2022_WorldCup_Women10m_{competition_type}_Athlete_Rankings.csv"
            df_athletes.to_csv(athletes_filename, index=False, encoding='utf-8-sig')
            print(f"\n✅ 2022世界杯分站赛运动员排名已保存为CSV: {athletes_filename}")
            print(f"📋 数据概览:")
            print(f"   - 总记录数: {len(df_athletes)}")
            print(f"   - 有分数的运动员: {df_athletes['Total_Points'].notna().sum()}")
            print(f"   - 有年龄的运动员: {df_athletes['Age'].notna().sum()}")
            print(f"📊 前10条数据:")
            print(df_athletes.head(10))

        if dive_list:
            df_dives = pd.DataFrame(dive_list)
            dives_filename = f"2022_WorldCup_Women10m_{competition_type}_Detailed_Scores.csv"
            df_dives.to_csv(dives_filename, index=False, encoding='utf-8-sig')
            print(f"\n✅ 2022世界杯分站赛详细跳水分数已保存为CSV: {dives_filename}")
            print(f"📊 总计 {len(dive_list)} 条跳水记录")
            if len(dive_list) > 0:
                print(f"📊 前5条跳水数据:")
                print(df_dives.head(5))
        else:
            print("\n⚠️ 没有提取到跳水详细数据")
            dives_filename = f"2022_WorldCup_Women10m_{competition_type}_Detailed_Scores.csv"
            pd.DataFrame().to_csv(dives_filename, index=False)
            print(f"⚠️ 创建了空的跳水分数文件: {dives_filename}")

        # Display statistics
        print(f"\n📈 2022世界杯数据提取统计:")
        print(f"  🏊 运动员数量: {len(athlete_list)}")
        print(f"  💦 跳水动作总数: {len(dive_list)}")
        print(f"  🏆 比赛类型: {competition_type}")
        print(f"  📅 赛事年份: 2022 (FINA时期)")

        # 显示年龄统计
        ages = [a['Age'] for a in athlete_list if a['Age']]
        if ages:
            age_nums = [int(age) for age in ages if age.isdigit()]
            if age_nums:
                print(f"  📅 年龄统计:")
                print(f"    • 最年轻运动员: {min(age_nums)} 岁")
                print(f"    • 最年长运动员: {max(age_nums)} 岁")
                print(f"    • 平均年龄: {sum(age_nums) / len(age_nums):.1f} 岁")

        # 显示总分统计
        try:
            valid_scores = []
            for a in athlete_list:
                if a['Total_Points']:
                    score_str = str(a['Total_Points']).strip()
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
                    print(f"\n🥇 奖牌获得者:")
                    sorted_athletes = sorted(athlete_list,
                                             key=lambda x: float(x['Total_Points']) if x['Total_Points'] and str(
                                                 x['Total_Points']).replace('.', '').isdigit() else 0,
                                             reverse=True)[:3]
                    medals = ['🥇', '🥈', '🥉']
                    for i, athlete in enumerate(sorted_athletes):
                        print(f"    {medals[i]} {athlete['Athlete']} ({athlete['Country']}): {athlete['Total_Points']}")
        except Exception as e:
            print(f"  ⚠️ 分数统计错误: {e}")

        # 显示国家分布
        if athlete_list:
            from collections import Counter

            countries = Counter([a['Country'] for a in athlete_list if a['Country']])
            print(f"\n🌍 国家分布 ({len(countries)} 个国家):")
            for country, count in countries.most_common():
                print(f"    • {country}: {count} 位运动员")

        # 显示文件保存位置
        import os

        current_dir = os.getcwd()
        print(f"\n📁 输出文件保存位置:")
        print(f"    • 当前工作目录: {current_dir}")
        if athletes_filename:
            print(f"    • {athletes_filename}")
        if dives_filename:
            print(f"    • {dives_filename}")

        print(f"\n📝 2022年比赛特点:")
        print(f"    • 这是FINA组织的最后一届跳水世界杯")
        print(f"    • 2022年12月FINA更名为World Aquatics")
        print(f"    • 比赛名称仍使用'FINA Diving World Cup'")

    else:
        print("❌ 未提取到有效的运动员数据")
        print("💡 建议:")
        print("   1. 检查页面是否正常加载")
        print("   2. 尝试增加等待时间")
        print("   3. 检查选择器是否匹配页面结构")
        print("   4. 查看保存的页面源代码文件: 2022_worldcup_page_source.html")

except Exception as e:
    print(f"❌ 提取数据时出错: {e}")
    print(f"❌ 错误类型: {type(e).__name__}")

    # 如果是ChromeDriver相关错误，给出更多信息
    if "chromedriver" in str(e).lower() or "service" in str(e).lower():
        print("\n🔧 ChromeDriver问题排查:")
        print("   1. 确认ChromeDriver路径正确: D:\\chromedriver\\chromedriver.exe")
        print("   2. 确认Chrome浏览器已安装")
        print("   3. 确认ChromeDriver版本与Chrome浏览器版本匹配")

    import traceback

    traceback.print_exc()

finally:
    # 关闭浏览器
    try:
        driver.quit()
        print("✅ 浏览器已关闭")
    except:
        pass

    print("\n🎉 2022世界杯女子10米跳台数据提取完成!")
    print("📅 注: 2022年比赛由FINA组织，后更名为World Aquatics")
    print("=" * 60)