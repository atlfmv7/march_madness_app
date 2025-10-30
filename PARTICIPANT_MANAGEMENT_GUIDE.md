# Participant Management - User Guide

## 🎯 What This Does

The Participant Management interface lets you add, edit, and manage the 16 people in your March Madness bracket pool.

---

## 🚀 **Quick Start**

### **Step 1: Access the Interface**

```bash
# Start the app
python app.py

# Visit in your browser:
http://localhost:5000/admin/participants
# Or on your network:
http://192.168.150.217:5000/admin/participants
```

### **Step 2: Add Participants**

1. Use the form on the left side
2. Enter each person's name
3. Optionally add their email (for future notifications)
4. Click "Add Participant"
5. Repeat until you have 16 people

### **Step 3: Verify**

The status badge at the top shows:
- ✅ **Green**: You have exactly 16 (ready for draft!)
- ⚠️ **Yellow**: You need more participants
- ❌ **Red**: You have too many

---

## ✨ **Features**

### **Add Participants**
- Required: Name (up to 100 characters)
- Optional: Email (for future notifications)
- Duplicate names are blocked
- Real-time validation

### **Edit Participants**
- Click "Edit" button next to any name
- Modal popup with current info
- Change name or email
- Saves immediately

### **Delete Participants**
- Click "Delete" button
- Confirmation prompt (can't be undone!)
- Prevents deletion if they own teams
- Safe guards in place

### **View All**
- Sorted alphabetically
- Shows count and status
- Easy to scan list

---

## 🧪 **Test It**

Use the test script to quickly add 16 sample participants:

```bash
python test_participants.py
```

This adds: Ryan, Alice, Bob, Carol, David, Emma, Frank, Grace, Henry, Ivy, Jack, Kate, Liam, Maya, Nathan, Olivia

---

## 📋 **Validation Rules**

- **Exactly 16 participants** needed for the bracket pool
- **Unique names** - no duplicates allowed
- **Name is required** - can't be empty
- **Email is optional** - leave blank if you don't need it
- **Can't delete** if participant owns teams (safety feature)

---

## 🎯 **Typical Workflow**

### **Before the Tournament:**

1. **Add participants** (do this anytime)
   - After Selection Sunday
   - Before or after loading the bracket
   - Can be done in any order

2. **Verify count** (must have exactly 16)
   - Check the status badge
   - Green = ready to proceed

3. **Assign teams** (next step - Enhancement #3)
   - Each participant gets 4 teams
   - One from each region

### **During the Tournament:**

- Names are displayed throughout the app
- Shows on main bracket page
- Shows in game listings
- Shows as team owners

### **After the Tournament:**

- Participants stay in database
- Can be reused next year
- Or delete and start fresh

---

## 🐛 **Troubleshooting**

### **Can't add participant - "already exists"**

**Cause:** Name is already in the system

**Solution:** 
- Use a nickname or last initial (e.g., "Ryan S" vs "Ryan M")
- Or edit the existing participant

### **Can't delete participant - "they own teams"**

**Cause:** Safety feature - participant has teams assigned

**Solution:**
- First remove their team assignments (Enhancement #3)
- Then delete the participant

### **Count shows wrong number**

**Cause:** Old data from seed_data.py

**Solution:**
```bash
# Clear old participants
sqlite3 instance/mmm.db
DELETE FROM participant WHERE name LIKE 'Participant %';
.quit
```

---

## 💡 **Pro Tips**

1. **Use Real Names** - Makes the bracket more fun!
2. **Add Emails** - Useful for future notification features
3. **Test First** - Use test_participants.py to practice
4. **Keep It Simple** - First names or nicknames work great
5. **Document Somewhere** - Keep a list of participants handy

---

## 🔗 **Integration with Other Features**

### **With Bracket Fetcher:**
- Load bracket first OR add participants first
- Order doesn't matter
- Both needed before team assignment

### **With Team Assignment (Coming Next):**
- Must have exactly 16 participants
- Then assign 4 teams to each
- One team per region per participant

### **With Main Bracket:**
- Participant names show as team owners
- Displayed in game listings
- Updated as tournament progresses

---

## 📊 **Database Structure**

The Participant table stores:

```sql
CREATE TABLE participant (
    id INTEGER PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    email VARCHAR(120)
);
```

Simple and clean!

---

## 🎉 **What's Next?**

After adding all 16 participants, you're ready for:

**Enhancement #3: Team Assignment (Draft Interface)**
- Assign 64 teams to 16 participants
- 4 teams each (one per region)
- Manual selection or random assignment
- Then you're ready for the tournament!

---

## 📞 **Quick Reference**

```bash
# Access participant management
http://localhost:5000/admin/participants

# Add 16 test participants
python test_participants.py

# Check database
sqlite3 instance/mmm.db
SELECT COUNT(*) FROM participant;
SELECT * FROM participant ORDER BY name;
.quit

# Clear all participants
sqlite3 instance/mmm.db
DELETE FROM participant;
.quit
```

---

**Ready to add your friends! 🎉**
