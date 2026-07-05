"use client";

import { useCallback, useState } from "react";
import { Loader2, MessageCircle, Send, Sparkles } from "lucide-react";
import { sendCoachChatMessage } from "@/lib/cvCoachApi";
import { refineMasterSection, type CoachChatMessage, type CoachChatResponse } from "@/lib/api";
import { sectionDisplayName } from "@/features/playground/latexPreview";

interface CoachChatPanelProps {
  projectId: string;
  targetRole: string;
  focus: string;
  globalInstruction: string;
  onSectionUpdated: () => void;
  onPdfRefresh: () => void;
  onSuggestionSelected: (sectionPath: string, instruction: string) => void;
}

export function CoachChatPanel({
  projectId,
  targetRole,
  focus,
  globalInstruction,
  onSectionUpdated,
  onPdfRefresh,
  onSuggestionSelected,
}: CoachChatPanelProps) {
  const [messages, setMessages] = useState<CoachChatMessage[]>([
    {
      role: "assistant",
      content:
        "Ask me anything about your CV — e.g. “make experience shorter”, “add more cloud keywords”, or “improve my summary”.",
    },
  ]);
  const [draftMessage, setDraftMessage] = useState("");
  const [isSending, setIsSending] = useState(false);
  const [isApplying, setIsApplying] = useState(false);
  const [pendingAction, setPendingAction] = useState<CoachChatResponse | null>(null);
  const [errorMessage, setErrorMessage] = useState("");

  const handleDraftChange = useCallback((event: React.ChangeEvent<HTMLInputElement>) => {
    setDraftMessage(event.target.value);
  }, []);

  const handleSendMessage = useCallback(async () => {
    const trimmed = draftMessage.trim();
    if (!trimmed || isSending) return;

    const nextHistory: CoachChatMessage[] = [...messages, { role: "user", content: trimmed }];
    setMessages(nextHistory);
    setDraftMessage("");
    setIsSending(true);
    setErrorMessage("");
    setPendingAction(null);

    try {
      const response = await sendCoachChatMessage(projectId, {
        message: trimmed,
        history: messages,
        targetRole,
        focus,
      });
      setMessages([...nextHistory, { role: "assistant", content: response.reply }]);
      if (response.suggested_section_path && response.suggested_instruction) {
        setPendingAction(response);
      }
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Chat failed");
    } finally {
      setIsSending(false);
    }
  }, [draftMessage, focus, isSending, messages, projectId, targetRole]);

  const handleSendClick = useCallback(() => {
    void handleSendMessage();
  }, [handleSendMessage]);

  const handleKeyDown = useCallback(
    (event: React.KeyboardEvent<HTMLInputElement>) => {
      if (event.key === "Enter") {
        event.preventDefault();
        handleSendClick();
      }
    },
    [handleSendClick]
  );

  const handleApplySuggestedFix = useCallback(async () => {
    if (!pendingAction?.suggested_section_path || !pendingAction.suggested_instruction) return;
    setIsApplying(true);
    setErrorMessage("");
    try {
      await refineMasterSection({
        projectId,
        sectionPath: pendingAction.suggested_section_path,
        instruction: pendingAction.suggested_instruction,
        globalInstruction: globalInstruction || (targetRole ? `Optimize for target role: ${targetRole}` : ""),
      });
      onSectionUpdated();
      onPdfRefresh();
      onSuggestionSelected(pendingAction.suggested_section_path, pendingAction.suggested_instruction);
      setPendingAction(null);
      setMessages((previous) => [
        ...previous,
        { role: "assistant", content: "Applied that change to your CV. Check the preview on the right." },
      ]);
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Could not apply suggestion");
    } finally {
      setIsApplying(false);
    }
  }, [
    globalInstruction,
    onPdfRefresh,
    onSectionUpdated,
    onSuggestionSelected,
    pendingAction,
    projectId,
    targetRole,
  ]);

  const handleApplyClick = useCallback(() => {
    void handleApplySuggestedFix();
  }, [handleApplySuggestedFix]);

  const handleUseSuggestedInstruction = useCallback(() => {
    if (!pendingAction?.suggested_section_path || !pendingAction.suggested_instruction) return;
    onSuggestionSelected(pendingAction.suggested_section_path, pendingAction.suggested_instruction);
    setPendingAction(null);
  }, [onSuggestionSelected, pendingAction]);

  return (
    <div className="rounded-apple-lg border border-apple-separator/60 bg-apple-surface-secondary/30 p-4" data-testid="coach-chat-panel">
      <h3 className="mb-3 flex items-center gap-2 text-apple-subheadline font-semibold text-apple-label">
        <MessageCircle size={16} className="text-brand-500" />
        Chat with CV Coach
      </h3>

      <div className="mb-3 max-h-56 space-y-2 overflow-y-auto" data-testid="coach-chat-messages">
        {messages.map((message, index) => (
          <div
            key={`${message.role}-${index}`}
            className={
              message.role === "user"
                ? "ml-8 rounded-apple bg-brand-500/10 px-3 py-2 text-apple-footnote text-apple-label"
                : "mr-8 rounded-apple bg-white/60 px-3 py-2 text-apple-footnote text-apple-label-secondary dark:bg-white/5"
            }
          >
            {message.content}
          </div>
        ))}
        {isSending ? (
          <div className="flex items-center gap-2 text-apple-footnote text-apple-label-secondary">
            <Loader2 size={14} className="animate-spin" />
            Thinking…
          </div>
        ) : null}
      </div>

      {pendingAction?.suggested_section_path ? (
        <div className="mb-3 rounded-apple border border-brand-500/20 bg-brand-500/5 p-3" data-testid="coach-chat-suggested-action">
          <p className="text-apple-caption font-medium text-brand-600">
            Suggested edit: {sectionDisplayName(pendingAction.suggested_section_path)}
          </p>
          <p className="mt-1 text-apple-footnote text-apple-label-secondary">
            {pendingAction.suggested_instruction}
          </p>
          <div className="mt-2 flex flex-wrap gap-2">
            <button
              type="button"
              onClick={handleApplyClick}
              disabled={isApplying}
              className="glass-button-primary text-sm"
              data-testid="coach-chat-apply-btn"
            >
              {isApplying ? <Loader2 size={14} className="animate-spin" /> : <Sparkles size={14} />}
              Apply to CV
            </button>
            <button type="button" onClick={handleUseSuggestedInstruction} className="glass-button text-sm">
              Edit instruction
            </button>
          </div>
        </div>
      ) : null}

      <div className="flex gap-2">
        <input
          value={draftMessage}
          onChange={handleDraftChange}
          onKeyDown={handleKeyDown}
          placeholder="Ask the coach to improve a section…"
          className="glass-input flex-1 text-sm"
          data-testid="coach-chat-input"
        />
        <button
          type="button"
          onClick={handleSendClick}
          disabled={isSending || !draftMessage.trim()}
          className="glass-button-primary text-sm"
          data-testid="coach-chat-send-btn"
        >
          <Send size={14} />
          Send
        </button>
      </div>

      {errorMessage ? (
        <p className="mt-2 text-apple-footnote text-apple-pink" data-testid="coach-chat-error">
          {errorMessage}
        </p>
      ) : null}
    </div>
  );
}
