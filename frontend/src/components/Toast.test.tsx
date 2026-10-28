import { act, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { Toast, UNDO_MS } from "./Toast";

afterEach(() => vi.useRealTimers());

describe("Toast", () => {
  it("keeps an Undo toast past 8 seconds and dismisses at the undo limit", () => {
    vi.useFakeTimers();
    const onDismiss = vi.fn();
    render(<Toast toast={{ id: 1, message: "Confirmed.", undo: () => {} }} onDismiss={onDismiss} />);
    act(() => void vi.advanceTimersByTime(14000));
    expect(onDismiss).not.toHaveBeenCalled();
    act(() => void vi.advanceTimersByTime(UNDO_MS - 14000));
    expect(onDismiss).toHaveBeenCalledTimes(1);
  });

  it("pauses while hovered", () => {
    vi.useFakeTimers();
    const onDismiss = vi.fn();
    render(<Toast toast={{ id: 1, message: "Confirmed.", undo: () => {} }} onDismiss={onDismiss} />);
    fireEvent.mouseEnter(screen.getByText("Confirmed.").parentElement!);
    act(() => void vi.advanceTimersByTime(UNDO_MS * 2));
    expect(onDismiss).not.toHaveBeenCalled();
    fireEvent.mouseLeave(screen.getByText("Confirmed.").parentElement!);
    act(() => void vi.advanceTimersByTime(UNDO_MS));
    expect(onDismiss).toHaveBeenCalledTimes(1);
  });

  it("keeps error toasts until dismissed and announces them", () => {
    vi.useFakeTimers();
    const onDismiss = vi.fn();
    render(<Toast toast={{ id: 1, message: "Nope.", error: true }} onDismiss={onDismiss} />);
    act(() => void vi.advanceTimersByTime(60000));
    expect(onDismiss).not.toHaveBeenCalled();
    expect(screen.getByRole("alert")).toHaveTextContent("Nope.");
  });
});
