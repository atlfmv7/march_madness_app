# Game Simulator Guide

## 🎮 **What It Does**

The game simulator lets you test your March Madness bracket system by simulating games with realistic scores, triggering all the logic for winner advancement, ownership transfers, and bracket progression.

---

## 🚀 **Quick Start**

### **Interactive Mode (Easiest!)**

```bash
python simulate_tournament.py --interactive
```

**You'll see a menu:**
```
1. Simulate one game
2. Simulate Round of 64
3. Simulate Round of 32
4. Simulate Round of 16
5. Simulate Elite 8
6. Simulate Final Four
7. Simulate Championship
8. Simulate entire tournament
9. Show tournament status
0. Exit
```

Just pick an option and watch the magic! ✨

---

## 📋 **Command Line Options**

### **Simulate One Game**
```bash
python simulate_tournament.py --game 123
```
Simulates game ID 123 with realistic scores

### **Simulate a Round**
```bash
python simulate_tournament.py --round 64
python simulate_tournament.py --round 32
python simulate_tournament.py --round 16
```

### **Simulate Entire Tournament**
```bash
python simulate_tournament.py --all
```
Runs through all rounds from 64 to Championship!

### **Check Status**
```bash
python simulate_tournament.py --status
```
Shows how many games completed in each round

### **Different Year**
```bash
python simulate_tournament.py --year 2024 --round 64
```

---

## 🎯 **What Happens During Simulation**

For each game:
1. ✅ **Generates realistic scores** (55-95 range)
2. ✅ **Slightly favors lower seeds** (upsets happen ~35% of the time)
3. ✅ **Marks game as Final**
4. ✅ **Evaluates spread** to determine owner winner
5. ✅ **Advances team winner** to next round
6. ✅ **Transfers ownership** based on spread outcome
7. ✅ **Updates both teams** in next round game

---

## 📊 **Example Output**

```
==================================================================
🏀 SIMULATING ROUND OF 64 (32 games)
==================================================================

✅ Game 1: UConn 78 - 65 Stetson
   Winner: UConn (Seed 1)
   Owner Winner (vs spread): Emma

✅ Game 2: Florida Atlantic 71 - 68 Northwestern 🎉 UPSET!
   Winner: Northwestern (Seed 9)
   Owner Winner (vs spread): Olivia

✅ Game 3: San Diego State 82 - 59 UAB
   Winner: San Diego State (Seed 5)
   Owner Winner (vs spread): Ivy

...

==================================================================
📊 ROUND OF 64 COMPLETE
   Games Simulated: 32
   Upsets: 7
==================================================================
```

---

## 🧪 **Testing Workflow**

### **Full Tournament Test**

```bash
# 1. Check current status
python simulate_tournament.py --status

# 2. Run interactive mode
python simulate_tournament.py --interactive

# 3. Simulate Round of 64
Choose option 2

# 4. Check bracket views
# Visit http://localhost:5000 (table view)
# Visit http://localhost:5000/bracket (visual bracket)

# 5. Continue simulating rounds
Choose options 3, 4, 5, 6, 7 in sequence

# 6. See the champion!
```

---

## 💡 **What To Watch For**

### **In Table View** (/)
- ✅ Scores appear in games
- ✅ Status changes to "Final"
- ✅ Winners show in green
- ✅ Teams advance to next round
- ✅ Owner names update

### **In Visual Bracket** (/bracket)
- ✅ Winner cards highlighted in green
- ✅ Losers become transparent
- ✅ Teams move to next round
- ✅ Owner names transfer
- ✅ Champion appears with gold trophy 🏆

### **In Admin** (/admin)
- ✅ Game status updates
- ✅ Can manually override if needed
- ✅ See all game details

---

## 🎲 **Realistic Features**

The simulator includes realistic basketball simulation:

**Score Generation:**
- Range: 55-95 points (realistic college basketball)
- Most scores in 60-85 range
- No ties allowed

**Upset Probability:**
- Lower seeds win ~65% of time
- Higher seeds (upsets) win ~35% of time
- Matches real March Madness statistics!

**Spread Evaluation:**
- Uses your bracket_logic.py
- Determines owner winner based on spread
- Transfers ownership to next round

---

## 🔧 **Troubleshooting**

### **"No scheduled games found"**
- Round already completed
- Run `--status` to check
- Games might not have teams assigned yet

### **"Game X is already Final"**
- That game was already simulated
- Move to next round
- Or reset database and start over

### **Reset to Start Over**
```bash
# Clear 2024 data and reload
sqlite3 instance/mmm.db
DELETE FROM game WHERE year = 2024;
DELETE FROM team WHERE year = 2024;
.quit

# Reload bracket
python fetch_bracket.py --year 2024 --csv bracket_2024.csv

# Re-run draft
# Visit http://localhost:5000/admin/draft
# Click "Random Assignment"

# Start simulating again!
python simulate_tournament.py --interactive
```

---

## 🎊 **Demo Scenarios**

### **Quick Demo (5 minutes)**
```bash
python simulate_tournament.py --round 64
# Watch 32 games complete
# Check both bracket views
```

### **Full Tournament (15 minutes)**
```bash
python simulate_tournament.py --all
# Simulates entire tournament
# Watch champion crowned!
```

### **Step-by-Step (Best for testing)**
```bash
python simulate_tournament.py --interactive
# Do one round at a time
# Check bracket between rounds
# See progression clearly
```

---

## 📸 **What to Look For**

After simulating:
1. **Table View** - See scores, winners, advancement
2. **Visual Bracket** - See green winners, team progression
3. **Admin Panel** - Verify data is correct
4. **Draft Interface** - See how owners change
5. **Database** - Check everything persisted

---

## 🏆 **Expected Results**

After complete simulation:
- ✅ 63 total games completed (64 → 32 → 16 → 8 → 4 → 2 → 1)
- ✅ One champion crowned
- ✅ One participant owns the champion
- ✅ All rounds show correctly
- ✅ Both bracket views show full tournament
- ✅ Ownership tracked throughout

---

## 🎉 **Have Fun!**

This simulator lets you:
- Test all your logic
- See the bracket in action
- Demo to friends
- Verify everything works
- Get excited for March 2025!

**Enjoy simulating your tournament!** 🏀🎮

---

## 📞 **Quick Commands**

```bash
# Most common commands:
python simulate_tournament.py --interactive    # Interactive menu
python simulate_tournament.py --round 64       # Simulate first round
python simulate_tournament.py --all            # Full tournament
python simulate_tournament.py --status         # Check progress
```
