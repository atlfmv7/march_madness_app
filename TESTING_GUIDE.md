# March Madness Madness - Testing & Deployment Guide

## 🧪 Testing Your Setup

### Option 1: Test with Mock Data (Available Anytime)
This simulates a complete tournament flow without needing real games:

```bash
# First, seed the database with demo data
python seed_data.py

# Run the mock tournament test
python test_mock_tournament.py
```

**What this tests:**
- ✅ Database is set up correctly
- ✅ Spread updates work with injected data
- ✅ Score updates work (in-progress and final)
- ✅ Bracket logic evaluates spreads correctly
- ✅ Team/owner propagation to next round works

### Option 2: Test with Live APIs (During NCAA Season)
Tests real API connections when games are happening:

```bash
# Test both APIs with current NCAA games
python test_api_live.py
```

**When to run this:**
- Regular season: November - March
- Conference tournaments: Early March
- NCAA Tournament: Mid-March to Early April

**What this tests:**
- ✅ Odds API returns spread data
- ✅ ESPN API returns score data
- ✅ API keys are configured correctly
- ✅ Provider modules work end-to-end

### Option 3: Test Flask CLI Commands
Test the actual commands that cron will run:

```bash
# Test spreads fetch (only works during NCAA season with games)
flask get-spreads

# Test with a specific date
flask get-spreads --date 2025-03-20

# Test scores update
flask update-scores

# Test with a specific date
flask update-scores --date 2025-03-20
```

### Option 4: Test Web Interface
Start the development server and test the UI:

```bash
# Start Flask development server
python app.py

# Or use Flask's built-in server
flask run --host=0.0.0.0 --port=5000
```

Then visit:
- **Main bracket:** http://localhost:5000
- **Admin panel:** http://localhost:5000/admin

**Test these features:**
- ✅ Games display correctly by region/round
- ✅ Year selector works (if you have multiple years)
- ✅ Auto-refresh activates when games are in progress
- ✅ Admin panel can manually set spreads
- ✅ Admin panel can manually set scores
- ✅ Marking game as Final evaluates spread correctly

---

## 📅 Timeline for Testing

### Now (October 2024):
- ✅ Run `test_mock_tournament.py` - verifies all logic works
- ✅ Run `test_api_live.py` - will show "no games today" but verifies API key works
- ✅ Test web interface with seed data
- ✅ Test admin interface

### During Regular Season (Nov 2024 - Mar 2025):
- Run `test_api_live.py` - should show actual NCAA basketball games
- Test `flask get-spreads` - should fetch real spreads
- Test `flask update-scores` - should fetch real scores
- Monitor API rate limits (500 requests/month on free tier)

### Selection Sunday (March 16, 2025):
- Update `seed_data.py` with all 64 teams
- Assign your 16 friends to their teams
- Run seed script to populate 2025 tournament
- Deploy to Raspberry Pi

### First Four (March 18-19, 2025):
- Enable cron jobs
- Monitor spreads fetch at 9am
- Monitor score updates during games
- Watch for team name mismatches

---

## 🚀 Deployment Checklist

### Before Tournament Starts:

- [ ] Update participant names in `seed_data.py`
- [ ] Get full 64-team bracket after Selection Sunday
- [ ] Assign initial team ownership (4 teams per participant)
- [ ] Run `seed_data.py` to populate database
- [ ] Transfer code to Raspberry Pi
- [ ] Set up Python virtual environment on Pi
- [ ] Install dependencies: `pip install -r requirements.txt`
- [ ] Copy `.env` file with your API key
- [ ] Test app runs on Pi: `python app.py`
- [ ] Set up Gunicorn + Nginx (optional but recommended)
- [ ] Configure cron jobs for automated updates
- [ ] Make app accessible on your network/internet

### Cron Job Setup:

Edit crontab: `crontab -e`

```bash
# Fetch spreads at 9:00 AM every day in March
0 9 * 3 * /home/pi/march_madness_app/scripts/get_spreads.sh

# Update scores every minute during March
* * * 3 * /home/pi/march_madness_app/scripts/update_scores.sh
```

**Important:** Edit the `.sh` scripts to update paths to match your Pi setup.

---

## 🔧 Troubleshooting

### "No games found" when testing APIs
**Cause:** NCAA season hasn't started or no games today  
**Fix:** This is normal! Try during:
- Regular season (Nov-Mar)
- Conference tournaments (early March)
- NCAA Tournament (mid-March to early April)

### "API key invalid" error
**Cause:** API key not set or incorrect  
**Fix:** 
1. Check `.env` file has: `ODDS_API_KEY=c0dd45487d6e3d75a38971dafe0c48a4`
2. Restart Flask app after changing `.env`

### Team names don't match between API and database
**Cause:** Different naming conventions (e.g., "Connecticut" vs "UConn")  
**Fix:** Add mappings to `util/name_map.py` in the `CANONICAL_MAP` dictionary

### Scores assigned to wrong teams
**Cause:** Home/away mismatch  
**Fix:** Already fixed in the code! But verify with real game data.

### Cron jobs not running
**Cause:** Environment variables not set in cron  
**Fix:** The `.sh` scripts handle this, but verify:
1. Scripts are executable: `chmod +x scripts/*.sh`
2. Check logs: `tail -f logs/get_spreads.log`

### Auto-refresh not working
**Cause:** JavaScript disabled or not tournament season  
**Fix:** Check browser console for errors. Auto-refresh only activates during March/April when games are "In Progress"

---

## 📊 API Rate Limits

### The Odds API (Free Tier):
- **Limit:** 500 requests/month
- **Usage:** 1 request per day = 30 requests/month for spreads
- **Tip:** You're well within limits for March Madness

### ESPN API:
- **Limit:** None documented (public endpoint)
- **Usage:** 1 request per minute during games = ~2000/month max
- **Tip:** Be respectful, don't hammer the endpoint

---

## 🎯 Next Steps

1. **Right now:** Run `python test_mock_tournament.py` to verify everything works

2. **During regular season:** Run `python test_api_live.py` to test live APIs

3. **Before Selection Sunday:** Update seed_data.py with real names and teams

4. **Day before First Four:** Deploy to Raspberry Pi and enable cron jobs

5. **During tournament:** Monitor daily, use admin panel for any manual fixes

---

## 📞 Quick Reference Commands

```bash
# Database
python seed_data.py                    # Populate with demo data

# Testing
python test_mock_tournament.py         # Test full flow with mock data
python test_api_live.py               # Test APIs with real games

# Flask CLI
flask get-spreads                     # Fetch today's spreads
flask get-spreads --date 2025-03-20  # Fetch specific date
flask update-scores                   # Fetch today's scores
flask mark-final --id 1 --t1 81 --t2 80  # Manually mark game final

# Run App
python app.py                         # Development server
gunicorn -w 1 -b 0.0.0.0:5000 "app:create_app()"  # Production

# View Logs
tail -f logs/get_spreads.log
tail -f logs/update_scores.log

# Database
sqlite3 instance/mmm.db               # Open database
.tables                               # Show tables
SELECT * FROM game;                   # Query games
```

---

**Good luck with your bracket! 🏀🎉**
