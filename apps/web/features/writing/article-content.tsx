import type { ArticleBlock } from "@portfolio/api-client";
import { Badge } from "@portfolio/ui";
import GithubSlugger from "github-slugger";
import { Quote } from "lucide-react";
import Image from "next/image";
import type { ReactNode } from "react";
import Markdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { MediaImage } from "@/components/media-image";

function safeMarkdownUrl(value: string | undefined): string | undefined {
  if (!value) return undefined;
  if (
    (value.startsWith("/") && !value.startsWith("//") && !value.includes("\\")) ||
    value.startsWith("#")
  )
    return value;
  try {
    const parsed = new URL(value);
    if (parsed.protocol === "https:" && !parsed.username && !parsed.password)
      return parsed.toString();
    if (parsed.protocol === "mailto:" && !parsed.search && !parsed.hash)
      return parsed.toString();
  } catch {
    return undefined;
  }
  return undefined;
}

function textContent(children: ReactNode): string {
  if (typeof children === "string" || typeof children === "number")
    return String(children);
  if (Array.isArray(children)) return children.map(textContent).join("");
  if (children && typeof children === "object" && "props" in children) {
    const props = children.props as { children?: ReactNode };
    return textContent(props.children);
  }
  return "";
}

function MarkdownBody({ source }: { source: string }) {
  const slugger = new GithubSlugger();
  const headingId = (children: ReactNode) => `article-${slugger.slug(textContent(children))}`;
  return (
    <Markdown
      remarkPlugins={[remarkGfm]}
      skipHtml
      urlTransform={(url) => safeMarkdownUrl(url) ?? ""}
      components={{
        h1: ({ children }) => <h2 id={headingId(children)}>{children}</h2>,
        h2: ({ children }) => <h2 id={headingId(children)}>{children}</h2>,
        h3: ({ children }) => <h3 id={headingId(children)}>{children}</h3>,
        h4: ({ children }) => <h4 id={headingId(children)}>{children}</h4>,
        h5: ({ children }) => <h5 id={headingId(children)}>{children}</h5>,
        h6: ({ children }) => <h6 id={headingId(children)}>{children}</h6>,
        a: ({ children, href }) => {
          const safeHref = safeMarkdownUrl(href);
          if (!safeHref) return <span>{children}</span>;
          const external = safeHref.startsWith("https://");
          return (
            <a
              href={safeHref}
              {...(external ? { target: "_blank", rel: "noreferrer" } : {})}
            >
              {children}
            </a>
          );
        },
        img: ({ alt, src }) => {
          const safeSrc = safeMarkdownUrl(typeof src === "string" ? src : undefined);
          if (!safeSrc || !alt?.trim()) return null;
          return (
            <span className="relative my-8 block aspect-video overflow-hidden rounded-[var(--radius-card)] border border-border">
              <Image
                src={safeSrc}
                alt={alt}
                fill
                unoptimized
                sizes="(max-width: 900px) 92vw, 760px"
                className="object-cover"
              />
            </span>
          );
        },
        blockquote: ({ children }) => (
          <blockquote className="border-l-2 border-primary pl-6 font-display text-2xl leading-relaxed">
            {children}
          </blockquote>
        ),
        pre: ({ children }) => (
          <pre className="max-w-full overflow-x-auto rounded-2xl bg-ink p-5 text-sm leading-6 text-white">
            {children}
          </pre>
        ),
        table: ({ children }) => (
          <span className="my-8 block max-w-full overflow-x-auto">
            <table>{children}</table>
          </span>
        ),
      }}
    >
      {source}
    </Markdown>
  );
}

export function ArticleContent({ blocks }: { blocks: ArticleBlock[] }) {
  return (
    <div className="prose-portfolio">
      {blocks.map((block) => {
        switch (block.kind) {
          case "markdown":
            return <MarkdownBody key={block.id} source={block.source} />;
          case "text":
            return <p key={block.id} className="whitespace-pre-line">{block.body}</p>;
          case "heading": {
            const Heading = block.level === 2 ? "h2" : "h3";
            return <Heading key={block.id} id={`section-${block.id}`}>{block.text}</Heading>;
          }
          case "quote":
            return <figure key={block.id} className="my-12 border-y border-border py-10"><Quote className="size-7 text-primary" aria-hidden="true" /><blockquote className="mt-7 font-display text-[clamp(2rem,4vw,3.7rem)] leading-[1.03] tracking-[-0.045em]">“{block.quote}”</blockquote>{block.attribution && <figcaption className="mt-6 text-sm font-semibold text-muted-foreground">— {block.attribution}</figcaption>}</figure>;
          case "code":
            return <figure key={block.id} className="my-10 overflow-hidden rounded-[var(--radius-card)] border border-border-strong bg-ink text-white"><figcaption className="flex items-center justify-between border-b border-white/10 px-5 py-3 font-mono text-[0.62rem] uppercase tracking-[0.12em] text-white/55"><span>{block.caption ?? "Code sample"}</span>{block.language && <Badge variant="outline">{block.language}</Badge>}</figcaption><pre className="overflow-x-auto p-5 text-sm leading-6"><code>{block.code}</code></pre></figure>;
          case "image":
            return <figure key={block.id} className="my-12"><MediaImage asset={block.media} className="aspect-[16/10] rounded-[var(--radius-card)] border border-border" fallbackLabel="Managed article media" />{block.caption && <figcaption className="mt-3 text-center font-mono text-[0.62rem] uppercase tracking-[0.1em] text-muted-foreground">{block.caption}</figcaption>}</figure>;
          case "list": {
            const List = block.style === "ordered" ? "ol" : "ul";
            return <List key={block.id} className={`${block.style === "ordered" ? "list-decimal" : "list-disc"} grid gap-2 pl-6 marker:text-primary`}>{block.items.map((item) => <li key={item} className="pl-2">{item}</li>)}</List>;
          }
        }
      })}
    </div>
  );
}
