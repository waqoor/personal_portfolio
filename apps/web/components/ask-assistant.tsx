"use client";

import type {
  AssistantResponse,
  AssistantSettings,
} from "@portfolio/api-client";
import {
  Alert,
  AlertDescription,
  AlertIcon,
  AlertTitle,
  Badge,
  Button,
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
  LoadingIndicator,
  Textarea,
} from "@portfolio/ui";
import {
  ArrowUpRight,
  Bot,
  CornerDownLeft,
  RotateCcw,
  Sparkles,
} from "lucide-react";
import * as React from "react";
import { getBrowserApi } from "@/lib/browser-api";

export function AskAssistant({ settings }: { settings: AssistantSettings }) {
  const [open, setOpen] = React.useState(false);
  const [question, setQuestion] = React.useState("");
  const [answer, setAnswer] = React.useState<AssistantResponse>();
  const [error, setError] = React.useState<string>();
  const [pending, startTransition] = React.useTransition();
  const textareaRef = React.useRef<HTMLTextAreaElement>(null);

  React.useEffect(() => {
    const launch = () => setOpen(true);
    window.addEventListener("portfolio:ask-ai", launch);
    return () => window.removeEventListener("portfolio:ask-ai", launch);
  }, []);

  const ask = (nextQuestion: string) => {
    const cleanQuestion = nextQuestion.trim();
    if (
      cleanQuestion.length < 3 ||
      cleanQuestion.length > settings.max_question_length ||
      pending
    )
      return;
    setError(undefined);
    startTransition(async () => {
      try {
        const result = await getBrowserApi().public.askAssistant({
          question: cleanQuestion,
        });
        setAnswer(result);
        setQuestion("");
      } catch (caught) {
        setError(
          caught instanceof Error
            ? caught.message
            : "The assistant could not answer right now.",
        );
      }
    });
  };

  const reset = () => {
    setAnswer(undefined);
    setQuestion("");
    setError(undefined);
    requestAnimationFrame(() => textareaRef.current?.focus());
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button
          variant="signal"
          size="lg"
          className="fixed bottom-4 right-4 z-40 shadow-[0_18px_60px_-24px_var(--shadow-ink)] sm:bottom-6 sm:right-6"
          aria-label="Ask my portfolio AI"
        >
          <Sparkles aria-hidden="true" />
          <span className="hidden sm:inline">Ask my AI</span>
        </Button>
      </DialogTrigger>
      <DialogContent className="bottom-3 left-3 right-3 top-auto max-h-[calc(100dvh-1.5rem)] w-auto max-w-none translate-x-0 translate-y-0 p-0 sm:left-auto sm:right-5 sm:w-[min(38rem,calc(100%-2.5rem))]">
        <div className="coordinate-grid border-b border-border p-6 pr-16 sm:p-8 sm:pr-16">
          <DialogHeader>
            <div className="mb-3 grid size-11 place-items-center rounded-full border border-primary/40 bg-primary/12 text-accent-ink dark:text-primary">
              <Bot className="size-5" aria-hidden="true" />
            </div>
            <DialogTitle>Ask the portfolio</DialogTitle>
            <DialogDescription>{settings.greeting}</DialogDescription>
          </DialogHeader>
        </div>

        <div className="grid gap-5 p-6 sm:p-8">
          {answer ? (
            <div className="grid gap-5" aria-live="polite">
              <div className="flex items-center justify-between gap-3">
                <Badge
                  variant={
                    answer.confidence === "high"
                      ? "verified"
                      : answer.confidence === "low" ||
                          answer.confidence === "unknown"
                        ? "destructive"
                        : "signal"
                  }
                >
                  {answer.confidence} confidence
                </Badge>
                <Button variant="ghost" size="sm" onClick={reset}>
                  <RotateCcw aria-hidden="true" />
                  New question
                </Button>
              </div>
              <p className="whitespace-pre-wrap text-base leading-7">
                {answer.answer}
              </p>
              {answer.citations.length > 0 && (
                <div className="grid gap-2 border-t border-border pt-5">
                  <p className="font-mono text-[0.65rem] font-semibold uppercase tracking-[0.15em] text-muted-foreground">
                    Published sources
                  </p>
                  {answer.citations.map((citation) => (
                    <a
                      key={`${citation.url}-${citation.title}`}
                      href={citation.url}
                      className="group flex min-h-11 items-center justify-between rounded-xl border border-border px-3 py-2 text-sm font-semibold transition-colors hover:border-primary hover:bg-primary/8"
                    >
                      <span>
                        <span className="mr-2 font-mono text-[0.65rem] text-primary">
                          [{citation.citation}]
                        </span>
                        {citation.title}
                      </span>
                      <ArrowUpRight
                        className="size-4 transition-transform group-hover:-translate-y-0.5 group-hover:translate-x-0.5"
                        aria-hidden="true"
                      />
                    </a>
                  ))}
                </div>
              )}
            </div>
          ) : (
            <>
              <div className="grid gap-2">
                <p className="font-mono text-[0.65rem] font-semibold uppercase tracking-[0.15em] text-muted-foreground">
                  Try asking
                </p>
                {settings.suggested_questions.map((suggestion) => (
                  <button
                    key={suggestion}
                    type="button"
                    onClick={() => {
                      setQuestion(suggestion);
                      textareaRef.current?.focus();
                    }}
                    className="min-h-11 rounded-xl border border-border px-3 py-2 text-left text-sm leading-5 transition-colors hover:border-primary hover:bg-primary/8 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                  >
                    {suggestion}
                  </button>
                ))}
              </div>
              <form
                onSubmit={(event) => {
                  event.preventDefault();
                  ask(question);
                }}
                className="grid gap-3"
              >
                <label htmlFor="assistant-question" className="sr-only">
                  Question for the portfolio assistant
                </label>
                <Textarea
                  ref={textareaRef}
                  id="assistant-question"
                  value={question}
                  onChange={(event) => setQuestion(event.target.value)}
                  maxLength={settings.max_question_length}
                  placeholder="Ask about projects, experience, tools, or fit…"
                  className="min-h-28"
                />
                <div className="flex items-center justify-between gap-4">
                  <span className="font-mono text-[0.62rem] text-muted-foreground">
                    {question.length}/{settings.max_question_length}
                  </span>
                  <Button
                    type="submit"
                    variant="signal"
                    disabled={
                      pending ||
                      question.trim().length < 3 ||
                      question.length > settings.max_question_length
                    }
                  >
                    {pending ? (
                      <LoadingIndicator label="Thinking" />
                    ) : (
                      <>
                        <span>Ask</span>
                        <CornerDownLeft aria-hidden="true" />
                      </>
                    )}
                  </Button>
                </div>
              </form>
            </>
          )}

          {error && (
            <Alert variant="destructive">
              <AlertIcon variant="destructive" />
              <AlertTitle>Assistant unavailable</AlertTitle>
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}
          <p className="border-t border-border pt-4 text-xs leading-5 text-muted-foreground">
            {settings.disclaimer}
          </p>
        </div>
      </DialogContent>
    </Dialog>
  );
}
