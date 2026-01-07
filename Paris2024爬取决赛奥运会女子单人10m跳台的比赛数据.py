import time
import pandas as pd
from selenium import webdriver
from selenium.webdriver.edge.service import Service
from selenium.webdriver.edge.options import Options
import mysql.connector
from mysql.connector import Error
import warnings

warnings.filterwarnings('ignore')

print("=== Paris 2024 Women's 10m Platform Final Data Extraction ===")

# 数据库配置
DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "root123456",
    "database": "OlympicDiving"
}

# Configure Edge Driver
EDGE_DRIVER_PATH = "/usr/local/bin/msedgedriver"

edge_options = Options()
edge_options.add_argument('--headless')  # Headless mode, no browser window
edge_options.add_argument('--disable-gpu')

service = Service(EDGE_DRIVER_PATH)
driver = webdriver.Edge(service=service, options=edge_options)

url = "https://www.worldaquatics.com/competitions/2943/olympic-games-paris-2024/results?disciplines=&event=9640d00d-e468-48d4-b47b-cf81ddb83f29&unit=finals"

print(f"🌐 Extracting data from: Paris 2024 Women's 10m Platform FINAL")
print(f"🔗 URL: {url}")


def create_database_connection():
    """创建数据库连接"""
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        if connection.is_connected():
            db_info = connection.get_server_info()
            print(f"✅ Connected to MySQL Server version: {db_info}")
            print(f"✅ Using database: {DB_CONFIG['database']}")
            return connection
    except Error as e:
        print(f"❌ Error connecting to MySQL database: {e}")
        print(f"❌ Check if database '{DB_CONFIG['database']}' exists and credentials are correct")
        return None


def check_database_exists(connection):
    """检查数据库是否存在，如果不存在则创建"""
    try:
        cursor = connection.cursor()

        # 检查数据库是否存在
        cursor.execute(f"SHOW DATABASES LIKE '{DB_CONFIG['database']}'")
        result = cursor.fetchone()

        if not result:
            print(f"⚠️ Database '{DB_CONFIG['database']}' does not exist, creating it...")
            cursor.execute(f"CREATE DATABASE {DB_CONFIG['database']}")
            cursor.execute(f"USE {DB_CONFIG['database']}")
            connection.commit()
            print(f"✅ Database '{DB_CONFIG['database']}' created successfully")
        else:
            cursor.execute(f"USE {DB_CONFIG['database']}")
            print(f"✅ Database '{DB_CONFIG['database']}' exists and selected")

        cursor.close()
        return True

    except Error as e:
        print(f"❌ Error checking/creating database: {e}")
        return False


def create_tables(connection):
    """创建数据表 - 2024_Paris FINAL"""
    try:
        cursor = connection.cursor()

        # 创建运动员排名表 - 2024_Paris FINAL（包含Age和Olympic_Games字段）
        athlete_table_sql = """
        CREATE TABLE IF NOT EXISTS `2024_Paris_Women10m_FINAL_Athlete_Rankings` (
            id INT AUTO_INCREMENT PRIMARY KEY,
            `Rank` VARCHAR(10),
            Athlete VARCHAR(100),
            Age VARCHAR(10),
            Country VARCHAR(50),
            Total_Points VARCHAR(20),
            Competition_Phase VARCHAR(10) DEFAULT 'FINAL',
            Olympic_Games VARCHAR(20) DEFAULT '2024_Paris',
            extraction_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """

        # 创建跳水详细分数表 - 2024_Paris FINAL（包含Olympic_Games字段）
        dive_table_sql = """
        CREATE TABLE IF NOT EXISTS `2024_Paris_Women10m_FINAL_Detailed_Scores` (
            id INT AUTO_INCREMENT PRIMARY KEY,
            Athlete_Rank VARCHAR(10),
            Athlete_Name VARCHAR(100),
            Country VARCHAR(50),
            Dive_Number VARCHAR(10),
            Dive_Code VARCHAR(20),
            Difficulty_Degree VARCHAR(10),
            Judge1 VARCHAR(10),
            Judge2 VARCHAR(10),
            Judge3 VARCHAR(10),
            Judge4 VARCHAR(10),
            Judge5 VARCHAR(10),
            Judge6 VARCHAR(10),
            Judge7 VARCHAR(10),
            Dive_Points VARCHAR(10),
            Cumulative_Total VARCHAR(20),
            Dive_Rank VARCHAR(10),
            Overall_Rank VARCHAR(10),
            Points_Behind VARCHAR(20),
            Competition_Phase VARCHAR(10) DEFAULT 'FINAL',
            Olympic_Games VARCHAR(20) DEFAULT '2024_Paris',
            extraction_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """

        cursor.execute(athlete_table_sql)
        cursor.execute(dive_table_sql)
        connection.commit()
        print("✅ 2024_Paris FINAL Database tables created/verified successfully")

        # 检查表结构
        cursor.execute("SHOW TABLES")
        tables = cursor.fetchall()
        print(f"📊 Available tables in database '{DB_CONFIG['database']}':")
        for table in tables:
            print(f"  - {table[0]}")

        cursor.close()

    except Error as e:
        print(f"❌ Error creating tables: {e}")


