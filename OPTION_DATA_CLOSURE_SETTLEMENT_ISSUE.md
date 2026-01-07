# CRITICAL ISSUE: Option Market Closure Settlement Bars

## Discovery Date
January 7, 2026

## Problem Summary

When fetching historical option TRADES data from IBKR with `useRTH=1` (regular trading hours only), the API returns **settlement price snapshots at market close** in addition to regular 30-minute trading bars. These settlement bars appear at various times depending on market schedule:
- **16:00:00** on regular trading days
- **13:00:00** on early-close days (e.g., Christmas Eve)

These settlement bars are NOT real trading data and cause mismatches when merging with underlying stock IV data.

## Root Cause Analysis

### The Mismatch

When fetching option data for OPTIONS_MARTIN strategy:

**Option TRADES Request:**
- Returns: 275 bars
- Includes: 9:30, 10:00, 10:30, ..., 15:00, 15:30, **+ settlement bars at close**

**Stock IV Request:**
- Returns: 254 bars
- Includes: 9:30, 10:00, 10:30, ..., 15:00, 15:30 (stops at last trading interval)

**Difference:** 21 bars total
- 20 bars at 16:00:00 (regular trading days)
- 1 bar at 13:00:00 (Christmas Eve early close)

### Why Options Have 16:00 Bars

Options require official settlement prices for:
- Mark-to-market calculations
- Margin requirements
- Daily P&L reporting
- Options expiration settlement

IBKR includes these settlement snapshots when you request TRADES data, even though they're not actual trades.

### Characteristics of 16:00 Settlement Bars

Evidence from testing (SPY 680C exp=20260220):

```
20251223  16:00:00
  Open:   $22.09
  High:   $22.09
  Low:    $22.09
  Close:  $22.09
  Volume: 0          ← NO TRADING VOLUME!
```

```
20251226  16:00:00
  Open:   $23.17
  High:   $23.17
  Low:    $23.17
  Close:  $23.17
  Volume: 0          ← Settlement price snapshot
```

**Key Indicators:**
- **Open = High = Low = Close** (single price point)
- **Volume = 0** (or very small - settlement marks, not trades)
- **Time = 16:00:00** (exactly 4:00 PM)
- **Frequency = Daily** (one per trading day)

### Why This Causes IV Merge Failures

Stock IV data correctly ends at 15:30:00 (last real 30-minute interval):
- Stock market closes at 16:00, but IV is computed during trading intervals
- Last 30-min interval: 15:30 - 16:00
- IV data timestamp: 15:30:00 (start of interval)

Option TRADES includes 16:00 settlement → 20 extra bars with no matching IV → NULL IV values

### Logical Contradiction

**User's Key Insight:** "Options can ONLY trade when the underlying stock trades. Therefore, option bars should be ≤ stock bars, NEVER MORE."

This is 100% correct! The fact that option TRADES had MORE bars than stock TRADES was the critical clue that something was wrong.

## The Solution

### Implementation

Filter option TRADES to only include bars that exist in IV data (after both are fetched):

```python
# In ibkr_option_service.py, after both TRADES and IV data received
iv_dates = set(bar['date'] for bar in self.iv_data)
original_count = len(self.data)
self.data = [bar for bar in self.data if bar['date'] in iv_dates]
filtered_count = original_count - len(self.data)
```

This approach automatically handles:
- 16:00 settlement bars on regular trading days
- 13:00 settlement bars on early-close days (Christmas Eve, etc.)
- Any future market schedule changes

### Result

After filtering:
- Option TRADES: 254 bars (9:30 - 15:30)
- Stock IV: 254 bars (9:30 - 15:30)
- **Perfect 1:1 match** ✅
- **NO forward/backward fill needed** ✅
- **100% IV coverage guaranteed** ✅

## Test Evidence

### Test File
`backend/test_option_trades_vs_stock_trades.py`

### Test Results

