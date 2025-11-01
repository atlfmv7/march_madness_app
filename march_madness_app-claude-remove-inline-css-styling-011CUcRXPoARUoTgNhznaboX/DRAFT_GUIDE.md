# Team Assignment (Draft) - User Guide

## 🎯 What This Does

The Draft Interface lets you assign all 64 tournament teams to your 16 participants. Each participant gets exactly 4 teams (one from each region).

---

## 🚀 **Quick Start**

### **Prerequisites:**
- ✅ Have exactly 16 participants
- ✅ Have 64 teams loaded (from bracket fetcher)

### **Access the Draft:**

```bash
# Start the app
python app.py

# Visit:
http://localhost:5000/admin/draft
# Or on network:
http://192.168.150.217:5000/admin/draft
```

---

## ⚡ **Three Ways to Assign Teams**

### **Method 1: Random Assignment (Fastest!)**

1. Click **"🎲 Random Assignment"** button
2. Confirm the action
3. Done! Each participant instantly gets 4 teams (one per region)

**When to use:**
- Quick setup before tournament
- Fair, unbiased distribution
- Don't want to do a manual draft

**Time:** ~2 seconds

---

### **Method 2: Manual Assignment**

1. Browse through each region (East, West, South, Midwest)
2. Use dropdown next to each team to select owner
3. Click **"💾 Save All Assignments"** when done

**When to use:**
- You already had a draft
- Want specific team assignments
- Entering pre-determined results

**Time:** ~10-15 minutes

---

### **Method 3: Reset and Start Over**

1. Click **"🔄 Reset All"** button
2. Confirm the action
3. All assignments cleared
4. Start fresh with Method 1 or 2

**When to use:**
- Made mistakes
- Want to redo the draft
- Testing different scenarios

---

## 📊 **Understanding the Interface**

### **Assignment Progress Panel**

Shows real-time status for each participant:

```
Ryan (4/4 teams) ✅
  E:1 W:1 S:1 M:1

Alice (2/4 teams) ⚠️
  E:1 W:0 S:1 M:0

Bob (0/4 teams) ⏳
  E:0 W:0 S:0 M:0
```

**Legend:**
- ✅ Green with checkmark = Complete (4 teams, one per region)
- ⚠️ Yellow = In progress (has some teams)
- ⏳ Gray = Not started (no teams)
- E/W/S/M = East/West/South/Midwest count

---

### **Team Lists by Region**

Each region shows:
- **Seed** - Tournament seeding (1-16)
- **Team** - School name
- **Assign To** - Dropdown to select owner

Teams are sorted by seed within each region.

---

## ✅ **Validation Rules**

The system ensures:
1. **Each participant gets exactly 4 teams**
2. **One team from each region per participant**
3. **No duplicate assignments** (one owner per team)
4. **All 64 teams assigned**

The progress panel shows violations in real-time.

---

## 🧪 **Test the Draft**

Use the test script to check status:

```bash
python test_draft.py
```

**Output shows:**
- Overall assignment status
- Teams per participant
- Assignments by region
- Validation results

---

## 🎯 **Typical Workflows**

### **Scenario A: Quick Random Setup**

```
1. Ensure you have 16 participants
2. Load 2024/2025 bracket
3. Visit /admin/draft
4. Click "Random Assignment"
5. Done! Check homepage to see owners
```

**Time:** 5 minutes

---

### **Scenario B: Manual Draft Entry**

```
1. Do your draft externally (email, in-person, etc.)
2. Record who got which teams
3. Visit /admin/draft
4. Go region by region, selecting owners
5. Click "Save All Assignments"
6. Verify on homepage
```

**Time:** 15 minutes

---

### **Scenario C: CSV Import** (Future Enhancement)

Not yet implemented, but planned:
- Export your draft to CSV
- Import: team_name, owner_name
- Validates and assigns automatically

---

## 🐛 **Troubleshooting**

### **"Need exactly 16 participants" error**

**Cause:** Don't have 16 participants yet

**Solution:**
```bash
# Add participants first
http://localhost:5000/admin/participants

# Or use test script:
python test_participants.py
```

---

### **"Need 64 teams" error**

**Cause:** Haven't loaded bracket yet

**Solution:**
```bash
# Load bracket first:
python fetch_bracket.py --year 2024 --csv bracket_2024.csv
```

---

### **Dropdown shows "-- Not Assigned --" after saving**

**Cause:** Didn't select an owner from dropdown

**Solution:** Select a participant name from each dropdown, then save

---

### **Page warns about unsaved changes**

**Cause:** Made changes but didn't click "Save All Assignments"

**Solution:** 
- Click "Save All Assignments" to keep changes
- Or reload page to discard changes

---

## 💡 **Pro Tips**

1. **Use Random Assignment First**
   - Try it once to see how it works
   - Then reset and do manual if needed

2. **Save Frequently**
   - Manual assignment takes time
   - Save after each region to avoid losing work

3. **Check Progress Panel**
   - Green checkmarks = done
   - Stay organized by completing one participant at a time

4. **Test with test_draft.py**
   - Run after assignment
   - Validates everything is correct

5. **Document Your Draft**
   - Take a screenshot of the final assignments
   - Or run test_draft.py and save the output

---

## 🔗 **Integration with Other Features**

### **With Main Bracket Page:**
Once assigned, team owners appear:
- Next to team names in matchups
- In game listings
- Throughout the tournament

### **With Spread Updates:**
Owners are used for:
- Determining who wins vs spread
- Transferring ownership when games finish
- Tracking standings

### **With Game Results:**
As tournament progresses:
- Owners change based on spread outcomes
- Winners advance to next round
- Final standings tracked

---

## 📊 **Database Structure**

Team assignments are stored in:

```sql
-- Initial ownership (draft results)
Team.initial_owner_id

-- Current ownership (changes during tournament)
Team.current_owner_id
```

Both fields point to the Participant table.

---

## 📞 **Quick Reference**

```bash
# Access draft interface
http://localhost:5000/admin/draft

# Test draft status
python test_draft.py

# Add/manage participants
http://localhost:5000/admin/participants

# Check assignments in database
sqlite3 instance/mmm.db
SELECT 
  t.name as team,
  t.region,
  p.name as owner
FROM team t
LEFT JOIN participant p ON t.initial_owner_id = p.id
WHERE t.year = 2024
ORDER BY t.region, t.seed;
.quit
```

---

## 🎉 **You're Ready!**

After completing the draft:
1. ✅ All 64 teams assigned
2. ✅ Each participant has 4 teams
3. ✅ One team per region per participant
4. ✅ Ready for tournament day!

**Next steps:**
- Set up cron jobs for automated updates
- Test spread and score fetching
- Wait for Selection Sunday 2025!

---

**Happy drafting! 🏀**
