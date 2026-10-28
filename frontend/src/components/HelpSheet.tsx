"use client";
import * as Dialog from "@radix-ui/react-dialog";

const KEYS: [string, string][] = [
  ["J or K", "Move to the next or previous row"],
  ["1 to 9", "Pick the numbered category"],
  ["Enter", "Confirm the row"],
  ["R", "Turn Remember for this merchant on or off"],
  ["U", "Undo the last confirm"],
  ["?", "Show this sheet"],
];

export function HelpSheet({ open, onOpenChange }: { open: boolean; onOpenChange: (o: boolean) => void }) {
  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-40 bg-ink/40" />
        <Dialog.Content className="panel-shadow fixed left-1/2 top-24 z-50 w-[min(92vw,30rem)] -translate-x-1/2 rounded-md bg-row p-6">
          <Dialog.Title className="text-lg font-semibold">Keyboard shortcuts</Dialog.Title>
          <Dialog.Description className="mt-1 max-w-[72ch] text-muted">
            Work through the list without the mouse.
          </Dialog.Description>
          <dl className="mt-4 divide-y divide-rule border-y border-rule">
            {KEYS.map(([k, d]) => (
              <div key={k} className="flex gap-4 py-2">
                <dt className="w-20 font-medium">{k}</dt>
                <dd>{d}</dd>
              </div>
            ))}
          </dl>
          <Dialog.Close className="mt-4 rounded-xs border border-ledger px-4 py-2 font-medium text-ledger">Close</Dialog.Close>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
