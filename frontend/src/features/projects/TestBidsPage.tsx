// OE-DELIVERY: 2026-10-19-test-bids
// Test page — renders BidOpportunitiesTab directly, bypassing ProjectsPage.
// Route: add <Route path="/test-bids" element={<TestBidsPage />} /> to App.tsx
// Open: http://127.0.0.1:5173/test-bids

import { BidOpportunitiesTab } from '@/features/projects/BidOpportunitiesTab';

export function TestBidsPage() {
  return (
    <div style={{ padding: '24px' }}>
      <h1 style={{ color: 'white', marginBottom: '16px' }}>
        TEST: BidOpportunitiesTab direct render
      </h1>
      <BidOpportunitiesTab />
    </div>
  );
}
