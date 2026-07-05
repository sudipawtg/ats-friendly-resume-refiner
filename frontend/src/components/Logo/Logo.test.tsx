import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { Logo, LogoMark } from "./Logo";

describe("Logo", () => {
  it("renders logo mark", () => {
    render(<LogoMark />);
    expect(document.querySelector("svg")).toBeInTheDocument();
  });

  it("renders wordmark with brand accent", () => {
    render(<Logo />);
    expect(screen.getByTestId("logo-mark")).toBeInTheDocument();
    expect(screen.getByText("Resume")).toBeInTheDocument();
    expect(screen.getByText("Forge")).toBeInTheDocument();
    expect(screen.getByText("AI CV tailoring")).toBeInTheDocument();
  });

  it("can hide wordmark", () => {
    render(<Logo showWordmark={false} />);
    expect(screen.getByTestId("logo-mark")).toBeInTheDocument();
    expect(screen.queryByText("Resume")).not.toBeInTheDocument();
  });
});
