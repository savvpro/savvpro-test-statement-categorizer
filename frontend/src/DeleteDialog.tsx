import { useLayoutEffect, useRef } from "react";
import { Trash2 } from "lucide-react";

type Props = {
  filename: string;
  busy: boolean;
  onCancel: () => void;
  onConfirm: () => void;
};

export default function DeleteDialog({
  filename,
  busy,
  onCancel,
  onConfirm,
}: Props) {
  const dialog = useRef<HTMLDialogElement>(null);
  useLayoutEffect(() => {
    const element = dialog.current;
    const trigger = document.activeElement;
    element?.showModal(); // Makes the background inert and focuses the first button.
    return () => {
      element?.close();
      if (trigger instanceof HTMLElement && trigger.isConnected)
        trigger.focus();
    };
  }, []);
  return (
    <dialog
      ref={dialog}
      className="panel modal"
      aria-labelledby="delete-title"
      onKeyDown={(event) => {
        if (event.key !== "Tab") return;
        const buttons = Array.from(
          event.currentTarget.querySelectorAll<HTMLButtonElement>(
            "button:not(:disabled)",
          ),
        );
        const first = buttons[0];
        const last = buttons[buttons.length - 1];
        if (!first) {
          event.preventDefault();
        } else if (event.shiftKey && document.activeElement === first) {
          event.preventDefault();
          last.focus();
        } else if (!event.shiftKey && document.activeElement === last) {
          event.preventDefault();
          first.focus();
        }
      }}
      onCancel={(event) => {
        event.preventDefault();
        if (!busy) onCancel();
      }}
    >
      <Trash2 size={24} />
      <h2 id="delete-title">Delete this statement?</h2>
      <p>
        This removes {filename} and its review history from this device. Your
        source CSV is unaffected. This cannot be undone.
      </p>
      <div className="button-row">
        <button className="button secondary" disabled={busy} onClick={onCancel}>
          Keep statement
        </button>
        <button
          className="button destructive"
          disabled={busy}
          onClick={onConfirm}
        >
          {busy ? "Deleting…" : "Delete statement"}
        </button>
      </div>
    </dialog>
  );
}
