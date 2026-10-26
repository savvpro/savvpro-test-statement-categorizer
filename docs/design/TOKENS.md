# SortedHisab interface

Concept: `concept.png`, generated with the built-in Image Gen tool. It is a design reference, never rendered as the working UI.

Direction: a calm bookkeeping workspace. Persistent deep teal navigation, white working surfaces, cool gray canvas, compact transaction rows and an amber uncertainty state. No decorative imagery is needed in the shipped product.

Tokens: sidebar #153f3b; action #187c68; canvas #f6f8fa; surfaces #ffffff; text #172532; secondary #778493; border #e1e7ec. Radius 5-7px for controls and working panels; spacing 8/12/16/20/24/32px. System sans typography, 30px page heading, 17px panel heading, 11-14px working text. Outline Lucide icons, usually 16-21px. The screenshot includes subtle background lighting; implementation intentionally uses flat, consistent surfaces.

Architecture: App shell; ImportDialog; TransactionTable; ReviewPanel. Sidebar becomes horizontal navigation on mobile; table scrolls inside its own surface; review panel becomes an overlay. Reduced motion is respected.

Required functional extensions to concept: empty workspace, explicit account and format mapping, transaction-type selector, explanation/confidence, account-scoped exact rules, invalid-row report, currency selection, source provenance, statement removal, separate overview reconciliation. Fixture values replace the concept's invented amounts. No decorative summary numbers are shipped.

Primary copy: SortedHisab; Overview; Transactions; Rules; Statements; Every rupee, in the right place.; Export CSV; Upload statement; Business expenses; Personal spending; Excluded movements; Needs review; All transactions; Confirmed; Review transaction; Save review.
