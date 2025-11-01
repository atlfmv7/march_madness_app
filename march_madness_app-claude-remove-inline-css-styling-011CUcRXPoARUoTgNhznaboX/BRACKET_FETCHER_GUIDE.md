# Bracket Fetcher Guide

## 🏀 Auto-Fetch Tournament Bracket

This tool automatically populates your database with the complete NCAA Tournament bracket after Selection Sunday.

---

## 📋 **What It Does**

1. **Fetches** all 64-68 teams with seeds and regions
2. **Creates** all 63+ games with proper round structure  
3. **Links** games so winners advance automatically
4. **Validates** bracket has correct structure (16 teams per region)

---

## 🚀 **Quick Start**

### **Step 1: Install Dependencies**

```bash
pip install beautifulsoup4
# Or update all:
pip install -r requirements.txt
```

### **Step 2: Fetch the Bracket**

```bash
# After Selection Sunday 2025 (March 16):
python fetch_bracket.py --year 2025

# Test with 2024 data (available now):
python fetch_bracket.py --year 2024

# Preview without saving (dry run):
python fetch_bracket.py --year 2024 --dry-run
```

---

## 📁 **CSV Import Method**

If the API fetch doesn't work, you can import from CSV:

### **Step 1: Create CSV File**

Use the template provided: `bracket_template_2024.csv`

**Format:**
```csv
team_name,seed,region
Duke,1,East
Vermont,16,East
Kentucky,2,East
...
```

**Requirements:**
- Exactly 64 teams (or 68 if including First Four)
- 16 teams per region (East, West, South, Midwest)
- Seeds 1-16 in each region

### **Step 2: Import CSV**

```bash
python fetch_bracket.py --year 2025 --csv my_bracket_2025.csv
```

---

## 📊 **How to Get Bracket Data**

### **Option A: Sports Reference (Easiest)**

After Selection Sunday, visit:
- https://www.sports-reference.com/cbb/postseason/2025-ncaa.html

The script will automatically scrape this page!

### **Option B: ESPN Tournament Challenge**

1. Visit: https://fantasy.espn.com/tournament-challenge-bracket/2025
2. View the bracket
3. The script attempts to fetch from their API

### **Option C: Manual CSV**

1. After Selection Sunday, get the official bracket from:
   - NCAA.com
   - ESPN.com
   - CBS Sports
   - Your local newspaper

2. Fill in `bracket_2025.csv` with the 64 teams

3. Import: `python fetch_bracket.py --year 2025 --csv bracket_2025.csv`

---

## 🔍 **Standard NCAA Bracket Structure**

The fetcher creates this structure automatically:

### **Rounds:**
- **Round of 64:** 32 games (8 per region)
- **Round of 32:** 16 games (4 per region)
- **Sweet 16:** 8 games (2 per region)
- **Elite 8:** 4 games (1 per region - regional finals)
- **Final Four:** 2 games
- **Championship:** 1 game

### **Standard Matchups (by seed):**
Each region has these matchups in Round of 64:
- 1 vs 16
- 8 vs 9
- 5 vs 12
- 4 vs 13
- 6 vs 11
- 3 vs 14
- 7 vs 10
- 2 vs 15

---

## ✅ **Verification**

After running the fetcher, verify it worked:

### **1. Check Database**

```bash
sqlite3 instance/mmm.db
```

```sql
-- Count teams (should be 64)
SELECT COUNT(*) FROM team WHERE year = 2025;

-- Count games (should be 63)
SELECT COUNT(*) FROM game WHERE year = 2025;

-- View teams by region
SELECT region, COUNT(*) FROM team WHERE year = 2025 GROUP BY region;

-- View games by round
SELECT round, COUNT(*) FROM game WHERE year = 2025 GROUP BY round;
```

### **2. Check Web Interface**

```bash
python app.py
# Visit: http://localhost:5000
```

You should see:
- All 4 regions with teams
- Round of 64 games with correct matchups
- No teams assigned to owners yet (that's next!)

---

## 🐛 **Troubleshooting**

### **Issue: "Could not fetch bracket from any source"**

**Cause:** Bracket not published yet or API changed

**Solutions:**
1. Wait until after Selection Sunday
2. Use CSV import method
3. Check if year is correct

### **Issue: "Invalid bracket: Region X has Y teams (need 16)"**

**Cause:** CSV file doesn't have 16 teams per region

**Solution:** Check your CSV has exactly 16 teams for each region:
- East: 16 teams
- West: 16 teams  
- South: 16 teams
- Midwest: 16 teams

### **Issue: Script fails with "ModuleNotFoundError: No module named 'bs4'"**

**Solution:**
```bash
pip install beautifulsoup4
```

### **Issue: "DuplicateKey" or "IntegrityError"**

**Cause:** Bracket already exists for this year

**Solution:** The script automatically clears old data, but you can manually clear:
```sql
DELETE FROM game WHERE year = 2025;
DELETE FROM team WHERE year = 2025;
```

---

## 🎯 **After Fetching the Bracket**

Once the bracket is loaded, your next steps are:

1. **✅ Verify** - Check web interface shows all teams
2. **📝 Add Participants** - Use admin to add your 16 friends' names
3. **👥 Assign Teams** - Use draft interface to assign 4 teams per participant
4. **📅 Wait for Tips** - Spreads will auto-fetch at 9am on game days
5. **🏀 Watch** - Scores auto-update during games

---

## 📅 **Timeline**

### **Selection Sunday (March 16, 2025):**
- Bracket announced around 6pm ET
- Run fetcher that evening or next morning

### **First Four (March 18-19, 2025):**
- Play-in games for 16-seeds and 11/12-seeds
- Most pools skip these (you can too!)

### **Round of 64 (March 20-21, 2025):**
- Tournament officially begins
- Make sure spreads are fetching and teams are assigned!

---

## 💡 **Pro Tips**

1. **Test with 2024 data first** - Practice the workflow before 2025
2. **Keep a backup CSV** - In case APIs fail, have a manual fallback
3. **Verify immediately** - Check the web interface right after fetching
4. **Document team names** - Note any naming differences (UConn vs Connecticut)

---

## 📞 **Quick Reference**

```bash
# Fetch 2024 bracket (test)
python fetch_bracket.py --year 2024

# Fetch 2025 bracket (real)
python fetch_bracket.py --year 2025

# Import from CSV
python fetch_bracket.py --year 2025 --csv bracket_2025.csv

# Dry run (preview)
python fetch_bracket.py --year 2024 --dry-run

# View database
sqlite3 instance/mmm.db
SELECT * FROM team WHERE year = 2025 LIMIT 10;

# Start web app
python app.py
```

---

**You're ready for March Madness! 🎉**
