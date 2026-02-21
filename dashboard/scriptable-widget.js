// Life Systems Widget for Scriptable (iOS)
// Install: Copy this code to Scriptable app, create widget on home screen
// Updates: Daily at midnight
// Tap: Opens web dashboard

// Configuration
const API_ENDPOINT = "http://localhost:8000/mock-data.json"; // Change to real API when deployed
const DASHBOARD_URL = "http://localhost:8000"; // Change to GitHub Pages URL

// Fetch data
async function fetchState() {
  try {
    let req = new Request(API_ENDPOINT);
    let data = await req.loadJSON();
    return data.payload;
  } catch (error) {
    console.error("Failed to fetch state:", error);
    return null;
  }
}

// Calculate scores
function calculateCareerScore(career) {
  if (!career || !career.pipeline_summary) return 0;
  
  const funnel = career.pipeline_summary;
  const responseRate = funnel.applied > 0 ? (funnel.response / funnel.applied) : 0;
  const interviewRate = funnel.applied > 0 ? (funnel.interview / funnel.applied) : 0;
  
  // Score formula: weighted by pipeline stage progression
  const score = (
    (funnel.discovered > 0 ? 20 : 0) +  // Activity
    (funnel.applied > 0 ? 20 : 0) +     // Action
    (responseRate * 30) +                // Engagement
    (interviewRate * 30)                 // Success
  );
  
  return Math.min(Math.round(score), 100);
}

function calculateDatingScore(dating) {
  if (!dating) return 0;
  
  const hoursRatio = dating.weekly_hours / dating.target_hours;
  const gymStreak = dating.streaks?.gym_consecutive_days || 0;
  const socialEvents = dating.streaks?.social_events_per_week || 0;
  
  // Score formula: hours + consistency + variety
  const score = (
    (hoursRatio * 50) +                  // Target hours
    (Math.min(gymStreak, 7) / 7 * 25) +  // Gym consistency (up to 7 days)
    (Math.min(socialEvents, 3) / 3 * 25) // Social variety (up to 3/week)
  );
  
  return Math.min(Math.round(score), 100);
}

function getFitnessStreak(dating) {
  if (!dating || !dating.streaks) return 0;
  return dating.streaks.gym_consecutive_days || 0;
}

// Create widget
function createWidget(state) {
  let widget = new ListWidget();
  widget.backgroundColor = new Color("#0f1419");
  widget.url = DASHBOARD_URL;
  
  if (!state) {
    // Error state
    let errorText = widget.addText("⚠️ No Data");
    errorText.textColor = Color.red();
    errorText.font = Font.boldSystemFont(16);
    return widget;
  }
  
  // Title
  let title = widget.addText("Life Systems");
  title.textColor = new Color("#1d9bf0");
  title.font = Font.boldSystemFont(14);
  
  widget.addSpacer(8);
  
  // Calculate scores
  const careerScore = calculateCareerScore(state.sections?.career);
  const datingScore = calculateDatingScore(state.sections?.dating);
  const fitnessStreak = getFitnessStreak(state.sections?.dating);
  
  // Career Score
  addScoreRow(widget, "💼 Career", careerScore);
  widget.addSpacer(4);
  
  // Dating Score
  addScoreRow(widget, "💃 Dating", datingScore);
  widget.addSpacer(4);
  
  // Fitness Streak
  let fitnessRow = widget.addStack();
  fitnessRow.layoutHorizontally();
  
  let fitnessLabel = fitnessRow.addText("🏋️ Streak");
  fitnessLabel.textColor = new Color("#71767b");
  fitnessLabel.font = Font.systemFont(12);
  
  fitnessRow.addSpacer();
  
  let fitnessValue = fitnessRow.addText(`${fitnessStreak} days`);
  fitnessValue.textColor = fitnessStreak >= 5 ? new Color("#00ba7c") : new Color("#ffd400");
  fitnessValue.font = Font.boldSystemFont(12);
  
  widget.addSpacer(8);
  
  // Alerts count (if any)
  const alertCount = state.alerts?.length || 0;
  if (alertCount > 0) {
    let alertText = widget.addText(`⚠️ ${alertCount} alert${alertCount > 1 ? 's' : ''}`);
    alertText.textColor = new Color("#f91860");
    alertText.font = Font.systemFont(10);
  }
  
  // Last update
  widget.addSpacer();
  let updateTime = widget.addText(`Updated: ${new Date().toLocaleTimeString()}`);
  updateTime.textColor = new Color("#71767b");
  updateTime.font = Font.systemFont(8);
  
  return widget;
}

function addScoreRow(widget, label, score) {
  let row = widget.addStack();
  row.layoutHorizontally();
  
  let labelText = row.addText(label);
  labelText.textColor = new Color("#71767b");
  labelText.font = Font.systemFont(12);
  
  row.addSpacer();
  
  let scoreText = row.addText(`${score}`);
  scoreText.textColor = getScoreColor(score);
  scoreText.font = Font.boldSystemFont(14);
  
  // Progress bar
  widget.addSpacer(2);
  let progressBar = widget.addStack();
  progressBar.layoutHorizontally();
  progressBar.size = new Size(0, 4);
  progressBar.cornerRadius = 2;
  progressBar.backgroundColor = new Color("#2f3336");
  
  let progressFill = progressBar.addStack();
  progressFill.size = new Size(score * 1.2, 4); // Max width ~120px
  progressFill.backgroundColor = getScoreColor(score);
  progressFill.cornerRadius = 2;
}

function getScoreColor(score) {
  if (score >= 70) return new Color("#00ba7c");  // Green
  if (score >= 40) return new Color("#ffd400");  // Yellow
  return new Color("#f91860");  // Red
}

// Main
async function main() {
  let state = await fetchState();
  let widget = createWidget(state);
  
  if (config.runsInWidget) {
    Script.setWidget(widget);
  } else {
    widget.presentMedium();
  }
  
  Script.complete();
}

await main();
