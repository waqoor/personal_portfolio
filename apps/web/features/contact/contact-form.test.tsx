import { act, fireEvent, render, screen } from "@testing-library/react";
import { fixtureContactOptions } from "@/test/portfolio-fixture";
import { ContactForm } from "./contact-form";

const { submitContact } = vi.hoisted(() => ({ submitContact: vi.fn() }));

vi.mock("@/lib/browser-api", () => ({
  getBrowserApi: () => ({ public: { submitContact } }),
}));

function completeValidForm() {
  fireEvent.change(screen.getByLabelText(/Name/), { target: { value: "Portfolio Visitor" } });
  fireEvent.change(screen.getByLabelText(/Email/), { target: { value: "visitor@example.com" } });
  fireEvent.change(screen.getByLabelText(/Organization/), { target: { value: "Example Org" } });
  fireEvent.change(screen.getByLabelText(/Subject/), { target: { value: "Production collaboration" } });
  fireEvent.change(screen.getByLabelText(/Context/), {
    target: { value: "I would like to discuss a concrete production platform project." },
  });
  const category = document.querySelector<HTMLSelectElement>('select[name="category_id"]');
  if (!category) throw new Error("Contact category control did not render a form value");
  fireEvent.change(category, { target: { value: "project" } });
  fireEvent.click(screen.getByRole("checkbox"));
}

describe("ContactForm", () => {
  beforeEach(() => submitContact.mockReset());

  it("exposes behavior-oriented validation without submitting incomplete data", () => {
    render(<ContactForm options={fixtureContactOptions} />);
    fireEvent.change(screen.getByLabelText(/Name/), { target: { value: "A" } });
    fireEvent.change(screen.getByLabelText(/Email/), { target: { value: "invalid" } });
    fireEvent.change(screen.getByLabelText(/Subject/), { target: { value: "x" } });
    fireEvent.change(screen.getByLabelText(/Context/), { target: { value: "short" } });
    fireEvent.click(screen.getByRole("button", { name: /Send inquiry/ }));
    expect(screen.getAllByRole("alert").length).toBeGreaterThanOrEqual(4);
    expect(screen.queryByText(/Message received/)).not.toBeInTheDocument();
  });

  it("renders the service-controlled paused state", () => {
    render(<ContactForm options={{ ...fixtureContactOptions, accepting_messages: false }} />);
    expect(screen.getByRole("alert")).toHaveTextContent("Contact form paused");
    expect(screen.queryByRole("button", { name: /Send inquiry/ })).not.toBeInTheDocument();
  });

  it("submits validated data and renders the server receipt", async () => {
    submitContact.mockResolvedValue({
      reference_id: "contact-1",
      message: "Message received for review.",
    });
    render(<ContactForm options={fixtureContactOptions} />);
    completeValidForm();

    await act(async () => {
      fireEvent.submit(screen.getByRole("button", { name: /Send inquiry/ }).closest("form")!);
    });

    expect(await screen.findByText("Message received for review.")).toBeInTheDocument();
    expect(submitContact).toHaveBeenCalledWith(
      expect.objectContaining({
        category_id: "project",
        organization: "Example Org",
        consent: true,
      }),
      { idempotencyKey: expect.stringMatching(/^contact-/) },
    );
  });

  it("reuses one operation key across an ambiguous retry", async () => {
    submitContact
      .mockRejectedValueOnce(new Error("Network timeout"))
      .mockResolvedValueOnce({ message: "Message received for review." });
    render(<ContactForm options={fixtureContactOptions} />);
    completeValidForm();
    const form = screen.getByRole("button", { name: /Send inquiry/ }).closest("form")!;

    await act(async () => fireEvent.submit(form));
    await screen.findByText(/Network timeout/);
    await act(async () => fireEvent.submit(form));

    const firstKey = submitContact.mock.calls[0]?.[1].idempotencyKey;
    expect(firstKey).toBeTruthy();
    expect(submitContact.mock.calls[1]?.[1].idempotencyKey).toBe(firstKey);
  });

});
