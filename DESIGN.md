# Digital Wellbeing desktop

Android Digital Wellbeing is the reference: calm presentation, a meaningful
usage ring, direct labels, and uncluttered usage lists. Adapt it to a Windows
desktop with keyboard navigation, explicit refresh, and scrollable pages.

## Visual language

- Warm off-white background, white content surfaces, forest-green emphasis.
- Shared colors and controls live in src/dashboard/theme.py.
- Segoe UI: 20pt page headings, 11pt body, 10pt supporting labels.
- 28px page margins; 18–24px section gaps; 8–12px related-control gaps.
- Color complements labels; it never carries status on its own.
- The overview ring means active share of device-open time, not goal progress.

## Behavior

- Overview, Apps & websites, Sessions, Weekly are persistent navigation.
- Dates apply to daily views; Weekly explicitly means the last seven days.
- Selecting a weekly day opens its Overview.
- Apps and websites have separate lists and a name filter.
- F5 refreshes; Alt+Left / Alt+Right navigate dates.
- Every page scrolls at smaller window sizes. Overview stacks its summary
  when narrow. Preserve view position during periodic refresh.
- Sample data is visibly labelled. No productivity scores or health claims.
- Website statistics are estimates from window titles, included in browser time.

## Verification

Run python -m unittest discover -s tests and python tests/ui_preview.py.
The latter opens sample-data screens and captures only the app window in the
temporary directory. Installer and physical multi-monitor DPI validation are
separate release checks.
