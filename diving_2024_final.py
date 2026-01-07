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

print("=== 2024 World Cup Women's 10m Platform Super Final Data Extraction ===")

# Configure Chrome Driver
CHROME_DRIVER_PATH = r'D:\chromedriver\chromedriver.exe'

chrome_options = Options()
chrome_options.add_argument('--headless')
chrome_options.add_argument('--disable-gpu')
chrome_options.add_argument('--no-sandbox')
chrome_options.add_argument('--disable-dev-shm-usage')
chrome_options.add_argument('--log-level=3')

# 如果需要看到浏览器界面，注释掉下面的headless选项
# chrome_options.add_argument('--headless')

service = Service(CHROME_DRIVER_PATH)
driver = webdriver.Chrome(service=service, options=chrome_options)

# 2024年世界杯超级决赛 URL
url = "https://www.worldaquatics.com/competitions/3378/world-aquatics-diving-world-cup-2024-super-final/results?event=a4491926-bdf7-4d1b-8dcc-c4613a0ab206&unit=finals"

print(f"🌐 Extracting data from: 2024 World Cup Women's 10m Platform SUPER FINAL")
print(f"🔗 URL: {url}")
print(f"🚀 ChromeDriver路径: {CHROME_DRIVER_PATH}")
print(f"📅 Competition: World Aquatics Diving World Cup 2024 - Super Final")
print(f"🏆 Event: Women's 10m Platform - FINALS")
print(f"📝 Note: This is 2024 competition data")

