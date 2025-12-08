# Portal Testing Guide

## Prerequisites

1. **Environment Variables**: Ensure `.env.local` has:

   ```bash
   NEXT_PUBLIC_SUPABASE_URL=https://vlvlwmolfdpzdfmtipji.supabase.co
   NEXT_PUBLIC_SUPABASE_ANON_KEY=<your-anon-key>
   NEXT_PUBLIC_API_URL=https://nikita-api-<id>.us-central1.run.app
   ```

2. **Dependencies**: Run `pnpm install` in the `portal/` directory

3. **Backend**: Ensure backend API is running and accessible

## Running the Portal Locally

```bash
cd portal
pnpm dev
```

The portal will be available at http://localhost:3000

## Test 1: Authentication Flow

### 1.1 Magic Link Email Submission

1. **Navigate** to http://localhost:3000
2. **Verify** landing page displays:
   - "Nikita" logo
   - "Don't Get Dumped" tagline
   - Sign In card with email input
3. **Test invalid email**:
   - Enter: `invalid-email` → Should show "Please enter a valid email address"
   - Enter: `test@` → Should show validation error
4. **Test valid email**:
   - Enter: `your-email@example.com`
   - Click "Send Magic Link"
   - Should show loading state: "Sending..."
   - Should show success message: "Check your email for the magic link to sign in."

### 1.2 Magic Link Click & Callback

1. **Check email** for magic link from Supabase
2. **Click link** in email
3. **Verify redirect** to `/auth/callback`
4. **Verify final redirect** to `/dashboard`

### 1.3 Error Handling

Test error scenarios:

- **Expired link**: Click old magic link → Should show error page with clear message
- **Invalid token**: Manually modify URL parameters → Should handle gracefully
- **Network error**: Disconnect network, submit email → Should show error message

## Test 2: Dashboard Components

Once authenticated and on `/dashboard`:

### 2.1 Header & Navigation

- **Verify header** displays:
  - "Nikita" logo
  - Navigation links: Dashboard, Conversations, History
  - "Sign Out" button (top right)
- **Test navigation**:
  - Click "Conversations" → Should navigate to `/conversations`
  - Click "History" → Should navigate to `/history`
  - Click "Dashboard" → Should navigate to `/dashboard`

### 2.2 Dashboard Cards

**Score Card:**

- Displays relationship score (0-100)
- Shows score trend (↑ or ↓)
- Color-coded by chapter:
  - Chapter 1-2: Green tones
  - Chapter 3-4: Yellow/Orange
  - Chapter 5: Red

**Chapter Card:**

- Shows current chapter (1-5)
- Displays chapter name
- Shows boss attempts (if in boss phase)
- Indicates game status

**Engagement Card** (if available):

- Shows engagement state (CALIBRATING, IN_ZONE, DRIFTING, etc.)
- Displays multiplier value
- Shows streaks (in-zone, clingy, distant days)

### 2.3 Metrics Grid

- **4 metric cards** displayed:
  - Intimacy (0-100)
  - Passion (0-100)
  - Trust (0-100)
  - Secureness (0-100)
- Each card shows:
  - Current value
  - Progress bar (color-coded)
  - Visual indicator

### 2.4 Vices Card

- Displays 8 vice categories
- Each shows:
  - Category name
  - Intensity level (1-5)
  - Engagement score
  - Visual bar representation

### 2.5 Decay Warning

- Should display if last interaction > 6 hours
- Shows:
  - Hours since last interaction
  - Next decay countdown
  - Current decay rate (varies by chapter)
  - Warning styling (orange/red)

## Test 3: API Integration

### 3.1 Data Loading States

- **On first load**: Should show loading spinner with "Loading your relationship..."
- **On data fetch**: Should smoothly transition to showing actual data
- **On error**: Should show error card with:
  - Warning icon
  - Error message
  - "Go to Login" button

### 3.2 API Endpoints (via Browser DevTools)

Open browser DevTools → Network tab:

1. **GET /api/v1/portal/stats**
   - Should return: user stats, metrics, relationship score, chapter
   - Status: 200 OK
   - Headers: `Authorization: Bearer <jwt>`

2. **GET /api/v1/portal/engagement**
   - Should return: engagement state, multiplier, streaks
   - Status: 200 OK

3. **GET /api/v1/portal/vices**
   - Should return: array of 8 vice preferences
   - Status: 200 OK

### 3.3 Authentication

- **JWT Token**: Check `localStorage` or cookies for Supabase session
- **Authorization Header**: All API calls should include `Bearer <token>`
- **Token Expiry**: After expiry, should redirect to login

## Test 4: Responsive Design

Test on different screen sizes:

- **Mobile (320px - 768px)**:
  - Cards stack vertically
  - Navigation collapses
  - Touch targets appropriately sized

- **Tablet (768px - 1024px)**:
  - 2-column grid layout
  - Readable text sizes

- **Desktop (1024px+)**:
  - 3-column grid layout
  - Optimal spacing

## Test 5: Conversations Page

Navigate to `/conversations`:

- Should display list of past conversations
- Each conversation shows:
  - Timestamp
  - Message count
  - Preview text
- Click conversation → Should show detail view

## Test 6: History Page

Navigate to `/history`:

- Should display:
  - Score history graph (Recharts)
  - Daily summaries list
  - Filterable by date range
- Graph should show:
  - X-axis: Time
  - Y-axis: Relationship score (0-100)
  - Line plot with data points

## Common Issues to Check

### Authentication Issues

- ❌ **Infinite redirect loop**: Check middleware.ts configuration
- ❌ **"Not authenticated" error**: Verify Supabase session is valid
- ❌ **CORS errors**: Check API backend CORS configuration

### API Issues

- ❌ **404 Not Found**: Verify `NEXT_PUBLIC_API_URL` is correct
- ❌ **401 Unauthorized**: Check JWT token is being sent
- ❌ **500 Server Error**: Check backend logs in Cloud Run

### UI Issues

- ❌ **Blank page**: Check browser console for React errors
- ❌ **Styling broken**: Verify Tailwind CSS classes are working
- ❌ **Components not rendering**: Check React Query hooks

## Performance Checks

- **Initial load**: Should be < 3 seconds
- **Data refresh**: Auto-refresh every 30 seconds (check Network tab)
- **Smooth transitions**: No janky animations

## Security Checks

- **JWT exposed**: JWT should NOT be visible in URL or logs
- **Environment variables**: Should NOT be exposed in client bundle (check `_app.js`)
- **XSS**: Try entering `<script>alert('xss')</script>` in email input → Should be sanitized

## Browser Compatibility

Test in:

- ✅ Chrome (latest)
- ✅ Firefox (latest)
- ✅ Safari (latest)
- ✅ Edge (latest)

## Accessibility

- **Keyboard navigation**: Tab through all interactive elements
- **Screen reader**: Test with VoiceOver (Mac) or NVDA (Windows)
- **Color contrast**: All text should have sufficient contrast (WCAG AA)
- **Focus indicators**: Visible focus outlines on all interactive elements

## Next Steps After Testing

1. Document any bugs found
2. Create GitHub issues for bugs
3. Deploy to Vercel for staging preview
4. Test staging deployment
5. Merge to production