```
OPTION TRADES - LAST BAR OF EACH DAY (Full Details)
================================================================================

20251230 - Last bar of the day:
  Time: 20251230  16:00:00
  Open:   $20.60
  High:   $20.60
  Low:    $20.60
  Close:  $20.60
  Volume: 0          ← Proof: Settlement snapshot, not trading bar
```

### Stock TRADES vs Option TRADES Comparison

When testing TRADES from both:
- Stock TRADES: Ends at 15:30:00
- Option TRADES (before filter): Ends at 16:00:00
- Option TRADES (after filter): Ends at 15:30:00 ✅

## Impact on Strategy

### Before Fix (with 16:00 bars)
```
491/530 bars with IV (92.6% coverage)
39 bars with NULL IV → Strategy fails silently
```

### After Fix (filtered 16:00 bars)
```
254/254 bars with IV (100% coverage)
0 bars with NULL IV → Strategy works perfectly
```

## Alternative Approaches Considered

### 1. Forward/Backward Fill (REJECTED)
**Why:** Masks the real problem. Fills fake data into settlement bars that shouldn't exist.

### 2. Use endDateTime parameter (INSUFFICIENT)
**Why:** Doesn't solve the issue. Both requests use same endDateTime but IBKR still returns 16:00 for options.

### 3. Request with useRTH=0 (REJECTED)
**Why:** Would include pre-market/after-hours bars, making the problem worse.

### 4. Filter 16:00 bars (IMPLEMENTED) ✅
**Why:** Removes non-trading data at the source. Clean, simple, correct.

## Code References

### Modified Files

1. **backend/services/ibkr_option_service.py** (lines 188-200)
   - Added filter to remove 16:00:00 settlement bars
   - Added logging for filtered bar count

### Related Files

2. **backend/test_option_trades_vs_stock_trades.py**
   - Test to compare option vs stock TRADES bar counts
   - Demonstrates the 16:00 settlement bar issue

3. **backend/test_iv_date_mismatch.py**
   - Original test that discovered the bar count mismatch

## Important Notes

### Do NOT Remove This Filter

Future developers: If you see this filter and think "we should get the closing price", **STOP!**

The 15:30 bar ALREADY contains the closing price:
- 15:30 bar represents the interval from 15:30 to 16:00 (market close)
- Its close price IS the 4:00 PM closing price
- The 16:00 "bar" is redundant settlement data

### Exception: Daily Bars

This issue is specific to **intraday bars** (30 mins, 1 hour, etc.).

For **daily bars**, there is no 16:00 settlement issue because:
- Daily bar covers entire trading day (9:30 - 16:00)
- Single close price = 16:00 settlement
- No duplicate bars

## Verification

To verify this fix is working:

```bash
# Run test
cd backend
python test_option_trades_vs_stock_trades.py

# Expected output:
# Option TRADES: 254 bars
# Stock TRADES: 254 bars
# ✅ PERFECT MATCH
```

## Related Documentation

- IBKR API Documentation: Historical Data - Regular Trading Hours
- Options Settlement Procedures
- IV Data Merge Logic (market_data.py)

## Lessons Learned

1. **Always validate bar counts** - Options should never have more bars than underlying stock
2. **Question the data source** - Not all bars from IBKR are trading data
3. **Print detailed bar information** - Open/High/Low/Close/Volume reveals settlement bars
4. **Trust domain knowledge** - User's insight about option/stock relationship was correct
5. **Test with real data** - Simulated data wouldn't have shown this issue

## Credits

Discovered through systematic investigation:
1. User noticed 491/530 IV coverage (not 100%)
2. Questioned why option bars > stock bars (logically impossible)
3. Requested detailed bar comparison
4. Identified 16:00 bars as settlement snapshots
5. Solution: Filter them out

---

**CRITICAL: DO NOT REMOVE THE 16:00 FILTER WITHOUT UNDERSTANDING THIS ISSUE FULLY**
