// static/script.js
// -------------------------------
// Auto-refresh for live score updates during tournament games
// -------------------------------

(function() {
  'use strict';

  // Configuration
  const REFRESH_INTERVAL = 60000; // 60 seconds (in milliseconds)
  const TOURNAMENT_MONTHS = [2, 3]; // March = 2 (0-indexed), April = 3
  
  /**
   * Check if we're currently in tournament season (March/April)
   * to avoid unnecessary refreshes during off-season
   */
  function isTournamentSeason() {
    const now = new Date();
    const month = now.getMonth();
    return TOURNAMENT_MONTHS.includes(month);
  }

  /**
   * Check if there are any games currently in progress on the page
   */
  function hasLiveGames() {
    const statusBadges = document.querySelectorAll('td .badge.text-bg-light');
    for (let badge of statusBadges) {
      if (badge.textContent.trim() === 'In Progress') {
        return true;
      }
    }
    return false;
  }

  /**
   * Reload the page preserving the current year parameter
   */
  function refreshPage() {
    console.log('[MMM] Auto-refreshing page at', new Date().toLocaleTimeString());
    window.location.reload();
  }

  /**
   * Initialize auto-refresh if conditions are met
   */
  function initAutoRefresh() {
    // Only auto-refresh during tournament season when games are live
    if (isTournamentSeason() && hasLiveGames()) {
      console.log('[MMM] Live games detected - enabling auto-refresh every', REFRESH_INTERVAL / 1000, 'seconds');
      setInterval(refreshPage, REFRESH_INTERVAL);
    } else {
      console.log('[MMM] No live games or not tournament season - auto-refresh disabled');
    }
  }

  // Start auto-refresh when page loads
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initAutoRefresh);
  } else {
    initAutoRefresh();
  }

  // Visual indicator that auto-refresh is active
  if (isTournamentSeason() && hasLiveGames()) {
    const navbar = document.querySelector('.navbar .container');
    if (navbar) {
      const indicator = document.createElement('span');
      indicator.className = 'badge bg-success ms-auto';
      indicator.innerHTML = '🔴 LIVE';
      indicator.title = 'Auto-refreshing every 60 seconds';
      navbar.appendChild(indicator);
    }
  }
})();