try:
    print("🔄 Starting Chrome browser...")
    driver.get(url)
    print("✅ Page loading...")

    # 增加等待时间确保页面完全加载
    time.sleep(10)

    print("✅ Page loaded successfully, trying to extract data...")

    # 保存页面源代码以便调试
    with open('2024_worldcup_superfinal_page_source.html', 'w', encoding='utf-8') as f:
        f.write(driver.page_source)
    print("✅ Page source saved for debugging")

    # 方法1: 使用Selenium直接查找元素
    print("🔄 Trying to find data with Selenium...")

    # 等待页面加载
    wait = WebDriverWait(driver, 20)

    # 尝试查找比赛标题
    competition_info = {
        'title': '',
        'eventName': '',
        'location': '',
        'date': ''
    }

    try:
        # 尝试获取比赛标题
        title_elements = driver.find_elements(By.TAG_NAME, 'h1')
        for element in title_elements:
            text = element.text.strip()
            if text:
                competition_info['title'] = text
                print(f"Found title: {text}")
                break
    except:
        pass

    # 尝试直接查找表格数据
    all_data = []

    # 查找所有表格行
    try:
        rows = driver.find_elements(By.CSS_SELECTOR, 'tr.results-table__row')
        if not rows:
            rows = driver.find_elements(By.CSS_SELECTOR, 'tr[class*="row"]')
        if not rows:
            rows = driver.find_elements(By.TAG_NAME, 'tr')

        print(f"Found {len(rows)} table rows")

        for i, row in enumerate(rows):
            try:
                row_text = row.text.strip()
                if not row_text or len(row_text) < 5:
                    continue

                # 跳过表头行
                if row_text.lower().startswith(('rank', 'athlete', 'total', '#')):
                    continue

                # 分解行数据
                cells = row.find_elements(By.TAG_NAME, 'td')
                if len(cells) >= 4:
                    athlete_data = {
                        'rank': cells[0].text.strip() if len(cells) > 0 else '',
                        'athlete': cells[1].text.strip() if len(cells) > 1 else '',
                        'country': cells[2].text.strip() if len(cells) > 2 else '',
                        'points': cells[3].text.strip() if len(cells) > 3 else '',
                        'age': '',
                        'diveDetails': []
                    }

                    # 尝试提取年龄
                    for cell in cells:
                        cell_text = cell.text.strip()
                        if cell_text.isdigit() and 10 <= int(cell_text) <= 50:
                            athlete_data['age'] = cell_text
                            break

                    all_data.append(athlete_data)
                    print(
                        f"Extracted athlete {i + 1}: {athlete_data.get('athlete', 'Unknown')} - Rank: {athlete_data.get('rank', 'N/A')}")

            except Exception as e:
                print(f"Error processing row {i}: {e}")
                continue

    except Exception as e:
        print(f"Error finding rows: {e}")

    # 如果没找到数据，尝试备用方法
    if not all_data:
        print("⚠️ No data found with direct method, trying JavaScript...")

        # 简单的JavaScript提取
        simple_js = """
        console.log("Starting simple data extraction...");

        var result = {
            competitionInfo: {
                title: document.title || '',
                eventName: document.querySelector('h1, h2, h3')?.textContent || ''
            },
            athleteData: []
        };

        // 查找所有可能的数据行
        var rows = document.querySelectorAll('tr, div[class*="row"], div[class*="result"]');
        console.log("Found " + rows.length + " potential rows");

        for (var i = 0; i < rows.length; i++) {
            try {
                var row = rows[i];
                var text = row.textContent.trim();

                // 跳过空行或标题行
                if (!text || text.length < 5 || 
                    text.toLowerCase().includes('rank') || 
                    text.toLowerCase().includes('athlete') ||
                    text.toLowerCase().includes('total') ||
                    text.includes('#') && text.length < 10) {
                    continue;
                }

                // 尝试提取排名和姓名
                var rankMatch = text.match(/^(\d+)/);
                var athleteMatch = text.match(/[A-Z][a-z]+\s+[A-Z][a-z]+/);

                if (rankMatch || athleteMatch) {
                    var athleteData = {
                        rank: rankMatch ? rankMatch[1] : '',
                        athlete: athleteMatch ? athleteMatch[0] : '',
                        country: '',
                        points: '',
                        age: '',
                        diveDetails: []
                    };

                    // 尝试提取国家代码
                    var countryMatch = text.match(/\s([A-Z]{2,3})\s/);
                    if (countryMatch) {
                        athleteData.country = countryMatch[1];
                    }

                    // 尝试提取分数
                    var pointsMatch = text.match(/(\d+\.?\d*)\s*$/);
                    if (pointsMatch) {
                        athleteData.points = pointsMatch[1];
                    }

                    console.log("Extracted: " + athleteData.athlete + " - " + athleteData.rank);
                    result.athleteData.push(athleteData);
                }
            } catch(e) {
                console.log("Error processing row: " + e);
            }
        }

        console.log("Total athletes extracted: " + result.athleteData.length);
        return result;
        """

        try:
            result = driver.execute_script(simple_js)
            if result:
                competition_info.update(result.get('competitionInfo', {}))
                all_data = result.get('athleteData', [])
                print(f"JavaScript extraction found {len(all_data)} athletes")
        except Exception as e:
            print(f"JavaScript execution error: {e}")

    # 显示比赛信息
    title = competition_info.get('title', 'World Aquatics Diving World Cup 2024 - Super Final')
    event_name = competition_info.get('eventName', "Women's 10m Platform - Finals")
    location = competition_info.get('location', '待确认')
    date = competition_info.get('date', '2024年')

    print(f"\n🏆 比赛信息:")
    print(f"   • 赛事名称: {title}")
    print(f"   • 事件名称: {event_name}")
    print(f"   • 比赛地点: {location}")
    print(f"   • 比赛时间: {date}")

    if all_data:
        print(f"\n✅ Successfully extracted data for {len(all_data)} athletes from 2024 World Cup Super Final")

        competition_type = 'SuperFinal2024'
        print(f"🎯 Identified as: 2024 World Cup Super Final")

        athlete_list = []
        dive_list = []

        for athlete in all_data:
            if not athlete.get('athlete') and not athlete.get('rank'):
                print(f"Skipping invalid data: {athlete}")
                continue

            athlete_list.append({
                'Rank': athlete.get('rank', ''),
                'Athlete': athlete.get('athlete', ''),
                'Age': athlete.get('age', ''),
                'Country': athlete.get('country', ''),
                'Total_Points': athlete.get('points', ''),
                'Competition': title,
                'Competition_Type': competition_type,
                'Event_Name': event_name,
                'Location': location,
                'Date': date,
                'Year': '2024'
            })

            # 如果没有详细的跳水数据，创建空记录
            dive_details = athlete.get('diveDetails', [])
            if not dive_details:
                # 为每位运动员创建5个跳水动作的占位数据
                for idx in range(1, 6):
                    dive_list.append({
                        'Athlete_Rank': athlete.get('rank', ''),
                        'Athlete_Name': athlete.get('athlete', ''),
                        'Country': athlete.get('country', ''),
                        'Dive_Number': idx,
                        'Dive_Code': '',
                        'Difficulty_Degree': '',
                        'Judge1': '',
                        'Judge2': '',
                        'Judge3': '',
                        'Judge4': '',
                        'Judge5': '',
                        'Judge6': '',
                        'Judge7': '',
                        'Dive_Points': '',
                        'Cumulative_Total': '',
                        'Competition': title,
                        'Competition_Type': competition_type,
                        'Event_Name': event_name,
                        'Location': location,
                        'Date': date,
                        'Year': '2024'
                    })

        # 去重
        unique_athletes = []
        seen = set()
        for athlete in athlete_list:
            key = (athlete['Rank'], athlete['Athlete'], athlete['Country'])
            if key not in seen:
                seen.add(key)
                unique_athletes.append(athlete)

        athlete_list = unique_athletes

        athletes_filename = ""
        dives_filename = ""

        if athlete_list:
            df_athletes = pd.DataFrame(athlete_list)
            athletes_filename = f"2024_WorldCup_Women10m_{competition_type}_Athlete_Rankings.csv"
            df_athletes.to_csv(athletes_filename, index=False, encoding='utf-8-sig')
            print(f"\n✅ 2024 Super Final athlete rankings saved as CSV: {athletes_filename}")
            print(f"📋 Data overview:")
            print(f"   - Total records: {len(df_athletes)}")
            print(f"   - Athletes with scores: {df_athletes['Total_Points'].notna().sum()}")
            print(f"📊 Top 10 records:")
            print(df_athletes.head(10))

        if dive_list:
            df_dives = pd.DataFrame(dive_list)
            dives_filename = f"2024_WorldCup_Women10m_{competition_type}_Detailed_Scores.csv"
            df_dives.to_csv(dives_filename, index=False, encoding='utf-8-sig')
            print(f"\n✅ 2024 Super Final detailed dive scores saved as CSV: {dives_filename}")
            print(f"📊 Total {len(dive_list)} dive records")
            if len(dive_list) > 0:
                print(f"📊 Top 5 dive records:")
                print(df_dives.head(5))
        else:
            print("\n⚠️ No detailed dive data extracted")
            dives_filename = f"2024_WorldCup_Women10m_{competition_type}_Detailed_Scores.csv"
            pd.DataFrame().to_csv(dives_filename, index=False)
            print(f"⚠️ Created empty dive scores file: {dives_filename}")

        print(f"\n📈 2024 World Cup Super Final Data Extraction Statistics:")
        print(f"  🏊 Number of athletes: {len(athlete_list)}")
        print(f"  💦 Total dive actions: {len(dive_list)}")
        print(f"  🏆 Competition type: {competition_type}")
        print(f"  📅 Year: 2024")
        print(f"  🌟 Event level: Super Final (highest level)")

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
                print(f"  🏆 Total Score Statistics:")
                print(f"    • Highest total score: {max(valid_scores):.1f}")
                print(f"    • Lowest total score: {min(valid_scores):.1f}")
                print(f"    • Average total score: {sum(valid_scores) / len(valid_scores):.1f}")

                if len(athlete_list) >= 3:
                    print(f"\n🥇 Medalists:")
                    sorted_athletes = sorted(athlete_list,
                                             key=lambda x: float(x['Total_Points']) if x['Total_Points'] and str(
                                                 x['Total_Points']).replace('.', '').isdigit() else 0,
                                             reverse=True)[:3]
                    medals = ['🥇', '🥈', '🥉']
                    for i, athlete in enumerate(sorted_athletes):
                        print(f"    {medals[i]} {athlete['Athlete']} ({athlete['Country']}): {athlete['Total_Points']}")
        except Exception as e:
            print(f"  ⚠️ Score statistics error: {e}")

        if athlete_list:
            from collections import Counter

            countries = Counter([a['Country'] for a in athlete_list if a['Country']])
            print(f"\n🌍 Country distribution ({len(countries)} countries):")
            for country, count in countries.most_common(10):
                print(f"    • {country}: {count} athletes")

        import os

        current_dir = os.getcwd()
        print(f"\n📁 Output file locations:")
        print(f"    • Current working directory: {current_dir}")
        if athletes_filename:
            print(f"    • {athletes_filename}")
        if dives_filename:
            print(f"    • {dives_filename}")

        print(f"\n🏅 2024 Super Final Features:")
        print(f"    • This is the final of the 2024 Diving World Cup")
        print(f"    • Key event before the Paris Olympics")
        print(f"    • Participants include world top divers")

    else:
        print("❌ No valid athlete data extracted")
        print("💡 Suggestions:")
        print("   1. Check if the page loaded properly")
        print("   2. Try increasing wait time")
        print("   3. Check the saved page source file: 2024_worldcup_superfinal_page_source.html")
        print("   4. Try running without headless mode to see what's displayed")

except Exception as e:
    print(f"❌ Error extracting data: {e}")
    print(f"❌ Error type: {type(e).__name__}")

    if "chromedriver" in str(e).lower() or "service" in str(e).lower():
        print("\n🔧 ChromeDriver troubleshooting:")
        print("   1. Confirm ChromeDriver path is correct: D:\\chromedriver\\chromedriver.exe")
        print("   2. Confirm Chrome browser is installed")
        print("   3. Confirm ChromeDriver version matches Chrome browser version")

    import traceback

    traceback.print_exc()

finally:
    try:
        driver.quit()
        print("✅ Browser closed")
    except:
        pass

    print("\n🎉 2024 World Cup Women's 10m Platform Super Final data extraction completed!")
    print("=" * 60)