def save_to_database(connection, athlete_list, dive_list):
    """保存数据到数据库 - 2024_Paris FINAL"""
    try:
        cursor = connection.cursor()

        # 首先检查表是否存在，如果不存在则创建
        cursor.execute("SHOW TABLES LIKE '2024_Paris_Women10m_FINAL_Athlete_Rankings'")
        if not cursor.fetchone():
            print("⚠️ 2024_Paris FINAL tables not found, creating tables...")
            create_tables(connection)

        # 清空现有2024_Paris FINAL数据
        print("🔄 Clearing existing 2024_Paris FINAL data from tables...")
        cursor.execute(
            "DELETE FROM `2024_Paris_Women10m_FINAL_Athlete_Rankings` WHERE Olympic_Games = '2024_Paris' AND Competition_Phase = 'FINAL'")
        cursor.execute(
            "DELETE FROM `2024_Paris_Women10m_FINAL_Detailed_Scores` WHERE Olympic_Games = '2024_Paris' AND Competition_Phase = 'FINAL'")

        # 插入运动员排名数据 - 2024_Paris FINAL
        athlete_insert_sql = """
        INSERT INTO `2024_Paris_Women10m_FINAL_Athlete_Rankings` 
        (`Rank`, Athlete, Age, Country, Total_Points, Competition_Phase, Olympic_Games)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """

        athlete_data = [(a['Rank'], a['Athlete'], a['Age'], a['Country'], a['Total_Points'], 'FINAL', '2024_Paris')
                        for a in athlete_list]

        if athlete_data:
            cursor.executemany(athlete_insert_sql, athlete_data)
            print(f"✅ Saved {len(athlete_data)} athlete records to 2024_Paris FINAL database")

        # 插入跳水详细分数数据 - 2024_Paris FINAL
        dive_insert_sql = """
        INSERT INTO `2024_Paris_Women10m_FINAL_Detailed_Scores` 
        (Athlete_Rank, Athlete_Name, Country, Dive_Number, Dive_Code, 
         Difficulty_Degree, Judge1, Judge2, Judge3, Judge4, Judge5, Judge6, Judge7,
         Dive_Points, Cumulative_Total, Dive_Rank, Overall_Rank, Points_Behind, Competition_Phase, Olympic_Games)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """

        dive_data = []
        for dive in dive_list:
            dive_tuple = (
                dive['Athlete_Rank'], dive['Athlete_Name'], dive['Country'],
                dive['Dive_Number'], dive['Dive_Code'], dive['Difficulty_Degree'],
                dive['Judge1'], dive['Judge2'], dive['Judge3'], dive['Judge4'],
                dive['Judge5'], dive['Judge6'], dive['Judge7'],
                dive['Dive_Points'], dive['Cumulative_Total'],
                dive['Dive_Rank'], dive['Overall_Rank'], dive['Points_Behind'],
                'FINAL', '2024_Paris'
            )
            dive_data.append(dive_tuple)

        if dive_data:
            cursor.executemany(dive_insert_sql, dive_data)
            print(f"✅ Saved {len(dive_data)} dive records to 2024_Paris FINAL database")

        connection.commit()
        cursor.close()

        # 显示数据库统计
        cursor = connection.cursor()
        cursor.execute(
            "SELECT COUNT(*) FROM `2024_Paris_Women10m_FINAL_Athlete_Rankings` WHERE Olympic_Games = '2024_Paris' AND Competition_Phase = 'FINAL'")
        athlete_count = cursor.fetchone()[0]

        cursor.execute(
            "SELECT COUNT(*) FROM `2024_Paris_Women10m_FINAL_Detailed_Scores` WHERE Olympic_Games = '2024_Paris' AND Competition_Phase = 'FINAL'")
        dive_count = cursor.fetchone()[0]

        print(f"\n📊 2024_Paris FINAL Database Statistics:")
        print(f"  Athlete records in 2024_Paris FINAL database: {athlete_count}")
        print(f"  Dive records in 2024_Paris FINAL database: {dive_count}")

        cursor.close()

    except Error as e:
        print(f"❌ Error saving data to database: {e}")
        import traceback
        traceback.print_exc()


