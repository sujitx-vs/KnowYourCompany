"use client";

import { useState } from "react";

export default function Home() {
  const [companyName, setCompanyName] = useState("");
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");

  const [threadId, setThreadId] = useState("");
  const [domains, setDomains] = useState<string[]>([]);
  const [selectedDomain, setSelectedDomain] = useState("");

  const [pdfPath, setPdfPath] = useState("");


  // ============================================================
  // START COMPANY RESEARCH
  // ============================================================

  async function handleResearch() {
    const cleanedName = companyName.trim();

    if (!cleanedName) {
      setMessage("Please enter a company name.");
      return;
    }

    try {
      setLoading(true);
      setMessage("");

      setThreadId("");
      setDomains([]);
      setSelectedDomain("");
      setPdfPath("");

      const response = await fetch(
        "http://127.0.0.1:8000/research",
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            company_name: cleanedName,
          }),
        }
      );

      const data = await response.json();

      console.log(
        "Backend response:",
        data
      );

      if (!response.ok) {
        setMessage(
          "Research request failed."
        );
        return;
      }

      if (
        data.status ===
        "awaiting_domain_selection"
      ) {
        setThreadId(
          data.thread_id
        );

        setDomains(
          data.available_domains
        );

        setMessage(
          "Company research completed. The agent needs your input."
        );

      } else if (
        data.status === "completed"
      ) {
        setMessage(
          "Research completed."
        );

      } else {
        setMessage(
          data.message ||
          "Unexpected backend response."
        );
      }

    } catch (error) {
      console.error(
        error
      );

      setMessage(
        "Could not connect to the backend."
      );

    } finally {
      setLoading(
        false
      );
    }
  }


  // ============================================================
  // HUMAN-IN-THE-LOOP DOMAIN SELECTION
  // ============================================================

  async function handleDomainSelection(
    domain: string
  ) {
    if (!threadId) {
      setMessage(
        "Research session could not be found."
      );
      return;
    }

    try {
      setLoading(
        true
      );

      setSelectedDomain(
        domain
      );

      setMessage(
        `Continuing research with ${domain}...`
      );

      const response = await fetch(
        "http://127.0.0.1:8000/select-domain",
        {
          method: "POST",
          headers: {
            "Content-Type":
              "application/json",
          },
          body: JSON.stringify({
            thread_id: threadId,
            selected_domain: domain,
          }),
        }
      );

      const data =
        await response.json();

      console.log(
        "Domain research response:",
        data
      );

      if (!response.ok) {
        setMessage(
          "Domain research request failed."
        );
        return;
      }

      if (
        data.status === "completed"
      ) {
        setDomains(
          []
        );

        if (data.pdf_path) {
          setPdfPath(
            data.pdf_path
          );

          setMessage(
            `Research completed for ${domain}. Your PDF report is ready.`
          );

        } else {
          setMessage(
            `Research completed for ${domain}, but no PDF path was returned.`
          );
        }

      } else {
        setMessage(
          data.message ||
          "Unexpected backend response."
        );
      }

    } catch (error) {
      console.error(
        error
      );

      setMessage(
        "Could not continue the research."
      );

    } finally {
      setLoading(
        false
      );
    }
  }


  // ============================================================
  // PDF URLS
  // ============================================================

  const pdfViewUrl = pdfPath
    ? `http://127.0.0.1:8000/view-pdf?path=${encodeURIComponent(
        pdfPath
      )}`
    : "";

  const pdfDownloadUrl = pdfPath
    ? `http://127.0.0.1:8000/download-pdf?path=${encodeURIComponent(
        pdfPath
      )}`
    : "";


  return (
    <main className="relative min-h-screen overflow-hidden bg-slate-950 text-white">

      {/* Background Glow */}
      <div className="absolute left-1/2 top-[-200px] h-[500px] w-[700px] -translate-x-1/2 rounded-full bg-indigo-600/20 blur-[120px]" />


      {/* Navbar */}
      <nav className="relative z-10 mx-auto flex max-w-7xl items-center justify-between px-6 py-6">

        <div className="flex items-center gap-3">

          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-white text-sm font-bold text-slate-950">
            K
          </div>

          <span className="text-lg font-semibold tracking-tight">
            KnowYourCompany
          </span>

        </div>


        <div className="rounded-full border border-white/10 bg-white/5 px-4 py-2 text-sm text-slate-300">
          AI Placement Research
        </div>

      </nav>


      {/* Main Content */}
      <section className="relative z-10 mx-auto flex max-w-5xl flex-col items-center px-6 pt-28 text-center">


        {/* Badge */}
        <div className="mb-7 rounded-full border border-indigo-400/20 bg-indigo-400/10 px-4 py-2 text-sm text-indigo-200">
          AI-powered company intelligence
        </div>


        {/* Heading */}
        <h1 className="max-w-4xl text-5xl font-semibold leading-tight tracking-tight sm:text-6xl lg:text-7xl">

          Research your next company

          <span className="block bg-gradient-to-r from-indigo-300 via-purple-300 to-sky-300 bg-clip-text text-transparent">
            before the interview.
          </span>

        </h1>


        {/* Description */}
        <p className="mt-7 max-w-2xl text-lg leading-8 text-slate-400">

          Get focused company research, relevant career domains,
          technologies, skills, and placement preparation insights
          powered by an evidence-aware AI research agent.

        </p>


        {/* Search Card */}
        <div className="mt-12 w-full max-w-2xl rounded-2xl border border-white/10 bg-white/[0.06] p-2 shadow-2xl shadow-indigo-950/30 backdrop-blur">

          <div className="flex flex-col gap-2 sm:flex-row">

            <input
              type="text"
              value={companyName}
              onChange={(event) =>
                setCompanyName(
                  event.target.value
                )
              }
              onKeyDown={(event) => {
                if (
                  event.key === "Enter" &&
                  !loading
                ) {
                  handleResearch();
                }
              }}
              placeholder="Enter a company name, e.g. TCS"
              disabled={loading}
              className="
                min-w-0
                flex-1
                rounded-xl
                bg-transparent
                px-5
                py-4
                text-white
                outline-none
                placeholder:text-slate-500
                disabled:opacity-50
              "
            />


            <button
              onClick={
                handleResearch
              }
              disabled={
                loading
              }
              className="
                rounded-xl
                bg-white
                px-6
                py-4
                font-medium
                text-slate-950
                transition
                hover:bg-slate-200
                disabled:cursor-not-allowed
                disabled:opacity-60
              "
            >

              {
                loading &&
                domains.length === 0
                  ? "Researching..."
                  : "Research Company →"
              }

            </button>

          </div>

        </div>


        {/* Status Message */}
        {message && (
          <p className="mt-5 text-sm text-slate-300">
            {message}
          </p>
        )}


        {/* ================================================== */}
        {/* HUMAN-IN-THE-LOOP DOMAIN SELECTION */}
        {/* ================================================== */}

        {domains.length > 0 && (
          <div className="mt-10 w-full max-w-3xl">

            <div className="rounded-2xl border border-indigo-400/20 bg-indigo-400/[0.06] p-7 shadow-xl shadow-indigo-950/20">

              <div className="text-left">

                <div className="mb-5 flex items-center gap-3">

                  <div className="flex h-8 w-8 items-center justify-center rounded-full border border-indigo-400/30 bg-indigo-400/10 text-indigo-300">
                    ?
                  </div>

                  <div>

                    <p className="text-xs font-medium uppercase tracking-[0.18em] text-indigo-300">
                      Agent needs your input
                    </p>

                    <p className="mt-1 text-xs text-slate-500">
                      Research paused
                    </p>

                  </div>

                </div>


                <h2 className="text-xl font-semibold text-white">
                  Choose your preparation domain
                </h2>


                <p className="mt-2 text-sm leading-6 text-slate-400">

                  The agent found these relevant domains for{" "}

                  <span className="text-slate-200">
                    {companyName}
                  </span>

                  . Select one to continue the research.

                </p>

              </div>


              {/* Domain Buttons */}
              <div className="mt-6 grid gap-3 sm:grid-cols-2">

                {domains.map(
                  (domain) => {

                    const isSelected =
                      selectedDomain === domain;

                    return (
                      <button
                        key={
                          domain
                        }
                        onClick={() =>
                          handleDomainSelection(
                            domain
                          )
                        }
                        disabled={
                          loading
                        }
                        className={`
                          rounded-xl
                          border
                          px-5
                          py-4
                          text-left
                          text-sm
                          transition
                          disabled:cursor-not-allowed
                          disabled:opacity-60

                          ${
                            isSelected
                              ? "border-indigo-400/60 bg-indigo-400/15 text-white"
                              : "border-white/10 bg-white/[0.04] text-slate-200 hover:border-indigo-400/50 hover:bg-indigo-400/10 hover:text-white"
                          }
                        `}
                      >

                        <div className="flex items-center justify-between gap-4">

                          <span>
                            {domain}
                          </span>


                          {isSelected &&
                            loading && (
                              <span className="text-xs text-indigo-300">
                                Running...
                              </span>
                            )}

                        </div>

                      </button>
                    );
                  }
                )}

              </div>


              {!loading && (
                <p className="mt-5 text-left text-xs text-slate-500">

                  The agent will resume from the same research
                  session after your selection.

                </p>
              )}

            </div>

          </div>
        )}


        {/* ================================================== */}
        {/* SELECTED DOMAIN */}
        {/* ================================================== */}

        {selectedDomain &&
          domains.length === 0 && (

            <div className="mt-8 rounded-full border border-emerald-400/20 bg-emerald-400/10 px-4 py-2 text-sm text-emerald-200">

              Selected domain: {selectedDomain}

            </div>

          )}


        {/* ================================================== */}
        {/* PDF REPORT */}
        {/* ================================================== */}

        {pdfPath && (
          <div className="mt-10 w-full max-w-4xl">

            <div className="rounded-2xl border border-white/10 bg-white/[0.04] p-6 shadow-2xl shadow-indigo-950/20">


              {/* PDF Header */}
              <div className="flex flex-col gap-4 text-left sm:flex-row sm:items-center sm:justify-between">

                <div>

                  <div className="mb-2 flex items-center gap-2">

                    <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-emerald-400/10 text-sm text-emerald-300">
                      ✓
                    </div>

                    <p className="text-xs font-medium uppercase tracking-[0.18em] text-emerald-300">
                      Report ready
                    </p>

                  </div>


                  <h2 className="text-xl font-semibold">
                    Placement Preparation Report
                  </h2>


                  <p className="mt-2 text-sm text-slate-400">

                    Your company and domain research has been
                    compiled into a PDF report.

                  </p>

                </div>


                {/* Download Button */}
                <a
                  href={
                    pdfDownloadUrl
                  }
                  className="
                    inline-flex
                    items-center
                    justify-center
                    rounded-xl
                    bg-white
                    px-5
                    py-3
                    text-sm
                    font-medium
                    text-slate-950
                    transition
                    hover:bg-slate-200
                  "
                >

                  Download PDF ↓

                </a>

              </div>


              {/* PDF Preview */}
              <div className="mt-6 overflow-hidden rounded-xl border border-white/10 bg-white">

                <iframe
                  src={
                    pdfViewUrl
                  }
                  title="Placement Preparation Report"
                  className="h-[750px] w-full"
                />

              </div>


              {/* Open in new tab */}
              <div className="mt-4 flex justify-end">

                <a
                  href={
                    pdfViewUrl
                  }
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-sm text-indigo-300 transition hover:text-indigo-200"
                >
                  Open PDF in new tab ↗
                </a>

              </div>

            </div>

          </div>
        )}


        {/* Initial Explanation */}
        {!domains.length &&
          !selectedDomain &&
          !pdfPath && (

            <p className="mt-4 text-sm text-slate-500">

              Enter a company and let the agent research before
              you choose your preparation domain.

            </p>

          )}


        {/* ================================================== */}
        {/* FEATURE CARDS */}
        {/* ================================================== */}

        <div className="mt-20 grid w-full grid-cols-1 gap-4 pb-16 md:grid-cols-3">


          {/* Card 1 */}
          <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-6 text-left">

            <div className="mb-4 text-2xl">
              ◇
            </div>

            <h3 className="font-medium">
              Multi-source research
            </h3>

            <p className="mt-2 text-sm leading-6 text-slate-400">

              Researches company information across multiple web
              sources using Tavily and Exa.

            </p>

          </div>


          {/* Card 2 */}
          <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-6 text-left">

            <div className="mb-4 text-2xl">
              ✓
            </div>

            <h3 className="font-medium">
              Evidence-aware
            </h3>

            <p className="mt-2 text-sm leading-6 text-slate-400">

              Verifies company identity and filters unrelated evidence
              before generating insights.

            </p>

          </div>


          {/* Card 3 */}
          <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-6 text-left">

            <div className="mb-4 text-2xl">
              ◎
            </div>

            <h3 className="font-medium">
              Placement focused
            </h3>

            <p className="mt-2 text-sm leading-6 text-slate-400">

              Choose a relevant domain and receive focused preparation
              insights for your placement.

            </p>

          </div>

        </div>

      </section>

    </main>
  );
}