import { render, screen } from "@testing-library/react";
import { ArticleContent } from "./article-content";

describe("ArticleContent Markdown", () => {
  it("renders the supported GFM subset with stable unique heading anchors", () => {
    const { container } = render(
      <ArticleContent
        blocks={[
          {
            id: "markdown",
            kind: "markdown",
            source: [
              "# Architecture",
              "## Architecture",
              "Paragraph with **strong** and [documentation](https://example.com/docs).",
              "- one",
              "- two",
              "1. first",
              "2. second",
              "> A reviewed quotation.",
              "```ts",
              "const ready = true;",
              "```",
              "| Signal | State |",
              "| --- | --- |",
              "| API | Ready |",
            ].join("\n"),
          },
        ]}
      />,
    );

    const headings = screen.getAllByRole("heading", { name: "Architecture" });
    expect(headings.map((heading) => heading.id)).toEqual([
      "article-architecture",
      "article-architecture-1",
    ]);
    expect(screen.getByRole("link", { name: "documentation" })).toHaveAttribute(
      "href",
      "https://example.com/docs",
    );
    expect(container.querySelector("ul")).not.toBeNull();
    expect(container.querySelector("ol")).not.toBeNull();
    expect(container.querySelector("blockquote")).toHaveTextContent(
      "A reviewed quotation.",
    );
    expect(container.querySelector("pre")).toHaveTextContent("const ready = true;");
    expect(container.querySelector("table")).toHaveTextContent("Ready");
  });

  it("drops raw HTML, unsafe URLs, and inaccessible images", () => {
    const { container } = render(
      <ArticleContent
        blocks={[
          {
            id: "unsafe",
            kind: "markdown",
            source: [
              '<script aria-label="attack">alert(1)</script>',
              "[unsafe](javascript:alert(1))",
              "![](https://example.com/image.png)",
              "![Reviewed diagram](https://example.com/diagram.png)",
            ].join("\n\n"),
          },
        ]}
      />,
    );

    expect(container.querySelector("script")).toBeNull();
    expect(screen.queryByRole("link", { name: "unsafe" })).toBeNull();
    expect(screen.queryByAltText("missing alternative")).toBeNull();
    expect(screen.getByAltText("Reviewed diagram")).toBeInTheDocument();
  });
});