try:
    # 创建数据库连接
    db_connection = create_database_connection()
    if db_connection:
        # 检查并选择数据库
        if check_database_exists(db_connection):
            create_tables(db_connection)
        else:
            print("⚠️  Database setup failed, only CSV files will be saved")

    # 网页数据提取部分
    driver.get(url)
    time.sleep(8)  # Wait for page to fully load

    print("Page loaded successfully, executing JavaScript to extract 2024_Paris FINAL data...")

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

    // 2. Extract all data
    var allData = [];

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

    return allData;
    """

    # Execute JavaScript
    print("Executing JavaScript code...")
    all_data = driver.execute_script(js_code)

    if all_data:
        print(f"Successfully extracted 2024_Paris FINAL data for {len(all_data)} athletes")

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
                'Total_Points': athlete.get('points', '')
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
                    'Points_Behind': dive.get('pointsBehind', '')
                })

        # 1. Save to CSV files - 2024_Paris FINAL
        if athlete_list:
            df_athletes = pd.DataFrame(athlete_list)
            athletes_filename = "2024_Paris_Women10m_FINAL_Athlete_Rankings.csv"
            df_athletes.to_csv(athletes_filename, index=False, encoding='utf-8-sig')
            print(f"✅ 2024_Paris FINAL athlete rankings saved to CSV: {athletes_filename}")
            print(f"📋 CSV columns: {df_athletes.columns.tolist()}")
            print(f"📊 Sample data with Age:")
            print(df_athletes[['Rank', 'Athlete', 'Age', 'Country', 'Total_Points']].head())

        if dive_list:
            df_dives = pd.DataFrame(dive_list)
            dives_filename = "2024_Paris_Women10m_FINAL_Detailed_Scores.csv"
            df_dives.to_csv(dives_filename, index=False, encoding='utf-8-sig')
            print(f"✅ 2024_Paris FINAL detailed diving scores saved to CSV: {dives_filename}")
            print(f"📊 2024_Paris FINAL total {len(dive_list)} records ({len(all_data)} athletes × 5 dives each)")

        # 2. Save to database - 2024_Paris FINAL
        if db_connection and db_connection.is_connected():
            save_to_database(db_connection, athlete_list, dive_list)
        else:
            print("⚠️  Database connection failed, only CSV files were saved")

        # Display statistics
        print(f"\n📈 2024_Paris FINAL Data Extraction Statistics:")
        print(f"  Number of athletes in 2024_Paris FINAL: {len(all_data)}")
        print(f"  Total number of dives in 2024_Paris FINAL: {len(dive_list)}")

        # 显示年龄统计
        ages = [a['Age'] for a in athlete_list if a['Age']]
        if ages:
            print(f"  Athletes with age data: {len(ages)}/{len(athlete_list)}")
            age_nums = [int(age) for age in ages if age.isdigit()]
            if age_nums:
                print(f"  Youngest athlete: {min(age_nums)} years")
                print(f"  Oldest athlete: {max(age_nums)} years")
                print(f"  Average age: {sum(age_nums) / len(age_nums):.1f} years")

        try:
            valid_scores = [float(a['Total_Points']) for a in athlete_list
                            if a['Total_Points'] and a['Total_Points'].replace('.', '').replace('-', '').isdigit()]
            if valid_scores:
                print(f"  Highest total score in 2024_Paris FINAL: {max(valid_scores):.1f}")
        except:
            print(f"  Highest total score in 2024_Paris FINAL: Calculation error")

    else:
        print("No 2024_Paris FINAL data extracted")

except Exception as e:
    print(f"Error extracting 2024_Paris FINAL data: {e}")
    import traceback

    traceback.print_exc()

finally:
    # 关闭数据库连接
    if 'db_connection' in locals() and db_connection and db_connection.is_connected():
        db_connection.close()
        print("✅ Database connection closed")

    # 关闭浏览器
    driver.quit()
    print("✅ Browser closed")
    print("🎉 2024_Paris FINAL data extraction and storage completed!")